from fastapi import APIRouter, HTTPException
from db import get_db
from db_helpers import create_activity, update_activity, delete_activity
from models import ActivityCreate, ActivityUpdate
from typing import List, Dict, Any

router = APIRouter()

@router.get("/")
async def list_activities():
    conn = get_db()
    cursor = conn.execute("SELECT * FROM activities ORDER BY created_at DESC")
    activities = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return activities

@router.get("/{activity_id}")
async def get_activity(activity_id: int):
    conn = get_db()
    cursor = conn.execute("SELECT * FROM activities WHERE id = ?", (activity_id,))
    activity = cursor.fetchone()
    conn.close()
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    return dict(activity)

@router.post("/")
async def create_activity_endpoint(activity: ActivityCreate):
    activity_data = activity.dict()
    activity_id = create_activity(activity_data)
    
    # Return the created activity
    conn = get_db()
    cursor = conn.execute("SELECT * FROM activities WHERE id = ?", (activity_id,))
    created_activity = cursor.fetchone()
    conn.close()
    
    return dict(created_activity)

@router.put("/{activity_id}")
async def update_activity_endpoint(activity_id: int, activity: ActivityUpdate):
    activity_data = activity.dict(exclude_unset=True)
    
    if not update_activity(activity_id, activity_data):
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Return the updated activity
    conn = get_db()
    cursor = conn.execute("SELECT * FROM activities WHERE id = ?", (activity_id,))
    updated_activity = cursor.fetchone()
    conn.close()
    
    if not updated_activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    return dict(updated_activity)

@router.delete("/{activity_id}")
async def delete_activity_endpoint(activity_id: int):
    if not delete_activity(activity_id):
        raise HTTPException(status_code=404, detail="Activity not found")
    
    return {"message": "Activity deleted successfully"}
