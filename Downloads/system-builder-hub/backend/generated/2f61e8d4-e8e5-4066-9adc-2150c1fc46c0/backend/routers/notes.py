from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
from db import get_db
from models import Note, NoteCreate, NoteUpdate

router = APIRouter(tags=["notes"])

@router.get("/contacts/{contact_id}/notes", response_model=List[Note])
async def get_contact_notes(contact_id: int):
    """Get all notes for a contact"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM notes 
        WHERE entity_type = 'contact' AND entity_id = ?
        ORDER BY pinned DESC, created_at DESC
    """, (contact_id,))
    
    notes = []
    for row in cursor.fetchall():
        notes.append(dict(row))
    
    conn.close()
    return notes

@router.post("/contacts/{contact_id}/notes", response_model=Note)
async def create_contact_note(contact_id: int, note: NoteCreate):
    """Create a new note for a contact"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO notes (entity_type, entity_id, body, pinned, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ('contact', contact_id, note.body, note.pinned, datetime.now(), datetime.now()))
    
    note_id = cursor.lastrowid
    conn.commit()
    
    # Get the created note
    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    created_note = dict(cursor.fetchone())
    
    conn.close()
    return created_note

@router.put("/notes/{note_id}", response_model=Note)
async def update_note(note_id: int, note_update: NoteUpdate):
    """Update a note"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if note exists
    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Build update query
    update_fields = []
    params = []
    
    if note_update.body is not None:
        update_fields.append("body = ?")
        params.append(note_update.body)
    
    if note_update.pinned is not None:
        update_fields.append("pinned = ?")
        params.append(note_update.pinned)
    
    if update_fields:
        update_fields.append("updated_at = ?")
        params.append(datetime.now())
        params.append(note_id)
        
        query = f"UPDATE notes SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
    
    # Get updated note
    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    updated_note = dict(cursor.fetchone())
    
    conn.close()
    return updated_note

@router.delete("/notes/{note_id}")
async def delete_note(note_id: int):
    """Delete a note"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Note not found")
    
    conn.commit()
    conn.close()
    
    return {"message": "Note deleted successfully"}
