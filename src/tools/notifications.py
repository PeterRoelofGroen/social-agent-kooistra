import os
import time
from twilio.rest import Client

def send_whatsapp_preview(to_number: str, image_path: str, caption: str):
    """
    Sends the preview.
    Split strategy: Sends Media first, then Text separately.
    This ensures captions never get lost for Videos.
    """
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    
    # Remove trailing slash from base URL
    base_url = os.environ.get("BASE_URL", "").rstrip("/") 

    if not all([account_sid, auth_token, base_url]):
        print("Missing Twilio credentials or BASE_URL in .env")
        return

    try:
        client = Client(account_sid, auth_token)
        from_number = os.environ.get("WHATSAPP_NUMBER")
        
        filename = os.path.basename(image_path)
        public_media_url = f"{base_url}/static/{filename}"
        
        print(f"Sending preview to {to_number}...")
        print(f"Media Link: {public_media_url}")

        # --- Media ---
        media_msg = client.messages.create(
            from_=from_number,
            to=to_number,
            media_url=[public_media_url]
            # No body here, just the file
        )
        print(f"Media sent! SID: {media_msg.sid}")

        # Short pause to ensure order (WhatsApp sometimes shuffles fast messages)
        time.sleep(1.0)

        # --- Caption ---
        text_msg = client.messages.create(
            from_=from_number,
            to=to_number,
            body=caption
        )
        print(f"Caption sent! SID: {text_msg.sid}")
        
    except Exception as e:
        print(f"Failed to send WhatsApp preview: {e}")