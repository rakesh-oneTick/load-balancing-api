

# logistics_ai_project/app/services/openai_client.py
import openai
import json
import logging
from typing import Dict, List, Optional, Any
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI client if API key is available
if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your-dummy-openai-key":
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
else:
    client = None
    logger.warning("OpenAI API key is a dummy or not configured. OpenAI client not initialized.")

def get_openai_summary(truck_info: Dict[str, Any], top_loads_data: List[Dict[str, Any]]) -> Optional[str]:
    """Generates a summary recommendation using OpenAI."""
    if client is None:
        return "OpenAI API key not set. Mock summary: Consider the load with the highest score and lowest detour."

    prompt = (
        f"Truck details: Current Location Lat/Lng ({truck_info.get('latitude')},{truck_info.get('longitude')}), "
        f"Capacity: {truck_info.get('capacity')} tons. Based on the following top {len(top_loads_data)} potential loads, "
        f"provide a concise recommendation for the driver. Prioritize loads with high scores, minimal detours, "
        f"and compatibility with truck capacity. Explain your top choice briefly.\n\n"
        f"Top Loads (with scores and detour info):\n{json.dumps(top_loads_data, indent=2)}\n\n"
        f"Recommendation:"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o", # Or "gpt-4" if you have access and prefer it
            messages=[
                {"role": "system", "content": "You are an expert logistics assistant providing clear, actionable advice to truck drivers."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI summary generation failed: {e}", exc_info=True)
        return None

def get_openai_agent_answer(question: str, recent_loads_data: List[Dict[str, Any]]) -> Optional[str]:
    """Gets an answer from OpenAI acting as a logistics expert without truck context."""

    if client is None:
        logger.warning("OpenAI API key not set. Returning mock agent answer.")
        return "OpenAI API key not set. Mock answer: I can help with logistics questions if properly configured."

    # Since truck_id is removed, we consider all recent loads directly
    prompt = (
        f"You are a logistics expert assisting with a question:\n"
        f"{question}\n\n"
        f"Here are some recent loads that might be relevant:\n"
        f"{json.dumps(recent_loads_data, indent=2)}\n\n"
        f"Answer:"
    )
    # logger.info(f"OpenAI Agent Prompt: {prompt}")

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful logistics expert."},
                {"role": "user", "content": prompt}
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI agent answer failed: {e}", exc_info=True)
        return None
    

    
def get_truck_capacity(truck_id: str) -> int:
    # In a real application, you would fetch this from a database or in-memory store
    if truck_id == "T123":
        return 15
    elif truck_id == "T456":
        return 10
    else:
        return 0 # Default or handle error appropriately