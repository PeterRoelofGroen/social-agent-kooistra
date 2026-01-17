import os
import uuid
import PIL.Image
# Bandaid version mismatch fix between pillow and moviepy
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip

# Ensure /tmp exists
TEMP_DIR = "/tmp"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "src/assets")

WATERMARK_PATH = os.path.join(ASSETS_DIR, "watermark.png")
BOTTOM_FLAIR_PATH = os.path.join(ASSETS_DIR, "bottom.png")

def extract_keyframes(video_path: str, num_frames: int = 5) -> list[str]:
    """
    Extracts keyframes from the video to send to Gemini
    """
    print(f"Extracting {num_frames} keyframes...")
    keyframe_paths = []
    try:
        with VideoFileClip(video_path) as clip:
            duration = clip.duration
            timestamps = [duration * (i + 1) / (num_frames + 1) for i in range(num_frames)]
            
            for i, t in enumerate(timestamps):
                filename = f"frame_{uuid.uuid4()}_{i}.jpg"
                output_path = os.path.join(TEMP_DIR, filename)
                clip.save_frame(output_path, t=t)
                keyframe_paths.append(output_path)
        return keyframe_paths
    except Exception as e:
        print(f"Error extracting frames: {e}")
        return []

def brand_video(video_path: str) -> str:
    print(f"Starting video branding on: {video_path}")
    
    try:
        video = VideoFileClip(video_path)
        w, h = video.size
        overlays = [video]

        # 1. BOTTOM FLAIR
        if os.path.exists(BOTTOM_FLAIR_PATH):
            flair = ImageClip(BOTTOM_FLAIR_PATH)
            # Resize width to match video, maintain aspect ratio
            flair_new_h = int(w * (flair.h / flair.w))
            flair = flair.resize(width=w, height=flair_new_h)
            # Position: Center Bottom, Duration: Full Video
            flair = flair.set_position(("center", "bottom")).set_duration(video.duration)
            overlays.append(flair)
        else:
            print("Bottom flair asset not found")

        # 2. LOGO
        if os.path.exists(WATERMARK_PATH):
            logo = ImageClip(WATERMARK_PATH)
            # Resize to 15% width
            target_w = int(w * 0.15)
            target_h = int(target_w * (logo.h / logo.w))
            logo = logo.resize(width=target_w, height=target_h)
            # Position: Top Right with padding
            padding = 20
            logo = logo.set_position((w - target_w - padding, padding)).set_duration(video.duration)
            overlays.append(logo)
        else:
            print("Watermark asset not found")

        # 3. WRITE FILE
        final = CompositeVideoClip(overlays)
        output_filename = f"branded_video_{uuid.uuid4()}.mp4"
        output_path = os.path.join(TEMP_DIR, output_filename)
        
        # Use preset='ultrafast' for speed, audio=True for sound
        final.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac", 
            temp_audiofile=os.path.join(TEMP_DIR, "temp-audio.m4a"),
            remove_temp=True,
            preset="ultrafast", 
            fps=24,
            logger=None
        )
        
        print(f"Video branding complete: {output_path}")
        return output_path

    except Exception as e:
        print(f"Error branding video: {e}")
        raise