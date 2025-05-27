# logistics_ai_project/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import uvicorn # For programmatic run, if needed

from app.config import settings
from app.routers import loads, recommendations, agent, feedback,save_new_load # Import your routers

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL.upper(),
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Logistics AI API",
    description="API for recommending truck loads and providing logistics insights.",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN] if settings.FRONTEND_ORIGIN else ["*"], # Allow all if not specified
    allow_credentials=True, # If your frontend needs to send cookies/auth headers
    allow_methods=["*"],    # Allows all methods
    allow_headers=["*"],    # Allows all headers
)

# Include routers
app.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["Recommendations"])
app.include_router(agent.router, prefix="/api/v1/agent", tags=["AI Agent"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["Feedback"])
app.include_router(save_new_load.router, prefix="/api/v1/load", tags=["Save New Load"])
app.include_router(loads.router, prefix="/api/v1/delete-load", tags=["Delete Load"])

@app.get("/", tags=["Root"])
async def read_root():
    logger.info("Root endpoint was accessed.")
    return {"message": "Welcome to the Logistics AI API!"}

# For running programmatically (optional)
if __name__ == "__main__":
    logger.info(f"Starting Uvicorn server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)