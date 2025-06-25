import logging
from typing import List, Dict, Any
from app.models import Truck
from app.services.Maps import get_route_eta_distance 
import requests
from dotenv import load_dotenv
import os
load_dotenv()


logger = logging.getLogger(__name__)

def score_loads(
    truck: Truck,
    all_loads_data: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Scores loads based on various factors including detour, rate, and urgency.
    Filters loads based on truck capacity.
    Applies fuel penalty by dividing by 100 and time penalty by dividing by 60.

    Args:
        truck: The Truck object representing the vehicle.
               IMPORTANT: This truck object is expected to already have
               'latitude', 'longitude', and 'capacity' attributes populated
               by the caller (e.g., the /recommend endpoint after geocoding).
        all_loads_data: A list of dictionaries, where each dictionary
                        represents a load with keys like 'load_id',
                        'weight_tons', 'rate', 'status', 'pickup_point'
                        or 'origin', 'destination'.

    Returns:
        A list of dictionaries, each containing the cleaned original 'load' data,
        its calculated 'score', and 'detour' information.
    """
    scored_and_filtered_loads = []

    truck_current_address = truck.location

    if not truck_current_address:
        truck_id_for_log = getattr(truck, 'truck_id', 'N/A')
        logger.error(
            f"Truck (ID: {truck_id_for_log}) is missing 'current_location_address'. "
            f"Cannot proceed with scoring."
        )
        return []
    
    # service = GoogleLocationService()
    # origin_coords_result = service.get_coordinates(truck_current_address)
    origin_coords_result = get_coordinates(truck_current_address)

    if not origin_coords_result["status"] or origin_coords_result["latitude"] is None or origin_coords_result["longitude"] is None:
        truck_id_for_log = getattr(truck, 'truck_id', 'N/A')
        logger.error(
            f"Failed to get coordinates for truck's current location '{truck_current_address}' (Truck ID: {truck_id_for_log}). "
            f"Error: {origin_coords_result.get('message', 'Unknown error')}. Cannot proceed with scoring."
        )
        return []

    truck_origin_lat = origin_coords_result["latitude"]
    truck_origin_lng = origin_coords_result["longitude"]


    # Basic validation for the truck's coordinates
    if truck_origin_lat is None or truck_origin_lng is None:
        # Include truck_id for better logging if available, otherwise just 'N/A'
        truck_id_for_log = getattr(truck, 'truck_id', 'N/A')
        logger.error(
            f"Truck (ID: {truck_id_for_log}) passed to score_loads is missing latitude or longitude. "
            f"This indicates an issue in the calling function. Cannot proceed with scoring."
        )
        return []


    for load_item in all_loads_data:
        current_load = dict(load_item)
        load_id = current_load.get('load_id', 'N/A')

        # --- Rate Cleaning and Type Conversion ---
        if "rate" in current_load and isinstance(current_load["rate"], str):
            # Replacing common currency symbols and stripping whitespace
            current_load["rate"] = current_load["rate"].replace("â‚¹", "₹").replace("Rs.", "₹").strip()

        # --- Capacity Check ---
        load_weight_tons = current_load.get("weight_tons")
        if isinstance(load_weight_tons, (int, float)):
            if load_weight_tons > truck.capacity:
                logger.info(
                    f"Load {load_id} (Weight: {load_weight_tons}t) "
                    f"exceeds truck capacity ({truck.capacity}t). Skipping."
                )
                continue
        else:
            logger.warning(
                f"Load {load_id} has missing or invalid 'weight_tons' ('{load_weight_tons}'). "
                f"Proceeding without capacity check for this load (assuming non-blocking)."
            )

        # --- Address Extraction and Validation (for load's pickup/drop-off) ---
        pickup_address = current_load.get("pickup_point") or current_load.get("origin")
        drop_address = current_load.get("destination")

        if not pickup_address or not drop_address:
            logger.warning(f"Load {load_id} is missing pickup ('{pickup_address}') or destination ('{drop_address}') address. Skipping.")
            continue

        # --- Detour Calculation ---
        # This uses the truck's already resolved origin coordinates
        detour_info = get_route_eta_distance(
            origin_lat=truck_origin_lat,
            origin_lng=truck_origin_lng,
            pickup_address=pickup_address,
            drop_address=drop_address
        )

        if not detour_info:
            logger.info(f"Skipping load {load_id} due to detour calculation failure (e.g., invalid addresses or API error).")
            continue

        # --- Rate Value Parsing ---
        rate_value = 0.0
        rate_str_cleaned = current_load.get("rate", "₹0/km")

        try:
            rate_value_str = rate_str_cleaned.replace("₹", "").replace("/km", "").strip()
            rate_value = float(rate_value_str)

            if rate_value < 0:
                logger.warning(f"Parsed negative rate value for load {load_id}: '{rate_str_cleaned}'. Using 0.0 for scoring.")
                rate_value = 0.0
        except ValueError as e:
            logger.warning(f"Rate parsing ValueError for load {load_id}: '{rate_str_cleaned}'. Error: {e}. Using 0.0.")
            rate_value = 0.0
        except Exception as e:
            logger.warning(f"Unexpected rate parse error for load {load_id} ('{rate_str_cleaned}'): {e}. Using 0.0.")
            rate_value = 0.0

        # --- Score Calculation (Using /100 for fuel and /60 for time, as requested) ---
        score = rate_value # Base score from rate per km

        # Bonus for urgency
        if "urgent" in current_load.get("status", "").lower():
            score += 2.0

        # Fuel Penalty
        fuel_penalty = 0.0
        detour_fuel_cost = detour_info.get("fuel_cost", 0.0)
        if isinstance(detour_fuel_cost, (int, float)) and detour_fuel_cost > 0:
            fuel_penalty = detour_fuel_cost / 100.0 # Penalty based on fuel cost

        # Time Penalty
        time_penalty = 0.0
        detour_extra_min = detour_info.get("extra_min", 0.0)
        if isinstance(detour_extra_min, (int, float)) and detour_extra_min > 0:
            time_penalty = detour_extra_min / 60.0 # Penalty based on extra time in minutes

        score -= fuel_penalty
        score -= time_penalty

        logger.debug(
            f"Load {load_id} -> Base Rate: {rate_value:.2f}, "
            f"Urgency Bonus: {2.0 if 'urgent' in current_load.get('status', '').lower() else 0.0:.2f}, "
            f"Fuel Penalty: -{fuel_penalty:.2f}, Time Penalty: -{time_penalty:.2f}, "
            f"Final Score: {score:.2f}"
        )

        scored_and_filtered_loads.append({
            "load": current_load,
            "score": round(score, 2), # Round the final score for consistency
            "detour": detour_info
        })

    return scored_and_filtered_loads



def get_coordinates(location: str) -> dict:
    """
    Returns latitude and longitude for a given address or pincode.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": location,
        "key": api_key
    }
    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        return {
            "status": False,
            "message": "Request to Google API failed",
            "latitude": None,
            "longitude": None
        }
    data = response.json()
    if data.get("status") != "OK" or not data.get("results"):
        return {
            "status": False,
            "message": f"Could not find coordinates for location: {location}",
            "latitude": None,
            "longitude": None
        }
    location_data = data["results"][0]["geometry"]["location"]
    formatted_address = data["results"][0]["formatted_address"]
    return {
        "status": True,
        "message": "Location coordinates fetched successfully",
        "location": formatted_address,
        "latitude": location_data["lat"],
        "longitude": location_data["lng"]
    }



# def score_loads(truck: Truck, all_loads_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#     """
#     Scores loads based on various factors including detour, rate, and urgency.
#     Filters loads based on truck capacity.

#     Args:
#         truck: The Truck object representing the vehicle.
#         all_loads_data: A list of dictionaries, where each dictionary
#                         represents a load with keys like 'load_id',
#                         'weight_tons', 'rate', 'status', 'pickup_point'
#                         or 'origin', 'destination'.

#     Returns:
#         A list of dictionaries, each containing the cleaned original 'load' data,
#         its calculated 'score', and 'detour' information.
#     """
#     scored_and_filtered_loads = []
#     for load_item in all_loads_data:
#         current_load = dict(load_item)
#         load_id = current_load.get('load_id', 'N/A') # Get ID early for logging

#         if "rate" in current_load and isinstance(current_load["rate"], str):
#             current_load["rate"] = current_load["rate"].replace("â‚¹", "₹").replace("Rs.", "₹").strip()

#         load_weight_tons = current_load.get("weight_tons")
#         if load_weight_tons is not None and isinstance(load_weight_tons, (int, float)):
#             if load_weight_tons > truck.capacity:
#                 logger.info(
#                     f"Load {load_id} (Weight: {load_weight_tons}t) "
#                     f"exceeds truck {truck.truck_id} capacity ({truck.capacity}t). Skipping."
#                 )
#                 continue # Skip this load
#         else:
#             logger.warning(
#                 f"Load {load_id} has missing or invalid 'weight_tons' ('{load_weight_tons}'). "
#                 f"Proceeding without capacity check for this load."
#             )


#         pickup_address = current_load.get("pickup_point") or current_load.get("origin")
#         drop_address = current_load.get("destination")

#         if not pickup_address or not drop_address:
#              logger.warning(f"Load {load_id} is missing pickup or destination address. Skipping.")
#              continue # Skip if addresses are incomplete

        

#         detour_info = get_route_eta_distance(
#             origin_lat=truck.latitude, # Truck's current location as origin for the detour calculation
#             origin_lng=truck.longitude,
#             pickup_address=pickup_address, # Load's pickup location
#             drop_address=drop_address      # Load's destination
#         )

#         if not detour_info:
#             logger.info(f"Skipping load {load_id} due to detour calculation failure.")
#             continue # Skip if routing fails

#         rate_str_cleaned = current_load.get("rate", "₹0/km")

#         try:
#             rate_value_str = rate_str_cleaned.replace("₹", "").replace("/km", "").strip()
#             rate_value = float(rate_value_str)

#             if rate_value < 0:
#                  logger.warning(f"Parsed negative rate value for load {load_id}: '{rate_str_cleaned}'. Using 0.0.")
#                  rate_value = 0.0 

#         except ValueError as e: 
#             logger.warning(f"Rate parsing ValueError for load {load_id}: '{rate_str_cleaned}'. Error: {e}. Using 0.0.")
#             rate_value = 0.0 # Use float 0.0
#         except Exception as e: # Catch any other unexpected errors during parsing
#              logger.warning(f"Unexpected rate parse error for load {load_id} ('{rate_str_cleaned}'): {e}. Using 0.0.")
#              rate_value = 0.0 # Use float 0.0

#         score = rate_value # Base score is the rate per km

#         # Bonus for urgency - arbitrary value
#         if "urgent" in current_load.get("status", "").lower():
#             score += 2.0 # Use float for consistency

#         fuel_penalty = 0.0
#         detour_fuel_cost = detour_info.get("fuel_cost", 0.0)
#         if detour_fuel_cost > 0:
#              fuel_penalty = detour_fuel_cost / 40.0

#         time_penalty = 0.0
#         # Ensure we get a float or 0.0 from get()
#         detour_extra_min = detour_info.get("extra_min", 0.0)
#         if detour_extra_min > 0:
#              time_penalty = detour_extra_min / 180.0


#         score -= fuel_penalty
#         score -= time_penalty

#         logger.debug(
#             f"Load {load_id} → Rate: {rate_value:.2f}, "
#             f"Urgency bonus: {2.0 if 'urgent' in current_load.get('status', '').lower() else 0.0:.2f}, "
#             f"Fuel penalty: -{fuel_penalty:.2f}, Time penalty: -{time_penalty:.2f}, Final score: {score:.2f}"
#         )

#         scored_and_filtered_loads.append({
#             "load": current_load, 
#             "score": round(score, 2),
#             "detour": detour_info 
#         })

#     return scored_and_filtered_loads
