from pathlib import Path
from uuid import uuid4

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

from app.core.auth import get_current_user
from app.core.dependencies import get_db
from app.models.artifact import Artifact
from app.models.manuscript import Manuscript
from app.models.page import Page
from app.models.user import User
from app.schemas.page import PageResponse
from app.services.provenance import create_artifact

router = APIRouter(
    tags=["Pages"],
)

STORAGE_DIR = Path("storage/originals")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


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
    manuscript = db.get(Manuscript, manuscript_id)

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

    extension = Path(file.filename or "").suffix.lower()
    if not extension:
        extension = ".jpg" if "jpeg" in content_type else ".png"

    safe_filename = f"manuscript_{manuscript_id}_page_{page_number}_{uuid4().hex[:8]}{extension}"
    file_path = STORAGE_DIR / safe_filename
    file_path.write_bytes(content)

    page = Page(
        manuscript_id=manuscript.id,
        page_number=page_number,
        original_filename=file.filename or "uploaded_page",
        original_path=str(file_path).replace("\\", "/"),
        mime_type=content_type,
    )

    try:
        db.add(page)
        db.flush()

        create_artifact(
            db,
            page_id=page.id,
            artifact_type="ORIGINAL",
            file_path=str(file_path).replace("\\", "/"),
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

    except SQLAlchemyError:
        db.rollback()
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not save page to database.",
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
    manuscript = db.get(Manuscript, manuscript_id)
    if manuscript is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manuscript not found",
        )

    return db.scalars(
        select(Page)
        .where(Page.manuscript_id == manuscript_id)
        .order_by(Page.page_number.asc())
    ).all()


@router.get("/pages/detail")
@router.get("/pages/{page_id}/detail")
def get_page_with_artifacts(
    page_id: int | None = None,
    manuscript_id: int | None = None,
    page_number: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Finds a page by page_id OR (manuscript_id + page_number) and returns
    its image URL along with the latest OCR, RECONSTRUCTION, and RAG artifacts.
    """
    page = None
    if page_id:
        page = db.get(Page, page_id)
    elif manuscript_id and page_number:
        page = db.scalars(
            select(Page).where(
                Page.manuscript_id == manuscript_id,
                Page.page_number == page_number,
            )
        ).first()

    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found",
        )

    # Format image path for browser consumption (e.g., /storage/originals/...)
    img_url = page.original_path
    if not img_url.startswith("/"):
        img_url = "/" + img_url

    artifacts = db.scalars(
        select(Artifact)
        .where(Artifact.page_id == page.id)
        .order_by(Artifact.version.desc(), Artifact.id.desc())
    ).all()

    ocr_artifact = next((a for a in artifacts if a.artifact_type == "OCR"), None)
    recon_artifact = next((a for a in artifacts if a.artifact_type == "RECONSTRUCTION"), None)

    return {
        "id": page.id,
        "page_id": page.id,
        "page_number": page.page_number,
        "manuscript_id": page.manuscript_id,
        "image_url": img_url,
        "original_path": page.original_path,
        "ocr_text": ocr_artifact.content if ocr_artifact else "",
        "ocr_confidence": (ocr_artifact.metadata_json or {}).get("confidence", 92) if ocr_artifact else 92,
        "reconstruction_text": recon_artifact.content if recon_artifact else "",
        "reconstruction_confidence": (recon_artifact.metadata_json or {}).get("confidence", 95) if recon_artifact else 95,
        "artifacts_count": len(artifacts),
    }


@router.get(
    "/pages/{page_id}",
    response_model=PageResponse,
)
def get_page(
    page_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    page = db.get(Page, page_id)
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
    page = db.get(Page, page_id)
    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found",
        )

    file_path = Path(page.original_path)

    try:
        db.delete(page)
        db.commit()

        if file_path.exists():
            file_path.unlink()

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete page from database.",
        )