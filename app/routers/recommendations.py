# logistics_ai_project/app/routers/recommendations.py
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
import logging
from typing import List


from app.models import Truck
from app.core.scoring import score_loads
from app.services import google_location_service
from app.services.openai_client import get_openai_summary
from app.data.data_loader import get_dummy_loads
import os
load_dotenv()

logger = logging.getLogger(__name__)
router = APIRouter()



class AppSettings:
    Maps_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY")
settings = AppSettings()


logger = logging.getLogger(__name__)
router = APIRouter()

try:
    google_location_service_instance = google_location_service(api_key=settings.Maps_API_KEY)
except AttributeError:
    logger.error("Maps_API_KEY not found in settings. Google Maps API service cannot be initialized.")
    google_location_service_instance = None
except Exception as e:
    logger.error(f"Failed to initialize GoogleLocationService: {e}")
    google_location_service_instance = None


# This endpoing is responsible to get loads based on the truck's location origin and destination
@router.post("/recommend", summary="Get scored load recommendations for a truck")
def recommend_loads_endpoint(truck: Truck) -> List[dict]:
    logger.info("Recommend loads endpoint method")
    """
    Provides a list of loads, scored and sorted based on suitability for the given truck.
    """
    all_available_loads = get_dummy_loads()
    if not all_available_loads:
        logger.warning("No loads available from the data source.")
        return []

    scored_loads_list = score_loads(truck, all_available_loads)
    
    if not scored_loads_list:
        logger.info(f"No suitable loads found for this truck after scoring.")
        return []
        
    return sorted(scored_loads_list, key=lambda x: x["score"], reverse=True)


# this endpoint is responsible to get the summary of the top 3 loads
@router.post("/recommend/summary", summary="Get an AI-generated summary for top recommendations")
def recommend_summary_endpoint(truck: Truck) -> dict:
    logger.info("recommedn summary method")
    """
    Provides an AI-generated summary for the top 3 recommended loads for the given truck.
    """
    all_available_loads = get_dummy_loads()
    if not all_available_loads:
        raise HTTPException(status_code=404, detail="No loads available to make recommendations.")

    scored_loads_list = score_loads(truck, all_available_loads)

    if not scored_loads_list:
        raise HTTPException(status_code=404, detail=f"No suitable loads found for truck {truck.truck_id} to summarize.")

    top_3_loads = sorted(scored_loads_list, key=lambda x: x["score"], reverse=True)[:3]

    # Prepare data for OpenAI prompt (original load dict + score + detour info)
    summary_input_data = []
    for item in top_3_loads:
        summary_input_data.append({
            "load_details": item["load"],
            "score": item["score"],
            "detour_info": item["detour"] # ensure key matches what score_loads returns
        })

    summary_text = get_openai_summary(truck.model_dump(), summary_input_data) # Use model_dump() for Pydantic v2+

    if summary_text is None:
        logger.error("Failed to generate AI summary.")
        raise HTTPException(status_code=500, detail="AI summary generation failed. Please check logs.")
    
    return {"summary": summary_text}