from fastapi import APIRouter, HTTPException, Body
import logging
from typing import Dict, Any,List

from app.services.openai_client import get_openai_agent_answer
from app.data.data_loader import get_dummy_loads

logger = logging.getLogger(__name__)
router = APIRouter()

def flatten_loads_data(raw_data: List[Any]) -> List[Dict[str, Any]]:
    """
    Flattens a potentially nested list structure read from the JSON file.
    Handles cases like [{}, [{}, {}], {}] into [{}, {}, {}, {}].
    """
    flattened_list = []
    if not isinstance(raw_data, list):
        logger.warning("Data read from file is not a list. Returning empty list for loads.")
        return []

    for item_or_sublist in raw_data:
        if isinstance(item_or_sublist, list):
            for load_item in item_or_sublist:
                if isinstance(load_item, dict):
                    flattened_list.append(load_item)
                else:
                    logger.warning(f"Skipping non-dictionary item in sublist: {type(load_item)}")
        elif isinstance(item_or_sublist, dict):
            flattened_list.append(item_or_sublist)
        else:
            logger.warning(f"Skipping non-dictionary, non-list item in main list: {type(item_or_sublist)}")
    return flattened_list

@router.post("/ask-agent", summary="Ask a question to the logistics AI agent")
def ask_agent_endpoint(payload: Dict[str, Any] = Body(...)) -> dict:
    """
    Asks a logistics question to the AI agent.
    Expects a JSON payload like: {"question": "your question here"}
    """
    question = payload.get("question")

    if not question:
        raise HTTPException(status_code=400, detail="A 'question' field is required in the payload.")

    # Load and flatten data to ensure it's a list of dictionaries
    raw_loads_from_file = get_dummy_loads()
    all_available_loads = flatten_loads_data(raw_loads_from_file)
    
    logger.debug(f"Number of loads after flattening: {len(all_available_loads)}")
    if all_available_loads:
        logger.debug(f"First load item type after flattening: {type(all_available_loads[0])}")

    recent_loads_for_context = all_available_loads[-5:] if all_available_loads else []
    logger.debug(f"Recent loads for context count: {len(recent_loads_for_context)}")

    context_loads_serializable = []
    for load in recent_loads_for_context:
        if isinstance(load, dict):
            context_loads_serializable.append(dict(load))  # Creates a shallow copy
        else:
            logger.warning(f"Skipping non-dictionary item in recent_loads_for_context: {type(load)}")

    logger.debug(f"Context loads being sent to agent: {context_loads_serializable}")

    # Call OpenAI agent without truck_id
    answer = get_openai_agent_answer(question, context_loads_serializable)

    if answer is None:
        logger.error(f"Failed to get an answer from the AI agent for question '{question}'. Check OpenAI client logs.")
        raise HTTPException(status_code=500, detail="Failed to get an answer from the AI agent. Please check server logs.")

    return {"answer": answer}
