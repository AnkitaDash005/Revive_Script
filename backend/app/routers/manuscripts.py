from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.dependencies import get_db
from app.models.collection import Collections
from app.models.manuscript import Manuscript
from app.models.user import User
from app.schemas.manuscript import (
    ManuscriptCreate,
    ManuscriptResponse,
    ManuscriptUpdate,
)

router = APIRouter(
    tags=["Manuscripts"],
)


@router.get(
    "/manuscripts",
    response_model=list[ManuscriptResponse],
)
def list_all_manuscripts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns all manuscripts owned by the current user across collections."""
    return db.scalars(
        select(Manuscript)
        .join(Collections, Manuscript.collection_id == Collections.id)
        .where(Collections.owner_id == current_user.id)
        .order_by(Manuscript.created_at.desc())
    ).all()


@router.post(
    "/collections/{collection_id}/manuscripts",
    response_model=ManuscriptResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_manuscript(
    collection_id: int,
    data: ManuscriptCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    collection = db.get(Collections, collection_id)

    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection ID {collection_id} does not exist.",
        )

    manuscript = Manuscript(
        collection_id=collection.id,
        title=data.title,
        description=data.description,
        language=data.language,
        script=data.script,
        author=data.author,
        approximate_date=data.approximate_date,
        source=data.source,
    )

    db.add(manuscript)
    db.commit()
    db.refresh(manuscript)

    return manuscript


@router.get(
    "/collections/{collection_id}/manuscripts",
    response_model=list[ManuscriptResponse],
)
def list_manuscripts_by_collection(
    collection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    collection = db.get(Collections, collection_id)

    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )

    return db.scalars(
        select(Manuscript)
        .where(Manuscript.collection_id == collection_id)
        .order_by(Manuscript.created_at.desc())
    ).all()


@router.get(
    "/manuscripts/{manuscript_id}",
    response_model=ManuscriptResponse,
)
def get_manuscript(
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

    return manuscript


@router.put(
    "/manuscripts/{manuscript_id}",
    response_model=ManuscriptResponse,
)
def update_manuscript(
    manuscript_id: int,
    data: ManuscriptUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    manuscript = db.get(Manuscript, manuscript_id)

    if manuscript is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manuscript not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(manuscript, field, value)

    db.commit()
    db.refresh(manuscript)

    return manuscript


@router.delete(
    "/manuscripts/{manuscript_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_manuscript(
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

    db.delete(manuscript)
    db.commit()