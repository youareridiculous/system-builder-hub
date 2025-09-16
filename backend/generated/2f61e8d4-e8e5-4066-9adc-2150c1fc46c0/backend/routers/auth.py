from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import json
from db import get_db
from models import (
    User, UserCreate, UserUpdate, UserWithRoles,
    LoginRequest, LoginResponse, TokenData,
    Role, RoleCreate, RoleUpdate, RoleWithPermissions,
    Permission, PermissionCreate
)

router = APIRouter(tags=["authentication"])

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = "your-secret-key-change-in-production"  # Should come from environment
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[int] = payload.get("sub")
        email: Optional[str] = payload.get("email")
        tenant_id: Optional[str] = payload.get("tenant_id")
        if user_id is None or email is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id, email=email, tenant_id=tenant_id)
    except JWTError:
        raise credentials_exception
    return token_data

def get_current_user(token_data: TokenData = Depends(verify_token)) -> UserWithRoles:
    conn = get_db()
    cursor = conn.cursor()
    
    # Get user with roles
    cursor.execute("""
        SELECT u.*, GROUP_CONCAT(r.name) as roles
        FROM users u
        LEFT JOIN user_roles ur ON u.id = ur.user_id
        LEFT JOIN roles r ON ur.role_id = r.id
        WHERE u.id = ? AND u.tenant_id = ? AND u.is_active = 1
        GROUP BY u.id
    """, (token_data.user_id, token_data.tenant_id))
    
    user_data = cursor.fetchone()
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    user_dict = dict(user_data)
    roles = user_dict.pop('roles', '').split(',') if user_dict.get('roles') else []
    user_dict['roles'] = [role for role in roles if role]
    
    return UserWithRoles(**user_dict)

def check_permission(permission_code: str):
    def permission_checker(current_user: UserWithRoles = Depends(get_current_user)) -> UserWithRoles:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get user's permissions
        cursor.execute("""
            SELECT DISTINCT p.code
            FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            JOIN user_roles ur ON rp.role_id = ur.role_id
            WHERE ur.user_id = ?
        """, (current_user.id,))
        
        user_permissions = [row['code'] for row in cursor.fetchall()]
        
        if permission_code not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission_code}' required"
            )
        
        return current_user
    
    return permission_checker

@router.post("/register", response_model=User)
def register(user: UserCreate):
    """Register a new user (dev only)"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if user already exists
    cursor.execute("SELECT id FROM users WHERE email = ?", (user.email,))
    if cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password and create user
    hashed_password = get_password_hash(user.password)
    cursor.execute("""
        INSERT INTO users (email, name, password_hash, tenant_id)
        VALUES (?, ?, ?, ?)
    """, (user.email, user.name, hashed_password, user.tenant_id))
    
    user_id = cursor.lastrowid
    conn.commit()
    
    # Return created user (without password)
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()
    return User(**dict(user_data))

@router.post("/login", response_model=LoginResponse)
def login(login_data: LoginRequest):
    """Login user and return JWT token"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get user with password hash
    cursor.execute("""
        SELECT u.*, GROUP_CONCAT(r.name) as roles
        FROM users u
        LEFT JOIN user_roles ur ON u.id = ur.user_id
        LEFT JOIN roles r ON ur.role_id = r.id
        WHERE u.email = ? AND u.is_active = 1
        GROUP BY u.id
    """, (login_data.email,))
    
    user_data = cursor.fetchone()
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    user_dict = dict(user_data)
    
    # Verify password
    if not verify_password(login_data.password, user_dict['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user_dict['id']), "email": user_dict['email'], "tenant_id": user_dict['tenant_id']},
        expires_delta=access_token_expires
    )
    
    # Prepare user response
    roles = user_dict.pop('roles', '').split(',') if user_dict.get('roles') else []
    user_dict['roles'] = [role for role in roles if role]
    user_dict.pop('password_hash', None)
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserWithRoles(**user_dict)
    )

@router.get("/me", response_model=UserWithRoles)
def get_current_user_info(current_user: UserWithRoles = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@router.post("/logout")
def logout():
    """Logout user (client-side token removal)"""
    return {"message": "Successfully logged out"}

# RBAC Management (Admin only)
@router.get("/roles", response_model=list[Role])
def get_roles(current_user: UserWithRoles = Depends(check_permission("roles.read"))):
    """Get all roles for current tenant"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM roles WHERE tenant_id = ?", (current_user.tenant_id,))
    return [Role(**dict(row)) for row in cursor.fetchall()]

@router.post("/roles", response_model=Role)
def create_role(role: RoleCreate, current_user: UserWithRoles = Depends(check_permission("roles.write"))):
    """Create a new role"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO roles (name, description, tenant_id)
        VALUES (?, ?, ?)
    """, (role.name, role.description, current_user.tenant_id))
    
    role_id = cursor.lastrowid
    conn.commit()
    
    cursor.execute("SELECT * FROM roles WHERE id = ?", (role_id,))
    role_data = cursor.fetchone()
    return Role(**dict(role_data))

@router.get("/permissions", response_model=list[Permission])
def get_permissions(current_user: UserWithRoles = Depends(check_permission("permissions.read"))):
    """Get all permissions"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM permissions")
    return [Permission(**dict(row)) for row in cursor.fetchall()]
