import os
import requests
import time

# --- CONFIGURATION FROM ENV ---
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
IG_USER_ID = os.environ.get("IG_USER_ID")
META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN") # <--- Using Env Var
BASE_URL = os.environ.get("BASE_URL", "https://localhost:8000").rstrip("/")

def get_auth_headers():
    """Injects the Env Var Token into the header"""
    if not META_ACCESS_TOKEN:
        raise ValueError("❌ Missing META_ACCESS_TOKEN in environment variables.")
    return {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}"
    }

def execute_post(media_path: str, caption: str, dry_run: bool = False):
    """
    Orchestrator: Generates public URL -> Posts to FB & IG
    """
    # 1. Generate the Public URL so Meta can download the file
    filename = os.path.basename(media_path)
    public_url = f"{BASE_URL}/static/{filename}"
    
    is_video = media_path.lower().endswith(".mp4")

    print(f"🚀 Starting Upload Process")
    print(f"📂 Local: {media_path}")
    print(f"ww Public: {public_url}")

    if is_video:
        fb = post_video_to_facebook(public_url, caption, dry_run)
        ig = post_reel_to_instagram(public_url, caption, dry_run)
    else:
        fb = post_to_facebook(public_url, caption, dry_run)
        ig = post_to_instagram(public_url, caption, dry_run)

    return fb and ig

# --- FACEBOOK FUNCTIONS ---

def post_to_facebook(media_path_or_url: str, caption: str, dry_run: bool = False):
    """
    Uploads PHOTO to Facebook. 
    Tries Local File upload first (Reliable), falls back to URL.
    Returns the 'post_id' (str) on success, or False on failure.
    """
    endpoint = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/photos"
    
    # 1. Check if it is a local file
    files = None
    payload = {
        "caption": caption,
        "published": "true"
    }

    if os.path.exists(media_path_or_url):
        # BINARY UPLOAD (Reliable)
        files = {
            'source': open(media_path_or_url, 'rb')
        }
    else:
        # URL UPLOAD (Fallback)
        payload['url'] = media_path_or_url

    if dry_run:
        print(f"[DRY RUN] FB Photo: {media_path_or_url}")
        return "DRY_RUN_ID_123"

    print(f"Sending request to Facebook API (Mode: {'Binary' if files else 'URL'})...")
    try:
        # Note: When using 'files', do NOT use json=payload, use data=payload
        if files:
            response = requests.post(endpoint, data=payload, files=files, headers=get_auth_headers())
        else:
            response = requests.post(endpoint, json=payload, headers=get_auth_headers())
            
        response.raise_for_status()
        post_id = response.json().get('id')
        print(f"✅ Facebook Posted! ID: {post_id}")
        return post_id
    except Exception as e:
        print(f"❌ Facebook Error: {e}")
        if 'response' in locals(): print(response.text)
        return False

def get_fb_picture_url(photo_id: str):
    """
    Helper: Gets the source URL of a photo already uploaded to Facebook.
    Used to give Instagram a reliable URL.
    """
    endpoint = f"https://graph.facebook.com/v21.0/{photo_id}"
    params = {
        "fields": "images",
    }
    try:
        response = requests.get(endpoint, params=params, headers=get_auth_headers())
        data = response.json()
        # Get the largest image source (usually the first one)
        return data['images'][0]['source']
    except Exception as e:
        print(f"❌ Failed to get FB Source URL: {e}")
        return None
def post_video_to_facebook(video_url: str, caption: str, dry_run: bool = False):
    endpoint = f"https://graph-video.facebook.com/v21.0/{FB_PAGE_ID}/videos"
    payload = {"file_url": video_url, "description": caption}

    if dry_run: return True

    try:
        response = requests.post(endpoint, json=payload, headers=get_auth_headers())
        response.raise_for_status()
        print(f"✅ FB Video Posted: {response.json().get('id')}")
        return True
    except Exception as e:
        print(f"❌ FB Video Error: {e}")
        return False

# --- INSTAGRAM FUNCTIONS ---

def post_to_instagram(image_url: str, caption: str, dry_run: bool = False):
    create_url = f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media"
    publish_url = f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish"

    if dry_run:
        print(f"[DRY RUN] IG Photo: {image_url}")
        return True

    # Step 1: Create Container
    for i in range(10):
        time.sleep(2)
        try:
            payload = {"image_url": image_url, "caption": caption}
            req1 = requests.post(create_url, json=payload, headers=get_auth_headers())
            if req1.status_code != 200:
                print(f"❌ IG Create Error: {req1.text}")
                return False
            creation_id = req1.json().get("id")
        except Exception as e:
            print(f"❌ IG Net Error: {e}")
            return False
    
    # Step 2: Publish Container
    try:
        req2 = requests.post(publish_url, json={"creation_id": creation_id}, headers=get_auth_headers())
        req2.raise_for_status()
        print(f"✅ Instagram Posted: {req2.json().get('id')}")
        return True
    except Exception as e:
        print(f"❌ IG Publish Error: {e}")
        return False

def post_reel_to_instagram(video_url: str, caption: str, dry_run: bool = False):
    # Same logic as above but with media_type='REELS' and polling
    create_url = f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media"
    publish_url = f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish"

    if dry_run: return True

    try:
        payload = {"media_type": "REELS", "video_url": video_url, "caption": caption}
        req1 = requests.post(create_url, json=payload, headers=get_auth_headers())
        creation_id = req1.json().get("id")
    except Exception as e:
        print(f"❌ IG Reel Error: {e}")
        return False

    # Poll status
    print("⏳ Waiting for IG processing...")
    status_url = f"https://graph.facebook.com/v21.0/{creation_id}"
    for _ in range(20):
        time.sleep(5)
        r = requests.get(status_url, params={"fields": "status_code"}, headers=get_auth_headers())
        status = r.json().get("status_code")
        if status == "FINISHED": break
        if status == "ERROR": return False
    
    # Publish
    try:
        req2 = requests.post(publish_url, json={"creation_id": creation_id}, headers=get_auth_headers())
        print(f"✅ IG Reel Posted: {req2.json().get('id')}")
        return True
    except Exception as e:
        print(f"❌ IG Reel Publish Error: {e}")
        return False