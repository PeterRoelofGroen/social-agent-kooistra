import os
import shutil
import uuid
import mimetypes

# 1. Load env
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

# Import Tools
from src.agent.graph import app as agent_app
from src.tools.downloader import download_image_from_url
from src.tools.notifications import send_whatsapp_preview
from src.tools.state_manager import save_draft, get_draft, update_draft_caption, clear_draft

# Import Video Tools
from src.tools.video_ops import brand_video, extract_keyframes

# Import Official API
from src.tools.official_api import post_to_facebook, post_to_instagram, post_reel_to_instagram, post_video_to_facebook, get_fb_picture_url

# Initialize FastAPI
app = FastAPI(title="Social Media AI Agent")

# Define directories
TEMP_DIR = "/tmp"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# --- MOUNT STATIC FILES ---
app.mount("/static", StaticFiles(directory=TEMP_DIR), name="static")

class SocialResponse(BaseModel):
    status: str
    caption: str
    platform: str

def get_auth_headers(access_token):
    return {"Authorization": f"Bearer {access_token}"}

# Helper: Execute Post (Official API + Logs)
def execute_post(media_path: str, caption: str, dry_run: bool = False):
    """
    Uploads to FB (Binary) -> Gets FB URL -> Uploads to IG.
    """
    # 1. Define Public URL (Still useful for video or fallback)
    base_url = os.environ.get("BASE_URL", "").rstrip("/")
    filename = os.path.basename(media_path)
    public_url = f"{base_url}/static/{filename}"
    
    is_video = media_path.lower().endswith(".mp4")

    print(f"STARTING UPLOAD ({'VIDEO' if is_video else 'IMAGE'})")
    print(f"File: {media_path}")

    if is_video:
        # Video Logic (Keep as is, or apply similar binary logic if needed)
        fb_success = post_video_to_facebook(public_url, caption, dry_run=dry_run)
        ig_success = post_reel_to_instagram(public_url, caption, dry_run=dry_run)
    else:
        # --- IMAGE OPTIMIZED FLOW ---
        
        # 1. Upload to Facebook (Using LOCAL FILE path for reliability)
        fb_id = post_to_facebook(media_path, caption, dry_run=dry_run)
        fb_success = bool(fb_id)
        
        ig_success = False
        if fb_success:
            # 2. Get the Meta-hosted URL (Trusted by Instagram)
            if dry_run:
                high_quality_url = public_url
            else:
                print("🔄 Fetching Facebook CDN URL for Instagram...")
                high_quality_url = get_fb_picture_url(fb_id)

            if high_quality_url:
                # 3. Upload to Instagram using the Facebook URL
                ig_success = post_to_instagram(high_quality_url, caption, dry_run=dry_run)
            else:
                print("⚠️ Could not retrieve FB URL, skipping IG.")
        else:
            print("⚠️ Facebook failed, skipping Instagram.")

    if fb_success and ig_success:
        print("ALL UPLOADS SUCCESSFUL")
        return True
    else:
        return False

# Helper: Send Reply
def send_reply(to_number: str, body_text: str):
    try:
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        client = Client(account_sid, auth_token)
        
        from_number = os.environ.get("WHATSAPP_NUMBER")

        client.messages.create(
            from_=from_number,
            to=to_number,
            body=body_text
        )
        print(f"Reply sent to {to_number}")
    except Exception as e:
        print(f"Failed to send reply: {e}")

# --- BACKGROUND TASK ---
# Updated to accept mime_type and handle Video vs Image logic
def process_incoming_media(media_url: str, mime_type: str, context_text: str, sender_number: str):
    print(f"Background Processing Started for {sender_number} [{mime_type}]")
    
    try:
        # 1. Download Content
        local_path = download_image_from_url(media_url)
        
        # 2. Check if Video or Image
        is_video = "video" in mime_type or local_path.endswith(".mp4")
        
        agent_inputs = {
            "context_text": context_text or "Maak een professionele post.",
            "is_video": is_video
        }

        if is_video:
            print("🎥 Video detected. Starting branding and frame extraction...")
            # A. Brand the video (Heavy Task)
            branded_video_path = brand_video(local_path)
            
            # B. Extract Keyframes (For the AI to see)
            keyframes = extract_keyframes(branded_video_path, num_frames=5)
            
            # C. Prepare Inputs
            agent_inputs["input_path"] = branded_video_path # The file to post
            agent_inputs["analysis_frame_paths"] = keyframes # The files to look at
            
        else:
            print("🖼️ Image detected. Starting standard processing...")
            # A. Prepare Inputs (Image branding happens inside the Graph)
            agent_inputs["input_path"] = local_path
            agent_inputs["analysis_frame_paths"] = None 

        # 3. Run Agent (Gemini)
        result = agent_app.invoke(agent_inputs)
        
        final_caption = result['generated_caption']
        final_media_path = result['processed_path'] # Branded Image OR Branded Video
        
        print("\n --- AGENT FINISHED ---")
        print(f"GENERATED CAPTION (RAW): {final_caption}")
        
        # 4. SAVE DRAFT
        save_draft(sender_number, final_media_path, final_caption)
        
        # 5. SEND PREVIEW
        # Dutch text, No Emoji
        preview_message = (
            f"{final_caption}\n\n"
            "------------------\n"
            "Antwoord *POST* om te publiceren.\n"
            "Antwoord *VERWIJDER* om te annuleren.\n"
            "Antwoord met een andere omschrijving om deze te vervangen."
        )
        
        send_whatsapp_preview(
            to_number=sender_number,
            image_path=final_media_path, 
            caption=preview_message
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Processing Failed: {e}")
        send_reply(sender_number, "Er is iets fout gegaan bij het verwerken van de media.")

# --- ROUTES ---

@app.get("/")
def health_check():
    return {"status": "online", "service": "Social Agent v1"}

@app.post("/process-upload", response_model=SocialResponse)
async def process_media(
    image: UploadFile = File(...),
    context: str = Form(...),
    platform: str = Form("Instagram")
):
    try:
        file_extension = image.filename.split(".")[-1]
        input_filename = f"input_{uuid.uuid4()}.{file_extension}"
        input_path = os.path.join(TEMP_DIR, input_filename)
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        # Fix: Ensure API calls use the correct keys
        agent_inputs = {
            "input_path": input_path, 
            "context_text": context,
            "is_video": False,
            "analysis_frame_paths": None
        }
        print(f"Agent triggered for: {input_filename}")
        result = agent_app.invoke(agent_inputs)
        
        return {
            "status": "success",
            "caption": result["generated_caption"],
            "platform": platform
        }
    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/whatsapp")
async def handle_whatsapp(request: Request, background_tasks: BackgroundTasks):
    form_data = await request.form()
    num_media = int(form_data.get("NumMedia", 0))
    incoming_msg = form_data.get("Body", "").strip()
    sender_number = form_data.get("From", "")
    
    # Get Media Type (Important for Video detection)
    mime_type = form_data.get("MediaContentType0", "")
    
    print(f"New WhatsApp from {sender_number} [{mime_type}]: {incoming_msg}")

    resp = MessagingResponse()

    # --- SCENARIO 1: NEW MEDIA (Start Draft) ---
    if num_media > 0:
        media_url = form_data.get("MediaUrl0")
        
        msg_type = "Video" if "video" in mime_type else "Foto"
        send_reply(sender_number, f"{msg_type} ontvangen, een moment geduld...")
        
        # Pass mime_type to the background task
        background_tasks.add_task(process_incoming_media, media_url, mime_type, incoming_msg, sender_number)
        return str(resp)

    # --- SCENARIO 2: TEXT REPLY (Edit or Post) ---
    current_draft = get_draft(sender_number)
    
    if not current_draft:
        send_reply(sender_number, "Geen concept gevonden. Stuur eerst media.")
        return str(resp)
    
    command = incoming_msg.upper()

    if command == "POST":
        success = execute_post(current_draft["image_path"], current_draft["caption"])
        
        if success:
            clear_draft(sender_number)
            send_reply(sender_number, "Gepubliceerd op social media.")
        else:
            send_reply(sender_number, "Publicatie mislukt. Controleer de logs.")
        
    elif command == "VERWIJDER" or command == "CANCEL":
        clear_draft(sender_number)
        send_reply(sender_number, "Concept verwijderd.")
        
    else:
        # Edit Caption
        update_draft_caption(sender_number, incoming_msg)
        
        updated_draft = get_draft(sender_number)
        msg_body = (
            "*Beschrijving aangepast!*\n\n"
            "Hier is de nieuwe versie:\n"
            "------------------\n"
            f"{updated_draft['caption']}\n"
            "------------------\n"
            "Antwoord *POST* om te publiceren."
        )
        send_reply(sender_number, msg_body)

    return str(resp)

@app.post("/manual-post")
async def manual_post_endpoint(
    file: UploadFile = File(...),
    caption: str = Form(...),
    dry_run: bool = Form(False)
):
    """
    Directly posts an image/video and caption to Facebook & Instagram.
    Bypasses AI generation and WhatsApp.
    """
    try:
        # 1. Save the uploaded file
        file_extension = file.filename.split(".")[-1]
        input_filename = f"manual_{uuid.uuid4()}.{file_extension}"
        input_path = os.path.join(TEMP_DIR, input_filename)
        
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        print(f"📂 Manual upload received: {input_filename}")

        # 2. Execute the post
        # execute_post handles the public URL construction and API calls
        success = execute_post(input_path, caption, dry_run=dry_run)

        if success:
            return {"status": "success", "message": "Posted successfully!", "file": input_filename}
        else:
            # If execute_post returns False, it printed the error to logs
            raise HTTPException(status_code=500, detail="Posting failed. Check server logs.")

    except Exception as e:
        print(f"❌ Manual Post Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))