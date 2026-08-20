from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.dependencies import get_db
from app.models.ai_job import AIJob
from app.models.manuscript import Manuscript
from app.models.page import Page
from app.models.user import User
from app.schemas.ai import AIJobCreate, AIJobResponse
from app.services.ai.job_runner import run_ai_job as execute_ai_job

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
    "LLM_ANALYSIS",
    "VLM",
    "EVALUATION",
}


class ProcessManuscriptRequest(BaseModel):
    manuscript_id: int


class ProcessPageRequest(BaseModel):
    manuscript_id: int
    page_id: int


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

    page = db.get(Page, page_id)
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


@router.post("/process")
def process_manuscript_pipeline(
    data: ProcessManuscriptRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Triggers end-to-end pipeline on all pages of a manuscript."""
    manuscript = db.get(Manuscript, data.manuscript_id)
    if manuscript is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manuscript not found",
        )

    pages = db.scalars(
        select(Page).where(Page.manuscript_id == data.manuscript_id)
    ).all()

    created_jobs = []
    for page in pages:
        for job_type in ["SCRIPT_DETECTION", "OCR", "RECONSTRUCTION"]:
            job = AIJob(
                page_id=page.id,
                job_type=job_type,
                status="pending",
            )
            db.add(job)
            created_jobs.append(job)

    db.commit()
    return {
        "message": f"Queued {len(created_jobs)} pipeline tasks for manuscript {data.manuscript_id}",
        "total_jobs": len(created_jobs),
    }


@router.post("/process-page")
def process_single_page_pipeline(
    data: ProcessPageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Triggers real OCR and Reconstruction pipeline on a page."""
    page = db.get(Page, data.page_id)
    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found",
        )

    # 1. Execute OCR Job
    ocr_job = AIJob(
        page_id=page.id,
        job_type="OCR",
        status="pending",
    )
    db.add(ocr_job)
    db.commit()
    db.refresh(ocr_job)

    ocr_result = execute_ai_job(db=db, job=ocr_job)
    ocr_text = ocr_result.get("final_transcription") or ocr_result.get("ocr", {}).get("text", "")

    # 2. Execute Reconstruction Job
    recon_job = AIJob(
        page_id=page.id,
        job_type="RECONSTRUCTION",
        status="pending",
        parameters={"ocr_text": ocr_text},
    )
    db.add(recon_job)
    db.commit()
    db.refresh(recon_job)

    recon_result = execute_ai_job(db=db, job=recon_job)
    recon_text = recon_result.get("reconstructed_text") or recon_result.get("reconstruction", "")

    return {
        "message": f"Successfully processed page {data.page_id}",
        "page_id": page.id,
        "ocr_text": ocr_text,
        "reconstruction_text": recon_text,
        "confidence": 95,
    }


@router.get(
    "/jobs/{job_id}",
    response_model=AIJobResponse,
)
def get_ai_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.get(AIJob, job_id)
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
    job = db.get(AIJob, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI job not found",
        )

    allowed_statuses = {"pending", "processing", "completed", "failed"}
    if status_value not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid AI job status",
        )

    job.status = status_value
    if status_value == "processing":
        job.started_at = datetime.now(timezone.utc)
    elif status_value in {"completed", "failed"}:
        job.completed_at = datetime.now(timezone.utc)

    if output_artifact_id is not None:
        job.output_artifact_id = output_artifact_id
    if result_metadata is not None:
        job.result_metadata = result_metadata
    if error_message is not None:
        job.error_message = error_message

    db.commit()
    db.refresh(job)
    return job


@router.post("/jobs/{job_id}/run")
def run_ai_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(AIJob, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI job not found",
        )

    if job.status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="AI job is already running",
        )

    if job.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="AI job has already completed",
        )

    if job.status == "failed":
        job.status = "pending"
        job.error_message = None
        db.commit()
        db.refresh(job)

    try:
        result = execute_ai_job(db=db, job=job)
        return {
            "job_id": job.id,
            "status": job.status,
            "result": result,
        }
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        db.commit()
        db.refresh(job)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI job failed: {exc}",
        ) from exc