from app.core.auth import get_current_user
from app.core.dependencies import get_db
from app.models.collection import Collections
from app.models.user import User
from app.schemas.collection import (
    CollectionCreate,
    CollectionResponse,
    CollectionUpdate,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(prefix= "/Collections", tags=["Collections"])

@router.post(
    "",
    response_model= CollectionResponse,
    status_code= status.HTTP_201_CREATED,
)

def create_collection(
    data: CollectionCreate,
    current_user: User = Depends(get_current_user),
    db:Session = Depends(get_db),
):
    collection = Collections(
        name = data.name,
        description = data.description,
        owner_id = current_user.id,
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)

    return collection

@router.get(
    "",
    response_model = list[CollectionResponse],
)
def list_collections(
    current_user : User = Depends (get_current_user),
    db: Session = Depends(get_db),
):
    collections = db.scalars(
        select(Collections)
        .where(Collections.owner_id == current_user.id)
        .order_by(Collections.created_at.desc())
    ).all()

    return collections

@router.get(
    "/{collection_id}",
    response_model = CollectionResponse,
)
def get_collection(
    collection_id :int,
    current_user: User = Depends(get_current_user),
    db:Session = Depends(get_db),
):
    collection = db.scalar(
        select(Collections).where(
            Collections.id == collection_id,
            Collections.owner_id == current_user.id,
        )
    )
    if collection is None:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail="Collection Not Found",
        )
    return collection

@router.put(
    "/{collection_id}",
    response_model = CollectionResponse,
)
def update_collection(
    collection_id: int,
    data: CollectionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    collection = db.scalar(
        select(Collections).where(
            Collections.id == collection_id,
            Collections.owner_id == current_user.id,
        )
    )
    if collection is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail="Collection Not Found",
        )
    if data.name is not None:
        collection.name = data.name
    if data.description is not None:
        collection.description = data.description

    db.commit()
    db.refresh(collection)
    return collection

@router.delete(
    "/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_collection(
    collection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    collection = db.scalar(
        select(Collections).where(
            Collections.id == collection_id,
            Collections.owner_id == current_user.id,
        )
    )

    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )

    db.delete(collection)
    db.commit()
