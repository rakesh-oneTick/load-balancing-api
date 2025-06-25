# logistics_ai_project/app/routers/feedback.py
from fastapi import APIRouter
import logging
from datetime import datetime

from app.models import Feedback as FeedbackModel # Alias to avoid conflict
from app.data.data_loader import save_dummy_feedback # Using the new save function

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/feedback", summary="Record user feedback on recommendations")
def record_feedback_endpoint(feedback_data: FeedbackModel) -> dict:
    """
    Records user feedback about a load recommendation and stores it.
    """
    feedback_entry = feedback_data.model_dump() # Use model_dump() for Pydantic v2+
    feedback_entry["timestamp"] = datetime.utcnow().isoformat()
    
    save_dummy_feedback(feedback_entry) # Save to the dummy_feedback_log.json
    
    logger.info(f"Feedback recorded: {feedback_entry}")
    return {"status": "feedback recorded successfully"}    
