from fastapi import APIRouter, HTTPException, Depends
from db import get_db
from db_helpers import create_account, update_account, delete_account
from models import AccountCreate, AccountUpdate, UserWithRoles
from routers.auth import check_permission, get_current_user
from typing import List, Dict, Any

router = APIRouter()

@router.get("/")
async def list_accounts(current_user: UserWithRoles = Depends(check_permission("accounts.read"))):
    conn = get_db()
    cursor = conn.execute("SELECT * FROM accounts WHERE tenant_id = ? ORDER BY created_at DESC", (current_user.tenant_id,))
    accounts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return accounts

@router.get("/{account_id}")
async def get_account(account_id: int, current_user: UserWithRoles = Depends(check_permission("accounts.read"))):
    conn = get_db()
    cursor = conn.execute("SELECT * FROM accounts WHERE id = ? AND tenant_id = ?", (account_id, current_user.tenant_id))
    account = cursor.fetchone()
    conn.close()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return dict(account)

@router.post("/")
async def create_account_endpoint(account: AccountCreate, current_user: UserWithRoles = Depends(check_permission("accounts.write"))):
    account_data = account.dict()
    account_data['tenant_id'] = current_user.tenant_id
    account_id = create_account(account_data)
    
    # Return the created account
    conn = get_db()
    cursor = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
    created_account = cursor.fetchone()
    conn.close()
    
    return dict(created_account)

@router.put("/{account_id}")
async def update_account_endpoint(account_id: int, account: AccountUpdate, current_user: UserWithRoles = Depends(check_permission("accounts.write"))):
    # Verify account belongs to tenant
    conn = get_db()
    cursor = conn.execute("SELECT id FROM accounts WHERE id = ? AND tenant_id = ?", (account_id, current_user.tenant_id))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Account not found")
    conn.close()
    
    account_data = account.dict(exclude_unset=True)
    
    if not update_account(account_id, account_data):
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Return the updated account
    conn = get_db()
    cursor = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
    updated_account = cursor.fetchone()
    conn.close()
    
    if not updated_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return dict(updated_account)

@router.delete("/{account_id}")
async def delete_account_endpoint(account_id: int, current_user: UserWithRoles = Depends(check_permission("accounts.delete"))):
    # Verify account belongs to tenant
    conn = get_db()
    cursor = conn.execute("SELECT id FROM accounts WHERE id = ? AND tenant_id = ?", (account_id, current_user.tenant_id))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Account not found")
    conn.close()
    
    if not delete_account(account_id):
        raise HTTPException(status_code=404, detail="Account not found")
    
    return {"message": "Account deleted successfully"}
