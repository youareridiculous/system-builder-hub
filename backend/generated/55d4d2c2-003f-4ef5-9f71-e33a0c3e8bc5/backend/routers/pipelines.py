from fastapi import APIRouter, HTTPException
from db import get_db
from db_helpers import create_pipeline, update_pipeline, delete_pipeline
from models import PipelineCreate, PipelineUpdate
from typing import List, Dict, Any

router = APIRouter()

@router.get("/")
async def list_pipelines():
    conn = get_db()
    cursor = conn.execute("SELECT * FROM pipelines ORDER BY created_at DESC")
    pipelines = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return pipelines

@router.get("/{pipeline_id}")
async def get_pipeline(pipeline_id: int):
    conn = get_db()
    cursor = conn.execute("SELECT * FROM pipelines WHERE id = ?", (pipeline_id,))
    pipeline = cursor.fetchone()
    conn.close()
    
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    return dict(pipeline)

@router.post("/")
async def create_pipeline_endpoint(pipeline: PipelineCreate):
    pipeline_data = pipeline.dict()
    pipeline_id = create_pipeline(pipeline_data)
    
    # Return the created pipeline
    conn = get_db()
    cursor = conn.execute("SELECT * FROM pipelines WHERE id = ?", (pipeline_id,))
    created_pipeline = cursor.fetchone()
    conn.close()
    
    return dict(created_pipeline)

@router.put("/{pipeline_id}")
async def update_pipeline_endpoint(pipeline_id: int, pipeline: PipelineUpdate):
    pipeline_data = pipeline.dict(exclude_unset=True)
    
    if not update_pipeline(pipeline_id, pipeline_data):
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    # Return the updated pipeline
    conn = get_db()
    cursor = conn.execute("SELECT * FROM pipelines WHERE id = ?", (pipeline_id,))
    updated_pipeline = cursor.fetchone()
    conn.close()
    
    if not updated_pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    return dict(updated_pipeline)

@router.delete("/{pipeline_id}")
async def delete_pipeline_endpoint(pipeline_id: int):
    if not delete_pipeline(pipeline_id):
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    return {"message": "Pipeline deleted successfully"}
