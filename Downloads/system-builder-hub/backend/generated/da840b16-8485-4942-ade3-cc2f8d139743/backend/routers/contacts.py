from fastapi import APIRouter, HTTPException
from db import get_db
from db_helpers import create_contact, update_contact, delete_contact
from models import ContactCreate, ContactUpdate
from typing import List, Dict, Any

router = APIRouter()

@router.get("/")
async def list_contacts():
    conn = get_db()
    cursor = conn.execute("SELECT * FROM contacts ORDER BY created_at DESC")
    contacts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return contacts

@router.get("/{contact_id}")
async def get_contact(contact_id: int):
    conn = get_db()
    cursor = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,))
    contact = cursor.fetchone()
    conn.close()
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    return dict(contact)

@router.post("/")
async def create_contact_endpoint(contact: ContactCreate):
    contact_data = contact.dict()
    contact_id = create_contact(contact_data)
    
    # Return the created contact
    conn = get_db()
    cursor = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,))
    created_contact = cursor.fetchone()
    conn.close()
    
    return dict(created_contact)

@router.put("/{contact_id}")
async def update_contact_endpoint(contact_id: int, contact: ContactUpdate):
    contact_data = contact.dict(exclude_unset=True)
    
    if not update_contact(contact_id, contact_data):
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Return the updated contact
    conn = get_db()
    cursor = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,))
    updated_contact = cursor.fetchone()
    conn.close()
    
    if not updated_contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    return dict(updated_contact)

@router.delete("/{contact_id}")
async def delete_contact_endpoint(contact_id: int):
    if not delete_contact(contact_id):
        raise HTTPException(status_code=404, detail="Contact not found")
    
    return {"message": "Contact deleted successfully"}
