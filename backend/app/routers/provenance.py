from app.core.auth import get_current_user
from app.core.dependencies import get_db
from app.models.artifact import Artifact
from app.models.collection import Collection
from app.models.manuscript import Manuscript
from app.models.page import Page
from app.models.provenance import ProvenanceEvent
from app.models.user import User
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

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
        .join(
            Manuscript,
            Page.manuscript_id == Manuscript.id,
        )
        .join(
            Collection,
            Manuscript.collection_id == Collection.id,
        )
        .where(
            Artifact.id == artifact_id,
            Collection.owner_id == current_user.id,
        )
    )

    if artifact is None:
        raise HTTPException(
            status_code=404,
            detail="Artifact not found",
        )

    events = db.scalars(
        select(ProvenanceEvent)
        .where(
            ProvenanceEvent.artifact_id == artifact_id
        )
        .order_by(ProvenanceEvent.created_at)
    ).all()

    return {
        "artifact": {
            "id": artifact.id,
            "type": artifact.artifact_type,
            "version": artifact.version,
            "generation_method": artifact.generation_method,
            "model_name": artifact.model_name,
            "model_version": artifact.model_version,
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