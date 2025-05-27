# app/routers/loads.py
import logging
from fastapi import APIRouter, HTTPException, status
from typing import Dict
from app.data import data_loader

router = APIRouter()
logger = logging.getLogger(__name__)

@router.delete("/loads/{load_id}", response_model=Dict[str, str], status_code=status.HTTP_200_OK) # <-- Ensure this line is exactly this
async def delete_load(load_id: str):
    logger.info(f"Delete load endpoint called with ID: {load_id}")
    try:
        deleted_successfully = data_loader.delete_load_by_id_from_file(load_id)

        if deleted_successfully:
            logger.info(f"Load with ID '{load_id}' successfully deleted from file.")
            return {"message": f"Load with ID '{load_id}' successfully deleted."}
        else:
            logger.warning(f"Load with ID '{load_id}' not found in file for deletion.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Load with ID '{load_id}' not found."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"An unexpected non-HTTPException error occurred during load deletion for ID '{load_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred during load deletion."
        )