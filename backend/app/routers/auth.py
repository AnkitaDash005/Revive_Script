from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.dependencies import get_db
from app.core.oauth import oauth
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.security import hash_password, verify_password
from app.services.token import create_access_token

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    existing_email = db.scalar(
    select(User).where(User.email == data.email)
)

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
    )

    existing_username = db.scalar(
        select(User).where(User.name == data.name)
    )

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
    )

    # Fixed: Unindented out of the 'if existing_user' block
    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        auth_provider="local",
        role="researcher",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            (User.email == data.identifier)
            | (User.name == data.identifier)
        )
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
        )

    # Google-only account
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "This account uses Google login. "
                "Please sign in with Google."
            ),
        )

    if not verify_password(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    token = create_access_token(
        user_id=user.id,
        role=user.role,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }

@router.get("/google/login")
async def google_login(request: Request):
    # Dynamically builds the exact callback URI matching current host/origin
    redirect_uri = str(request.url_for("google_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", name="google_callback")
async def google_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    token = await oauth.google.authorize_access_token(request)

    user_info = token.get("userinfo")
    if not user_info:
        # Fallback to parsing openid ID token if userinfo endpoint isn't auto-merged
        user_info = await oauth.google.parse_id_token(request, token)

    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to retrieve Google user information",
        )

    if not user_info.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google email is not verified",
        )

    google_id = user_info.get("sub")
    email = user_info.get("email")
    name = user_info.get("name")

    if not google_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incomplete Google account information",
        )

    # 1. Try to find user by Google ID
    user = db.scalar(
        select(User).where(User.google_id == google_id)
    )

    # 2. Check if user exists by email if Google ID not found
    if user is None:
        user = db.scalar(
            select(User).where(User.email == email)
        )

    # 3. Create new user if account doesn't exist
    if user is None:
        user = User(
            name=name or email.split("@")[0],
            email=email,
            password_hash=None,
            google_id=google_id,
            auth_provider="google",
            role="researcher",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Link Google ID to existing email account
        if user.google_id is None:
            user.google_id = google_id
            db.commit()
            db.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # 4. Generate application JWT
    access_token = create_access_token(
        user_id=user.id,
        role=user.role,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }