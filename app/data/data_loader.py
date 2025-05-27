# logistics_ai_project/app/data/data_loader.py

import json
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Define base path for data files relative to this file's location
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DUMMY_LOADS_FILE = os.path.join(DATA_DIR, "dummy_loads.json")
DUMMY_FEEDBACK_FILE = os.path.join(DATA_DIR, "dummy_feedback_log.json")


def get_dummy_loads() -> List[Dict[str, Any]]:
    """Loads dummy load data from a JSON file."""
    try:
        if os.path.exists(DUMMY_LOADS_FILE):
            with open(DUMMY_LOADS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                logger.warning(f"{DUMMY_LOADS_FILE} does not contain a list. Returning empty list.")
        else:
            logger.warning(f"Data file {DUMMY_LOADS_FILE} not found.")
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {DUMMY_LOADS_FILE}")
    except Exception as e:
        logger.error(f"Error reading {DUMMY_LOADS_FILE}: {e}")
    return []


def save_loads(loads_to_save: List[Dict[str, Any]]):
    """Saves the entire list of loads to the JSON file, overwriting previous content."""
    try:
        with open(DUMMY_LOADS_FILE, 'w', encoding='utf-8') as f:
            json.dump(loads_to_save, f, indent=4, ensure_ascii=False)
        logger.info(f"All loads saved to {DUMMY_LOADS_FILE}")
    except Exception as e:
        logger.error(f"Error saving loads to {DUMMY_LOADS_FILE}: {e}")


def delete_load_by_id_from_file(load_id: str) -> bool:
    """
    Deletes a load from the dummy_loads.json file by its ID.
    Returns True if the load was found and deleted, False otherwise.
    """
    current_loads = get_dummy_loads()
    if not current_loads:
        logger.warning("Load list is empty or could not be loaded.")
        return False

    logger.debug(f"Attempting to delete load with ID: {load_id}")
    logger.debug(f"Available load IDs: {[load.get('load_id') for load in current_loads]}")

    # ✅ FIX: Use "load_id" instead of "Load_id"
    updated_loads = [load for load in current_loads if load.get("load_id") != load_id]

    if len(updated_loads) < len(current_loads):
        save_loads(updated_loads)
        logger.info(f"Load with ID '{load_id}' deleted from {DUMMY_LOADS_FILE}.")
        return True
    else:
        logger.warning(f"Load with ID '{load_id}' not found. No changes made.")
        return False


def get_dummy_feedback() -> List[Dict[str, Any]]:
    """Loads dummy feedback data from a JSON file."""
    try:
        if os.path.exists(DUMMY_FEEDBACK_FILE):
            with open(DUMMY_FEEDBACK_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                logger.warning(f"{DUMMY_FEEDBACK_FILE} does not contain a list.")
        else:
            logger.info(f"{DUMMY_FEEDBACK_FILE} not found. Returning empty feedback list.")
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {DUMMY_FEEDBACK_FILE}")
    except Exception as e:
        logger.error(f"Error reading {DUMMY_FEEDBACK_FILE}: {e}")
    return []


def save_dummy_feedback(feedback_entry: Dict[str, Any]):
    """Appends a feedback entry to the JSON file."""
    current_feedback = get_dummy_feedback()
    current_feedback.append(feedback_entry)
    try:
        with open(DUMMY_FEEDBACK_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_feedback, f, indent=4, ensure_ascii=False)
        logger.info(f"Feedback entry saved to {DUMMY_FEEDBACK_FILE}")
    except Exception as e:
        logger.error(f"Error saving feedback to {DUMMY_FEEDBACK_FILE}: {e}")
