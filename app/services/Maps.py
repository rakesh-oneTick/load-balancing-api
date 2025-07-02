# logistics_ai_project/app/services/Maps.py
import requests
import logging
from typing import Dict, Optional, Any
from app.config import settings # Import settings from your config.py
import os
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

def get_route_eta_distance(
    origin_lat: float,
    origin_lng: float,
    pickup_address: str,
    drop_address: str
) -> Optional[Dict[str, Any]]:
    """
    Calculates route, ETA, and distance using Google Maps API.
    """
    def query(origins_val: str, destinations_val: str) -> Optional[Dict[str, Any]]:
        if not settings.Maps_API_KEY or settings.Maps_API_KEY == os.getenv("Maps_API_KEY"):
           logger.warning("Google Maps API key is a dummy or not configured. Returning mock data.")
           return {"distance": {"value": 200000}, "duration": {"value": 10800}, "status": "OK_MOCK"}

        try:
            response = requests.get(
                "https://maps.googleapis.com/maps/api/distancematrix/json",
                params={
                    "origins": origins_val,
                    "destinations": destinations_val,
                    "key": settings.Maps_API_KEY,
                    "units": "metric" # Ensures values are in meters and seconds
                }
            )
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
            result = response.json()

            if result['status'] != 'OK' or not result['rows'] or not result['rows'][0]['elements']:
                logger.warning(f"Google Maps API issue for {origins_val} → {destinations_val}: Status {result.get('status')}, Error: {result.get('error_message', 'No elements')}")
                return None
            
            element = result['rows'][0]['elements'][0]
            if element['status'] != 'OK':
                logger.warning(f"Google Maps element status not OK for {origins_val} → {destinations_val}: {element['status']}")
                return None
            return element
        except requests.exceptions.RequestException as e:
            logger.error(f"Google Maps request failed for {origins_val} → {destinations_val}: {e}")
            return None
        except Exception as e: # Catch any other unexpected errors
            logger.error(f"Unexpected error in Google Maps query for {origins_val} → {destinations_val}: {e}", exc_info=True)
            return None

    if not pickup_address or not drop_address:
        logger.warning("Pickup or drop address is missing.")
        return None

    truck_current_location = f"{origin_lat},{origin_lng}"

    direct_route_info = query(truck_current_location, drop_address)
    to_pickup_info = query(truck_current_location, pickup_address)
    pickup_to_drop_info = query(pickup_address, drop_address)

    if not all([direct_route_info, to_pickup_info, pickup_to_drop_info]):
        logger.warning("Failed to retrieve all necessary route segments from Google Maps.")
        return None

    try:
        direct_km = direct_route_info['distance']['value'] / 1000
        direct_min = direct_route_info['duration']['value'] / 60

        via_km = (to_pickup_info['distance']['value'] + pickup_to_drop_info['distance']['value']) / 1000
        via_min = (to_pickup_info['duration']['value'] + pickup_to_drop_info['duration']['value']) / 60
        
        extra_km = via_km - direct_km
        fuel_cost = extra_km * settings.FUEL_COST_PER_KM if extra_km > 0 else 0.0


        return {
            "direct_km": round(direct_km, 1),
            "via_km": round(via_km, 1),
            "extra_km": round(extra_km, 1),
            "extra_min": round(via_min - direct_min, 1),
            "fuel_cost": round(fuel_cost, 2)
        }
    except KeyError as e: # More specific exception for missing keys in API response
        logger.error(f"Detour calculation failed due to missing key in Google Maps response: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Detour calculation failed: {e}", exc_info=True)
        return None