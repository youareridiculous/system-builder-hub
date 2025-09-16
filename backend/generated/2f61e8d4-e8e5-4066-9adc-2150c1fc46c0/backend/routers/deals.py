from fastapi import APIRouter, HTTPException
from db import get_db
from db_helpers import create_deal, update_deal, delete_deal
from models import DealCreate, DealUpdate
from typing import List, Dict, Any

router = APIRouter()

@router.get("/")
async def list_deals():
    conn = get_db()
    cursor = conn.execute("""
        SELECT d.*, 
               a.name as account_name,
               c.first_name || ' ' || c.last_name as contact_name
        FROM deals d
        LEFT JOIN accounts a ON d.account_id = a.id
        LEFT JOIN contacts c ON d.contact_id = c.id
        ORDER BY d.created_at DESC
    """)
    deals = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return deals

@router.get("/{deal_id}")
async def get_deal(deal_id: int):
    conn = get_db()
    cursor = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,))
    deal = cursor.fetchone()
    conn.close()
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    return dict(deal)

@router.post("/")
async def create_deal_endpoint(deal: DealCreate):
    deal_data = deal.dict()
    deal_id = create_deal(deal_data)
    
    # Return the created deal
    conn = get_db()
    cursor = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,))
    created_deal = cursor.fetchone()
    conn.close()
    
    return dict(created_deal)

@router.put("/{deal_id}")
async def update_deal_endpoint(deal_id: int, deal: DealUpdate):
    deal_data = deal.dict(exclude_unset=True)
    
    if not update_deal(deal_id, deal_data):
        raise HTTPException(status_code=404, detail="Deal not found")
    
    # Return the updated deal
    conn = get_db()
    cursor = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,))
    updated_deal = cursor.fetchone()
    conn.close()
    
    if not updated_deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    return dict(updated_deal)

@router.delete("/{deal_id}")
async def delete_deal_endpoint(deal_id: int):
    if not delete_deal(deal_id):
        raise HTTPException(status_code=404, detail="Deal not found")
    
    return {"message": "Deal deleted successfully"}
