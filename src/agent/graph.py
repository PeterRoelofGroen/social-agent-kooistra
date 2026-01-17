from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph, END

# Import tools
from src.tools.image_ops import process_image, apply_branding
from src.agent.gemini_client import generate_social_post
from src.agent.prompts import KOOISTRA_PROMPT

# 1. Define the State
class AgentState(TypedDict):
    input_path: str          # The original file (Image OR Video)
    context_text: str
    is_video: bool           # flag to tell us what mode we are in
    
    # For AI Analysis
    analysis_frame_paths: Optional[List[str]] # List of images for Gemini to "see"
    
    # Outputs
    processed_path: Optional[str] # The final branded file (Image or Video)
    generated_caption: Optional[str]

# 2. Define the Nodes
def processing_node(state: AgentState):
    """
    Handles Branding.
    - If Image: Resize + Brand.
    - If Video: Skip (Branding is done in main.py via video_ops to save state complexity).
    """
    print("--- 1. PROCESSING MEDIA ---")
    
    if state["is_video"]:
        # videos are branded in main.py
        return {"processed_path": state["input_path"]}
    
    else:
        # Resize
        resized = process_image(state["input_path"])

        # Brand
        # NOT USED SO COMMENTED OUT
        #branded = apply_branding(resized)
        
        # For images, the "Analysis Frames" is just the single branded image
        return {
            "processed_path": resized, 
            "analysis_frame_paths": [resized]
        }

def content_generation_node(state: AgentState):
    """Calls Gemini to write the caption using the analysis frames."""
    print("--- 2. GENERATING CAPTION ---")
    
    # If video, state['analysis_frame_paths'] was passed in by main.py (keyframes)
    # If image, it was set by processing_node above (single image)
    
    media_inputs = state.get("analysis_frame_paths", [])
    
    if not media_inputs:
        media_inputs = [state["input_path"]]

    caption = generate_social_post(
        media_paths=media_inputs,
        context_text=state["context_text"],
        prompt_template=KOOISTRA_PROMPT
    )
    return {"generated_caption": caption}

# 3. Build the Graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("process_media", processing_node)
workflow.add_node("generate_caption", content_generation_node)

# Add edges
workflow.set_entry_point("process_media")
workflow.add_edge("process_media", "generate_caption")
workflow.add_edge("generate_caption", END)

# Compile
app = workflow.compile()