from app.data.data_loader import save_loads,get_dummy_loads
from fastapi import APIRouter, HTTPException, Body
import logging
from typing import Dict, Any, List
import re

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
                    logger.warning(f"Skipping non-dictionary item in sublist: {load_item}")
        elif isinstance(item_or_sublist, dict):
            flattened_list.append(item_or_sublist)
        else:
            logger.warning(f"Skipping non-dictionary, non-list item in main list: {item_or_sublist}")
    return flattened_list



from fastapi import HTTPException
from fastapi.responses import JSONResponse

@router.post("/add-load", summary="Add a new logistics load")
async def add_load(payload: Dict[str, Any] = Body(...)) -> dict:
    required_fields = [
        "pickup_point", "destination", "rate", "cargo_type",
        "weight_tons", "expected_delivery_date"
    ]

    for field in required_fields:
        if field not in payload:
            raise HTTPException(
                status_code=400,
                detail={"status": False, "message": f"Missing field: {field}"}
            )

    # --- Rate Processing and Formatting ---
    rate_input_str = payload.get("rate")
    if not isinstance(rate_input_str, str):
        if isinstance(rate_input_str, (int, float)):
            rate_input_str = str(rate_input_str)
        else:
            raise HTTPException(
                status_code=400,
                detail={"status": False, "message": "Field 'rate' must be a string or number representing the rate amount (e.g., '26', 28.5)."}
            )

    try:
        numeric_rate = float(rate_input_str)
        if numeric_rate < 0:
            raise HTTPException(
                status_code=400,
                detail={"status": False, "message": "Field 'rate' must be a non-negative number."}
            )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"status": False, "message": f"Field 'rate' ('{rate_input_str}') is not a valid number. Please provide a numeric value (e.g., '26', '28.5')."}
        )

    if numeric_rate == int(numeric_rate): 
        formatted_rate_string = f"₹{int(numeric_rate)}/km"
    else:
        formatted_rate_string = f"₹{numeric_rate:.2f}/km"

    try:
        weight = float(payload["weight_tons"])
    except (ValueError, TypeError): 
        raise HTTPException(
            status_code=400,
            detail={"status": False, "message": "Field 'weight_tons' must be a valid number."}
        )
    if weight < 0: 
        raise HTTPException(
            status_code=400,
            detail={"status": False, "message": "Field 'weight_tons' must be non-negative."}
        )

    raw_loads_from_file = get_dummy_loads()
    current_loads = flatten_loads_data(raw_loads_from_file)

    numeric_ids = []
    for load in current_loads:
        if isinstance(load, dict) and "load_id" in load:
            lid = load.get("load_id")
            if lid:
                match = re.match(r"[A-Za-z]*(\d+)", str(lid))
                if match:
                    numeric_ids.append(int(match.group(1)))

    max_id_num = max(numeric_ids) if numeric_ids else 100
    
    new_id_num = max_id_num + 1
    new_load_id = f"L{new_id_num}"

    new_load = {
        "load_id": new_load_id,
        "pickup_point": payload["pickup_point"],
        "destination": payload["destination"],
        "rate": formatted_rate_string,  
        "status": payload.get("status", "available"),
        "cargo_type": payload["cargo_type"],
        "weight_tons": weight,
        "expected_delivery_date": payload["expected_delivery_date"]
    }

    current_loads.append(new_load)
    save_loads(current_loads)

    # Modified response includes boolean 'status' true on success
    return {"status": True, "message": "Load added successfully", "load": new_load}
