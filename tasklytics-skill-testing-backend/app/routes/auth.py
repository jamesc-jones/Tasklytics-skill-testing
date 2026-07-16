from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app import schemas
from app.auth.auth_utils import hash_password, verify_password, create_access_token, create_refresh_token, decode_token

from app.models import User, Task

from app.database import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.get("/")
def test_auth():
    return {"message": "Auth route working"}

@router.post("/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = User(
        email=user.email,
        hashed_password=hash_password(user.password),
        role="user"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created successfully",
            "user": {
                "id": new_user.id,
                "email": new_user.email
                }
            }


@router.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token_claims = {
        "sub": str(db_user.id),
        "email": db_user.email,
        "role": db_user.role
    }

    token = create_access_token(token_claims)
    refresh_token = create_refresh_token(token_claims)

    return {
        "access_token": token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "email": db_user.email,
            "role": db_user.role
        }
    }


@router.post("/refresh")
def refresh_access_token(payload: schemas.RefreshTokenRequest, db: Session = Depends(get_db)):
    decoded = decode_token(payload.refresh_token)

    if decoded is None or decoded.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id = decoded.get("sub")
    db_user = db.query(User).filter(User.id == int(user_id)).first() if user_id else None

    if not db_user:
        raise HTTPException(status_code=401, detail="User not found")

    new_access_token = create_access_token({
        "sub": str(db_user.id),
        "email": db_user.email,
        "role": db_user.role
    })

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }