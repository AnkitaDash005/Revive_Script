from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.dependencies import get_db
from app.models.ai_job import AIJob
from app.models.page import Page
from app.models.user import User
from app.schemas.ai import AIJobCreate, AIJobResponse
from datetime import datetime, timezone


router = APIRouter(
    prefix="/ai",
    tags=["AI"],
)


ALLOWED_JOB_TYPES = {
    "SCRIPT_DETECTION",
    "OCR",
    "EMBEDDING",
    "RAG",
    "RECONSTRUCTION",
    "TRANSLATION",
}


@router.post(
    "/pages/{page_id}/jobs",
    response_model=AIJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ai_job(
    page_id: int,
    data: AIJobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.job_type not in ALLOWED_JOB_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported AI job type",
        )

    page = db.scalar(
        select(Page).where(
            Page.id == page_id
        )
    )

    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found",
        )

    job = AIJob(
        page_id=page_id,
        job_type=data.job_type,
        status="pending",
        model_name=data.model_name,
        model_version=data.model_version,
        input_artifact_id=data.input_artifact_id,
        parameters=data.parameters,
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job

@router.get(
    "/jobs/{job_id}",
    response_model=AIJobResponse,
)
def get_ai_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.scalar(
        select(AIJob).where(
            AIJob.id == job_id
        )
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI job not found",
        )

    return job

@router.patch(
    "/jobs/{job_id}",
    response_model=AIJobResponse,
)
def update_ai_job(
    job_id: int,
    status_value: str,
    output_artifact_id: int | None = None,
    result_metadata: dict | None = None,
    error_message: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.scalar(
        select(AIJob).where(
            AIJob.id == job_id
        )
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI job not found",
        )

    allowed_statuses = {
        "pending",
        "processing",
        "completed",
        "failed",
    }

    if status_value not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid AI job status",
        )

    job.status = status_value

    if status_value == "processing":
        job.started_at = datetime.now(timezone.utc)

    if status_value == "completed":
        job.completed_at = datetime.now(timezone.utc)
        job.output_artifact_id = output_artifact_id
        job.result_metadata = result_metadata

    if status_value == "failed":
        job.completed_at = datetime.now(timezone.utc)
        job.error_message = error_message

    db.commit()
    db.refresh(job)

    return job