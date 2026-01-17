import os
import time
from typing import List, Union
from google import genai
from google.genai import types

# Initialize client
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

def generate_social_post(media_paths: Union[str, List[str]], context_text: str, prompt_template: str):
    """
    Uploads one or multiple images/frames to Gemini and generates a caption.
    """
    print(f"Uploading media to Gemini...")
    
    # 1. Normalize input to a list
    if isinstance(media_paths, str):
        media_paths = [media_paths]
        
    uploaded_files = []
    
    # 2. Upload all files
    try:
        for path in media_paths:
            # Check if file exists
            if not os.path.exists(path):
                print(f"Warning: File not found {path}, skipping.")
                continue
                
            # Upload
            print(f"   - Uploading: {os.path.basename(path)}")
            file_obj = client.files.upload(file=path)
            uploaded_files.append(file_obj)
            
            # Small delay to ensure Google processes it (rarely needed but safer)
            time.sleep(0.5)

        if not uploaded_files:
            return "Error: No media files could be uploaded."

        # 3. Construct the prompt
        # We pass the list of file objects AND the text prompt
        contents = uploaded_files + [f"{prompt_template}\n\nEXTRA CONTEXT:\n{context_text}"]

        print("Generating content...")
        
        # 4. Call the model
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.7
            )
        )

        return response.text

    except Exception as e:
        print(f"Gemini Error: {e}")
        return "Error generating caption. Please try again."