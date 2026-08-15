from pathlib import Path
from uuid import uuid4

from app.core.auth import get_current_user
from app.core.dependencies import get_db
from app.models.collection import Collections
from app.models.manuscript import Manuscript
from app.models.page import Page
from app.models.user import User
from app.schemas.page import PageResponse
from app.services.provenance import create_artifact
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

router = APIRouter(
    tags=["Pages"],
)


STORAGE_DIR = Path("storage/originals")

ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

MAX_FILE_SIZE = 10 * 1024 * 1024

@router.post(
    "/manuscripts/{manuscript_id}/pages",
    response_model=PageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_page(
    manuscript_id: int,
    page_number: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    manuscript = db.scalar(
        select(Manuscript)
        .join(
            Collection,
            Manuscript.collection_id == Collection.id,
        )
        .where(
            Manuscript.id == manuscript_id,
            Collection.owner_id == current_user.id,
        )
    )

    if manuscript is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manuscript not found",
        )

    if page_number < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be greater than zero",
        )

    # Safe fallback if content_type is None
    content_type = file.content_type or ""
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG and WebP images are allowed",
        )

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size must be less than 10 MB",
        )

    STORAGE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    extension = Path(file.filename or "").suffix.lower()

    safe_filename = (
        f"manuscript_{manuscript_id}"
        f"_page_{page_number}"
        f"_{uuid4().hex}"
        f"{extension}"
    )

    file_path = STORAGE_DIR / safe_filename
    file_path.write_bytes(content)

    page = Page(
        manuscript_id=manuscript.id,
        page_number=page_number,
        original_filename=file.filename or "unknown",
        original_path=str(file_path),
        mime_type=content_type,
    )

    try:
        # Add and flush to generate page.id before creating the artifact
        db.add(page)
        db.flush()

        artifact = create_artifact(
            db,
            page_id=page.id,
            artifact_type="ORIGINAL",
            file_path=str(file_path),
            created_by=current_user.id,
            generation_method="human",
            metadata={
                "original_filename": file.filename or "unknown",
                "mime_type": content_type,
                "page_number": page_number,
            },
        )

        db.commit()
        db.refresh(page)
        
    except SQLAlchemyError as e:
        db.rollback()
        # Clean up the orphaned file if DB commit fails
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not save page to database. Ensure data is valid."
        )

    return page

@router.get(
    "/manuscripts/{manuscript_id}/pages",
    response_model=list[PageResponse],
)
def list_pages(
    manuscript_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    manuscript = db.scalar(
        select(Manuscript)
        .join(
            Collection,
            Manuscript.collection_id == Collection.id,
        )
        .where(
            Manuscript.id == manuscript_id,
            Collection.owner_id == current_user.id,
        )
    )

    if manuscript is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manuscript not found",
        )

    pages = db.scalars(
        select(Page)
        .where(Page.manuscript_id == manuscript_id)
        .order_by(Page.page_number)
    ).all()

    return pages

@router.get(
    "/pages/{page_id}",
    response_model=PageResponse,
)
def get_page(
    page_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    page = db.scalar(
        select(Page)
        .join(
            Manuscript,
            Page.manuscript_id == Manuscript.id,
        )
        .join(
            Collection,
            Manuscript.collection_id == Collection.id,
        )
        .where(
            Page.id == page_id,
            Collection.owner_id == current_user.id,
        )
    )

    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found",
        )

    return page

@router.delete(
    "/pages/{page_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_page(
    page_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    page = db.scalar(
        select(Page)
        .join(
            Manuscript,
            Page.manuscript_id == Manuscript.id,
        )
        .join(
            Collection,
            Manuscript.collection_id == Collection.id,
        )
        .where(
            Page.id == page_id,
            Collection.owner_id == current_user.id,
        )
    )

    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found",
        )

    file_path = Path(page.original_path)

    try:
        # Note: Your Page ORM model must have cascade="all, delete-orphan" 
        # for its relationship with Artifacts to avoid a foreign key constraint error here.
        db.delete(page)
        db.commit()
        
        # Only delete the file AFTER the DB transaction is successful
        if file_path.exists():
            file_path.unlink()
            
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete page from database."
        )