import requests
import os

# --- CONFIGURATION ---
# 1. Point this to your running server
# Local: "http://localhost:8000/manual-post"
# Render: "https://socialmedia-agent.onrender.com/manual-post"
API_URL = "https://socialmedia-agent.onrender.com/manual-post" 

# 2. The local file you want to upload
IMAGE_PATH = "src/assets/test1.jpeg" 

# 3. Your Caption
CAPTION = """
De week is weer in bijna voorbij, maar wij staan gewoon voor u klaar! 🤩 Vanavond ook weer op koopavond geopend!

Op zoek naar de nieuwste upgrade? Goed nieuws! De iPhone 17 en iPhone 17 Pro zijn nog steeds direct leverbaar. Kom gezellig langs in onze winkel in Dokkum om ze zelf te ervaren of haal direct uw nieuwe toestel op.

We helpen u graag met deskundig advies!

#Audiocom #Dokkum #iPhone17 #iPhone17Pro #DirectLeverbaar #Telefoon #Elektronica #KomGezelligLangs
"""

# 4. Set to True to test the connection without actually posting to Meta
DRY_RUN = False 

def run():
    print(f"🚀 Starting Manual Upload...")
    print(f"TARGET: {API_URL}")
    print(f"FILE:   {IMAGE_PATH}")
    
    # Check if file exists
    if not os.path.exists(IMAGE_PATH):
        print(f"❌ Error: File not found at {IMAGE_PATH}")
        return

    # Open the file in binary mode
    with open(IMAGE_PATH, "rb") as f:
        # Prepare the payload
        files = {"file": f}
        data = {
            "caption": CAPTION,
            "dry_run": str(DRY_RUN) # Send as string, FastAPI converts it
        }
        
        try:
            # Send POST request
            print("⏳ Uploading to server...")
            response = requests.post(API_URL, files=files, data=data)
            
            # Print Result
            if response.status_code == 200:
                print("\n✅ SUCCESS!")
                print(response.json())
            else:
                print(f"\n❌ FAILED (Status {response.status_code})")
                print("Response:", response.text)
                
        except requests.exceptions.ConnectionError:
            print("\n❌ Error: Could not connect to the server.")
            print("   - Is main.py running?")
            print("   - Did you check the API_URL?")
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    run()