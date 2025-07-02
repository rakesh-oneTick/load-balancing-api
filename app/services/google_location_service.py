import requests
from dotenv import load_dotenv
import os
load_dotenv()



class GoogleLocationService:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY")  # ✅ Fix: Use the correct key
        self.base_url = "https://maps.googleapis.com/maps/api/geocode/json"

    def get_coordinates(self, location: str) -> dict:
        params = {
            "address": location,
            "key": self.api_key
        }

        response = requests.get(self.base_url, params=params)
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
