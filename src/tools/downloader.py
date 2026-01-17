import os
import requests
import uuid
import mimetypes
from requests.auth import HTTPBasicAuth

# Ensure /tmp exists
TEMP_DIR = "/tmp"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def download_image_from_url(url: str) -> str:
    """
    Downloads media and saves with the correct extension.
    """
    try:
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        
        auth = None
        if "twilio.com" in url and account_sid and auth_token:
            auth = HTTPBasicAuth(account_sid, auth_token)

        headers = {
            'User-Agent': 'Mozilla/5.0'
        }
        
        # 1. Get the Header first to check content-type
        with requests.get(url, headers=headers, auth=auth, stream=True) as response:
            response.raise_for_status()
            
            # Detect extension
            content_type = response.headers.get('content-type')
            extension = mimetypes.guess_extension(content_type)
            if not extension:
                # Fallback based on content type string 
                if "video" in content_type:
                    extension = ".mp4"
                else:
                    extension = ".jpg"
            
            # Generate filename
            filename = f"whatsapp_{uuid.uuid4()}{extension}"
            file_path = os.path.join(TEMP_DIR, filename)

            # Save file
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        print(f"📥 Downloaded media to: {file_path} ({content_type})")
        return file_path

    except Exception as e:
        print(f"❌ Failed to download media: {e}")
        raise