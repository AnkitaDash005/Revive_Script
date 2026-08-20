from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.dependencies import get_db
from app.models.artifact import Artifact
from app.models.collection import Collections
from app.models.manuscript import Manuscript
from app.models.page import Page
from app.models.provenance import ProvenanceEvent
from app.models.user import User

router = APIRouter(
    prefix="/provenance",
    tags=["Provenance"],
)


@router.get("/artifacts/{artifact_id}")
def get_artifact_provenance(
    artifact_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    artifact = db.scalar(
        select(Artifact)
        .join(Page, Artifact.page_id == Page.id)
        .join(Manuscript, Page.manuscript_id == Manuscript.id)
        .join(Collections, Manuscript.collection_id == Collections.id)
        .where(
            Artifact.id == artifact_id,
            Collections.owner_id == current_user.id,
        )
    )

    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )

    events = db.scalars(
        select(ProvenanceEvent)
        .where(ProvenanceEvent.artifact_id == artifact_id)
        .order_by(ProvenanceEvent.created_at.asc())
    ).all()

    return {
        "artifact": {
            "id": artifact.id,
            "type": artifact.artifact_type,
            "version": artifact.version,
            "generation_method": artifact.generation_method,
            "model_name": artifact.model_name,
            "model_version": artifact.model_version,
            "status": artifact.status,
        },
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "actor_id": event.actor_id,
                "source_artifact_id": event.source_artifact_id,
                "description": event.description,
                "created_at": event.created_at,
            }
            for event in events
        ],
    }


@router.get("/manuscripts/{manuscript_id}")
def get_manuscript_provenance(
    manuscript_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetches all provenance events associated with all pages/artifacts in a manuscript."""
    manuscript = db.get(Manuscript, manuscript_id)
    if manuscript is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manuscript not found",
        )

    events = db.scalars(
        select(ProvenanceEvent)
        .join(Artifact, ProvenanceEvent.artifact_id == Artifact.id)
        .join(Page, Artifact.page_id == Page.id)
        .where(Page.manuscript_id == manuscript_id)
        .order_by(ProvenanceEvent.created_at.desc())
    ).all()

    return [
        {
            "id": event.id,
            "event_type": event.event_type,
            "actor_id": event.actor_id,
            "artifact_id": event.artifact_id,
            "description": event.description,
            "created_at": event.created_at,
        }
        for event in events
    ]


@router.get("/pending")
def get_pending_provenance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns artifacts awaiting scholar verification."""
    pending_artifacts = db.scalars(
        select(Artifact)
        .join(Page, Artifact.page_id == Page.id)
        .join(Manuscript, Page.manuscript_id == Manuscript.id)
        .join(Collections, Manuscript.collection_id == Collections.id)
        .where(
            Collections.owner_id == current_user.id,
            Artifact.status == "pending_verification",
        )
        .order_by(Artifact.created_at.desc())
    ).all()

    return [
        {
            "id": item.id,
            "page_id": item.page_id,
            "artifact_type": item.artifact_type,
            "version": item.version,
            "status": item.status,
            "created_at": item.created_at,
        }
        for item in pending_artifacts
    ]