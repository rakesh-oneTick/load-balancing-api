# logistics_ai_project/app/models.py
from pydantic import BaseModel

class Truck(BaseModel):
    # truck_id: str
    location: str # Descriptive location, for display or context
    # latitude: float
    # longitude: float
    capacity: int # Assuming in tons, for example

class Feedback(BaseModel):
    truck_id: str
    load_origin: str
    load_destination: str
    ai_score: float
    action: str # e.g., "accepted", "rejected"