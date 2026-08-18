from sqlalchemy.orm import Session

from app.models.ai_job import AIJob
from app.models.page import Page
from app.services.ai.ocr import OCRService
from app.services.ai.vlm import VLMService


def run_ocr_job(
    *,
    db: Session,
    job: AIJob,
) -> dict:
    page = db.get(Page, job.page_id)

    if page is None:
        raise ValueError(f"Page {job.page_id} not found")

    image_path = (
        getattr(page, "processed_path", None)
        or page.original_path
    )

    if not image_path:
        raise ValueError(
            f"Page {page.id} has no image available to process"
        )

    job.status = "processing"
    db.commit()
    db.refresh(job)

    try:
        ocr_service = OCRService()

        result = ocr_service.process(
            page_id=page.id,
            input_data=str(image_path),
        )

        job.status = "completed"
        job.result_metadata = result

        db.commit()
        db.refresh(job)

        return result

    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)

        db.commit()
        db.refresh(job)

        raise


def run_vlm_job(
    *,
    db: Session,
    job: AIJob,
) -> dict:
    page = db.get(Page, job.page_id)

    if page is None:
        raise ValueError(f"Page {job.page_id} not found")

    image_path = (
        getattr(page, "processed_path", None)
        or page.original_path
    )

    if not image_path:
        raise ValueError(
            f"Page {page.id} has no image available to process"
        )

    params = job.parameters or {}

    # ---------------------------------------------------------
    # Get OCR text
    # ---------------------------------------------------------

    ocr_text = params.get("ocr_text", "")

    # If OCR text was not manually supplied,
    # look for a completed OCR job for this page.
    if not ocr_text:

        ocr_job = (
            db.query(AIJob)
            .filter(
                AIJob.page_id == page.id,
                AIJob.job_type == "OCR",
                AIJob.status == "completed",
            )
            .order_by(AIJob.id.desc())
            .first()
        )

        if ocr_job and ocr_job.result_metadata:
            ocr_result = ocr_job.result_metadata

            if isinstance(ocr_result, dict):
                ocr_text = ocr_result.get("text", "")

    # ---------------------------------------------------------
    # Get script
    # ---------------------------------------------------------

    script = params.get("script", "unknown")

    # ---------------------------------------------------------
    # Run Gemini VLM
    # ---------------------------------------------------------

    job.status = "processing"
    db.commit()
    db.refresh(job)

    try:
        vlm_service = VLMService()

        result = vlm_service.process(
            page_id=page.id,
            input_data={
                "image_path": str(image_path),
                "ocr_text": ocr_text,
                "script": script,
            },
        )

        job.status = "completed"
        job.result_metadata = result

        db.commit()
        db.refresh(job)

        return result

    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)

        db.commit()
        db.refresh(job)

        raise