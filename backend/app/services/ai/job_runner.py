from app.models.ai_job import AIJob
from app.models.artifact import Artifact
from app.models.page import Page
from app.services.ai.evaluation import EvaluationService
from app.services.ai.ocr import OCRService
from app.services.ai.rag import RAGService
from app.services.ai.reconstruction import ReconstructionService
from app.services.ai.vlm import VLMService
from app.services.provenance import create_artifact
from sqlalchemy import select
from sqlalchemy.orm import Session


def run_ocr_vlm_job(
    *,
    db: Session,
    job: AIJob,
) -> dict:
    """
    B2.8.3 pipeline:
        Page image -> OCR -> Gemini / VLM -> Final transcription -> Save Artifact
    """
    page = db.get(Page, job.page_id)

    if page is None:
        raise ValueError(f"Page {job.page_id} not found")

    # 1. Locate page image
    image_path = getattr(page, "processed_path", None) or page.original_path

    if not image_path:
        raise ValueError(f"Page {page.id} has no image available")

    # 2. Mark job as processing
    job.status = "processing"
    job.error_message = None
    db.commit()
    db.refresh(job)

    try:
        # 3. Run OCR
        ocr_service = OCRService()
        ocr_result = ocr_service.process(
            page_id=page.id,
            input_data=image_path,
        )
        ocr_text = ocr_result.get("text", "")

        # 4. Determine script
        params = job.parameters or {}
        script = params.get("script", "Devanagari")

        # 5. Run Gemini / VLM
        vlm_service = VLMService()
        vlm_result = vlm_service.process(
            page_id=page.id,
            input_data={
                "image_path": str(image_path),
                "ocr_text": ocr_text,
                "script": script,
            },
        )

        final_text = vlm_result.get("analysis") or ocr_text

        # 6. Build final result dict
        result = {
            "page_id": page.id,
            "image_path": str(image_path),
            "ocr": {
                "text": ocr_text,
                "regions": ocr_result.get("regions", []),
            },
            "vlm": {
                "model": vlm_result.get("model"),
                "script": vlm_result.get("script"),
                "analysis": vlm_result.get("analysis"),
            },
            "final_transcription": final_text,
        }

        # 7. Create Artifact so frontend can load it
        artifact = create_artifact(
            db=db,
            page_id=page.id,
            artifact_type="OCR",
            content=final_text,
            generation_method="ai",
            model_name=vlm_result.get("model") or "PaddleOCR+Gemini",
            metadata={
                "confidence": 92,
                "script": script,
                "raw_ocr": ocr_text,
            },
        )

        # 8. Complete job
        job.status = "completed"
        job.output_artifact_id = artifact.id
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


def run_reconstruction_job(
    *,
    db: Session,
    job: AIJob,
) -> dict:
    page = db.get(Page, job.page_id)

    if page is None:
        raise ValueError(f"Page {job.page_id} not found")

    # 1. Grab the image path so the AI can actually see the page
    image_path = getattr(page, "processed_path", None) or page.original_path

    params = job.parameters or {}

    ocr_text = params.get("ocr_text")
    if not ocr_text:
        latest_ocr = db.scalar(
            select(Artifact)
            .where(Artifact.page_id == page.id, Artifact.artifact_type == "OCR")
            .order_by(Artifact.version.desc())
        )
        ocr_text = latest_ocr.content if latest_ocr else ""

    corrected_text = params.get("corrected_text", "")
    rag_context = params.get("rag_context", "")
    script = params.get("script", "Devanagari")

    job.status = "processing"
    db.commit()
    db.refresh(job)

    try:
        service = ReconstructionService()
        result = service.process(
            page_id=page.id,
            input_data={
                "image_path": str(image_path), # <--- ADD THIS LINE
                "ocr_text": ocr_text,
                "corrected_text": corrected_text,
                "rag_context": rag_context,
                "script": script,
            },
        )

        recon_text = result.get("reconstructed_text") or result.get("text") or str(result)

        artifact = create_artifact(
            db=db,
            page_id=page.id,
            artifact_type="RECONSTRUCTION",
            content=recon_text,
            generation_method="ai",
            model_name="Gemini/Reconstruction",
            metadata={
                "confidence": result.get("confidence", 95),
                "script": script,
            },
        )

        job.status = "completed"
        job.output_artifact_id = artifact.id
        job.result_metadata = result
        db.commit()
        db.refresh(job)

        return result

    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        db.commit()
        raise


def run_rag_job(
    *,
    db: Session,
    job: AIJob,
) -> dict:
    page = db.get(Page, job.page_id)

    if page is None:
        raise ValueError(f"Page {job.page_id} not found")

    params = job.parameters or {}
    query = params.get("query")

    if not query:
        raise ValueError("RAG job requires parameters.query")

    job.status = "processing"
    db.commit()
    db.refresh(job)

    try:
        rag_service = RAGService()
        result = rag_service.process(
            page_id=page.id,
            input_data={
                "query": query,
                "limit": params.get("limit", 5),
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
        raise


def run_evaluation_job(
    *,
    db: Session,
    job: AIJob,
) -> dict:
    page = db.get(Page, job.page_id)

    if page is None:
        raise ValueError(f"Page {job.page_id} not found")

    params = job.parameters or {}
    predicted_text = params.get("predicted_text", "")
    reference_text = params.get("reference_text", "")

    if not predicted_text:
        raise ValueError("Evaluation job requires parameters.predicted_text")

    job.status = "processing"
    job.error_message = None
    db.commit()
    db.refresh(job)

    try:
        service = EvaluationService()
        result = service.process(
            page_id=page.id,
            input_data={
                "predicted_text": predicted_text,
                "reference_text": reference_text,
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


def run_ai_job(
    *,
    db: Session,
    job: AIJob,
) -> dict:
    if job.job_type == "RAG":
        return run_rag_job(db=db, job=job)

    if job.job_type == "RECONSTRUCTION":
        return run_reconstruction_job(db=db, job=job)

    if job.job_type == "EVALUATION":
        return run_evaluation_job(db=db, job=job)

    if job.job_type in {"OCR", "LLM_ANALYSIS", "VLM", "SCRIPT_DETECTION"}:
        return run_ocr_vlm_job(db=db, job=job)

    raise ValueError(f"No AI runner implemented for job type: {job.job_type}")