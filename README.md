# Social Media AI Agent

An autonomous agent that processes WhatsApp media into professional Instagram and Facebook posts. It handles image resizing, video branding, AI captioning (in Dutch), and approval workflows via a conversational interface.

## Features

*   **Multi-Media Support:** Processes both Images and Videos (.mp4).
*   **Auto-Branding:** Automatically applies overlays (watermark logo and bottom branding bar).
*   **AI Captioning:** Uses Google Gemini 2.5 Flash to analyze media and write captions in specific tones (Technical, Lifestyle, Seasonal, Recruitment).
*   **Approval Workflow:**
    *   Drafts are sent to WhatsApp for review.
    *   Reply with text to edit the caption.
    *   Reply "POST" to publish to Meta.
    *   Reply "CANCEL" to discard.
*   **Meta Integration:** Publishes directly to Instagram Business and Facebook Page feeds.

## Project Structure

socialmedia-agent/
├── assets/                 # Branding files (watermark.png, bottom.png)
├── src/
│   ├── agent/              # AI Logic (LangGraph + Gemini)
│   ├── tools/              # Media processing (Pillow/MoviePy) & API tools
│   └── main.py             # FastAPI Server & Routes
├── .env                    # Environment variables
├── Dockerfile              # Deployment configuration
└── requirements.txt        # Python dependencies

## Setup & Installation

### 1. Prerequisites
*   Python 3.10+
*   FFmpeg (required for video processing)
*   Twilio Account (WhatsApp Sandbox or Live)
*   Google AI Studio API Key
*   Meta Developer Account (Linked to FB Page & IG Business)

### 2. Installation
Clone the repository and install dependencies:

```bash
git clone https://github.com/yourusername/socialmedia-agent.git
cd socialmedia-agent

python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configuration
Create a `.env` file in the root directory:

```ini
# AI
GOOGLE_API_KEY=AIzaSy...

# WhatsApp (Twilio)
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
WHATSAPP_NUMBER=whatsapp:+...

# Meta (Facebook/Instagram)
FB_PAGE_ID=12345...
IG_USER_ID=67890...
META_ACCESS_TOKEN=EAA...

# Server
# Public URL where Twilio can reach your webhook
BASE_URL=https://your-app-url.com
```

### 4. Assets
Ensure the `assets/` folder contains:
*   `watermark.png`
*   `bottom.png`

## Usage

1.  **Start the Server:**
    ```bash
    uvicorn src.main:app --reload
    ```
2.  **Connect Twilio:**
    Configure your Twilio Sandbox webhook to point to: `YOUR_BASE_URL/whatsapp`
3.  **Workflow:**
    *   Send an image or video to the bot via WhatsApp.
    *   Wait for the branded preview and generated caption.
    *   Reply with text to edit the caption if needed.
    *   Reply **POST** to publish to social media.
    *   Reply **TEST** to simulate a publish action (dry run).

## Deployment

The project includes a `Dockerfile` optimized for containerized hosting (Render, Fly.io, etc).

**Build & Run with Docker:**
```bash
docker build -t social-agent .
docker run -p 8000:8000 --env-file .env social-agent
```