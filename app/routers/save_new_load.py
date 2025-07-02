from app.data.data_loader import save_loads,get_dummy_loads
from fastapi import APIRouter, HTTPException, Body,File, UploadFile
import logging
from typing import Dict, Any, List
import re
import pandas as pd
from io import BytesIO 

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




@router.post("/upload-loads-excel", summary="Upload loads from an Excel file")
async def upload_loads_excel(file: UploadFile = File(...)): # Assuming this function is used

    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail={"status": False, "message": "Invalid file type. Please upload an Excel file (.xlsx or .xls)."})

    try:
        contents = await file.read()
        excel_data = pd.read_excel(BytesIO(contents))
        excel_data = excel_data.where(pd.notnull(excel_data), None)
    except Exception as e:
        logger.error(f"Error reading Excel file: {e}")
        raise HTTPException(status_code=400, detail={"status": False, "message": f"Error processing Excel file: {str(e)}"})

    required_excel_columns = [
        "pickup_point", "destination", "rate", "cargo_type",
        "weight_tons", "expected_delivery_date"
    ]

    for col in required_excel_columns:
        if col not in excel_data.columns:
            raise HTTPException(
                status_code=400,
                detail={"status": False, "message": f"Missing required column in Excel file: {col}"}
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
    next_id_num = max_id_num + 1

    newly_added_loads = []
    processing_errors = []

    for index, row in excel_data.iterrows():
        try:
            load_data = row.to_dict()

            missing_fields_in_row = [
                field for field in required_excel_columns
                if pd.isna(load_data.get(field)) or load_data.get(field) == ''
            ]
            if missing_fields_in_row:
                processing_errors.append({"row": index + 2, "error": f"Missing data for fields: {', '.join(missing_fields_in_row)}"})
                continue

            # --- Rate Processing ---
            rate_input = load_data.get("rate")

            if isinstance(rate_input, (int, float)):
                rate_input_str = str(rate_input)
            elif isinstance(rate_input, str):
                rate_input_str = rate_input
            else:
                processing_errors.append({"row": index + 2, "field": "rate", "error": "Rate must be a number or string."})
                continue

            try:
                numeric_rate = float(re.sub(r'[^\d.]', '', rate_input_str))
                if numeric_rate < 0:
                    processing_errors.append({"row": index + 2, "field": "rate", "error": "Rate must be non-negative."})
                    continue
            except ValueError:
                processing_errors.append({"row": index + 2, "field": "rate", "error": f"Invalid rate format: '{rate_input}'. Expected a number."})
                continue

            # ✅ Convert rate to "₹25/km" or "₹25.50/km"
            if numeric_rate == int(numeric_rate):
                formatted_rate_string = f"₹{int(numeric_rate)}/km"
            else:
                formatted_rate_string = f"₹{numeric_rate:.2f}/km"

            # --- Weight Processing ---
            try:
                weight = float(load_data["weight_tons"])
                if weight < 0:
                    processing_errors.append({"row": index + 2, "field": "weight_tons", "error": "Weight must be non-negative."})
                    continue
            except (ValueError, TypeError):
                processing_errors.append({"row": index + 2, "field": "weight_tons", "error": "Weight must be a valid number."})
                continue

            # --- Expected Delivery Date Processing ---
            expected_delivery_date_input = load_data["expected_delivery_date"]
            if isinstance(expected_delivery_date_input, pd.Timestamp):
                formatted_delivery_date = expected_delivery_date_input.strftime('%Y-%m-%d')
            elif isinstance(expected_delivery_date_input, str):
                formatted_delivery_date = expected_delivery_date_input
            else:
                processing_errors.append({"row": index + 2, "field": "expected_delivery_date", "error": "Invalid date format."})
                continue

            new_load_id = f"L{next_id_num}"
            next_id_num += 1

            new_load_entry = {
                "load_id": new_load_id,
                "pickup_point": str(load_data["pickup_point"]),
                "destination": str(load_data["destination"]),
                "rate": formatted_rate_string,
                "status": str(load_data.get("status", "available")),
                "cargo_type": str(load_data["cargo_type"]),
                "weight_tons": weight,
                "expected_delivery_date": formatted_delivery_date
            }
            current_loads.append(new_load_entry)
            newly_added_loads.append(new_load_entry)

        except Exception as e:
            logger.error(f"Error processing row {index + 2} from Excel: {e}")
            processing_errors.append({"row": index + 2, "error": f"Unexpected error: {str(e)}"})
            continue

    if newly_added_loads:
        save_loads(current_loads)

    return {
        "status": True,
        "message": f"Processed Excel file. Added {len(newly_added_loads)} loads.",
        "added_loads": newly_added_loads,
        "errors": processing_errors
    }



@router.get("/get-all-loads", summary="Retrieve all available logistics loads")
async def get_all_loads() -> Dict[str, Any]:
    """
    Retrieves all logistics loads from the dummy data storage.
    """
    try:
        raw_loads = get_dummy_loads()
        loads = flatten_loads_data(raw_loads)
        return {"status": True, "message": "Loads retrieved successfully", "loads": loads}
    except Exception as e:
        logger.error(f"Error retrieving all loads: {e}")
        raise HTTPException(status_code=500, detail={"status": False, "message": f"Failed to retrieve loads: {str(e)}"})
