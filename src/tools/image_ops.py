import os
import uuid
from PIL import Image, ImageFilter

# Ensure /tmp exists
TEMP_DIR = "/tmp"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# --- HARDCODED PATHS ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "src/assets")

WATERMARK_PATH = os.path.join(ASSETS_DIR, "watermark.png")
BOTTOM_FLAIR_PATH = os.path.join(ASSETS_DIR, "bottom.png")


def process_image(image_path: str, max_width: int = 1080) -> str:
    """
    Standardizes image: Convert to RGB, Resize, and Enforce Aspect Ratio.
    """
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            
            # 1. Resize if too big
            if img.width > max_width:
                ratio = max_width / float(img.width)
                new_height = int(float(img.height) * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # 2. SAVE to temp first (so we have a file to work with)
            filename = f"resized_{uuid.uuid4()}.jpg"
            temp_path = os.path.join(TEMP_DIR, filename)
            img.save(temp_path, "JPEG", quality=95)

            # 3. ENFORCE ASPECT RATIO (Smart Padding)
            final_path = validate_and_pad_image(temp_path)
            return final_path
            
    except Exception as e:
        print(f"❌ Error processing image: {e}")
        raise

def validate_and_pad_image(image_path: str) -> str:
    """
    Checks if image fits Instagram ratios (4:5 to 1.91:1).
    If not, pads it with a blurred background to fit 4:5 (vertical) or 1.91:1 (horizontal).
    """
    try:
        with Image.open(image_path) as img:
            w, h = img.size
            aspect_ratio = w / h
            
            # Instagram limits
            MIN_RATIO = 0.8  # 4:5 (Tallest allowed)
            MAX_RATIO = 1.91 # Landscape
            
            # If it fits, return original
            if MIN_RATIO <= aspect_ratio <= MAX_RATIO:
                return image_path
            
            print(f"⚠️ Image ratio {aspect_ratio:.2f} invalid. Applying smart padding...")
            
            # Calculate new canvas size
            if aspect_ratio < MIN_RATIO:
                # Too Tall (e.g. 9:16) -> Make it 4:5
                new_h = h
                new_w = int(h * MIN_RATIO)
            else:
                # Too Wide -> Make it 1.91:1
                new_w = w
                new_h = int(w / MAX_RATIO)
                
            # Create Blur Background
            background = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            background = background.filter(ImageFilter.GaussianBlur(radius=50))
            
            # Center original image on background
            bg_w, bg_h = background.size
            offset = ((bg_w - w) // 2, (bg_h - h) // 2)
            background.paste(img, offset)
            
            # Save
            output_filename = f"padded_{uuid.uuid4()}.jpg"
            output_path = os.path.join(TEMP_DIR, output_filename)
            background.save(output_path, "JPEG", quality=95)
            
            return output_path

    except Exception as e:
        print(f"❌ Padding Error: {e}")
        return image_path
    
def apply_branding(base_image_path: str) -> str:
    """
    Applies the bottom flair and top-right logo.
    """
    try:
        base_img = Image.open(base_image_path).convert("RGB")
        base_w, base_h = base_img.size
        
        # 1. Apply Bottom Flair
        if os.path.exists(BOTTOM_FLAIR_PATH):
            flair = Image.open(BOTTOM_FLAIR_PATH).convert("RGBA")
            # Resize to match width
            flair_aspect = flair.height / flair.width
            new_flair_h = int(base_w * flair_aspect)
            flair = flair.resize((base_w, new_flair_h), Image.Resampling.LANCZOS)
            # Paste at bottom
            base_img.paste(flair, (0, base_h - new_flair_h), flair)

        # 2. Apply Logo
        if os.path.exists(WATERMARK_PATH):
            logo = Image.open(WATERMARK_PATH).convert("RGBA")
            # Resize to 15% width
            target_w = int(base_w * 0.15)
            logo_aspect = logo.height / logo.width
            target_h = int(target_w * logo_aspect)
            logo = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)
            # Paste top right
            padding = int(base_w * 0.02) # 2% padding
            base_img.paste(logo, (base_w - target_w - padding, padding), logo)
        # 3. Save
        filename = f"branded_{uuid.uuid4()}.jpg"
        output_path = os.path.join(TEMP_DIR, filename)
        base_img.save(output_path, "JPEG", quality=95)
        
        return output_path

    except Exception as e:
        print(f"❌ Branding Error: {e}")
        raise