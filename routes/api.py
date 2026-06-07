import os
import tempfile
import threading
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.db import SessionLocal
from models.product import Product
from services.api import ingest_products_from_path

router = APIRouter(prefix="/api", tags=["ingest"])

ingest_jobs: dict[str, dict] = {}
ingest_jobs_lock = threading.Lock()


def _update_job(task_id: str, **fields: object) -> None:
    with ingest_jobs_lock:
        if task_id in ingest_jobs:
            ingest_jobs[task_id].update(fields)


def _run_ingest_job(task_id: str, file_path: str, batch_size: int) -> None:
    _update_job(task_id, status="running")
    db = SessionLocal()
    try:
        def on_progress(count: int) -> None:
            _update_job(task_id, ingested_rows=count)

        ingested_rows = ingest_products_from_path(
            file_path, db, batch_size=batch_size, on_progress=on_progress
        )
        _update_job(task_id, status="succeeded", ingested_rows=ingested_rows)
    except Exception as exc:
        _update_job(task_id, status="failed", error=str(exc))
    finally:
        db.close()
        try:
            os.remove(file_path)
        except OSError:
            pass


def _get_product_table_count() -> int:
    db = SessionLocal()
    try:
        result = db.scalar(select(func.count()).select_from(Product))
        return int(result or 0)
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/ingest", summary="Ingest product CSV data", status_code=status.HTTP_202_ACCEPTED)
async def ingest_data(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    batch_size: int = Query(1000, gt=0, le=10000, description="Rows to write per database commit batch."),
):
    """Start ingestion of a CSV file in the background.

    The Swagger UI will render a browse button for file upload.
    """
    if file.content_type not in ("text/csv", "application/vnd.ms-excel"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are accepted. Upload a valid CSV file.",
        )

    baseline_rows = _get_product_table_count()
    task_id = uuid.uuid4().hex
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as temp_file:
        while content := await file.read(1024 * 1024):
            temp_file.write(content)
        temp_path = temp_file.name

    with ingest_jobs_lock:
        ingest_jobs[task_id] = {
            "status": "queued",
            "batch_size": batch_size,
            "ingested_rows": 0,
            "baseline_rows": baseline_rows,
            "error": None,
        }

    background_tasks.add_task(_run_ingest_job, task_id, temp_path, batch_size)
    return {"task_id": task_id, "status": "accepted"}


@router.get("/ingest/status/{task_id}", summary="Get ingestion job status")
def get_ingest_status(task_id: str):
    job = ingest_jobs.get(task_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingestion task not found.",
        )

    if job.get("baseline_rows") is not None:
        current_rows = _get_product_table_count()
        job = {
            **job,
            "table_rows": current_rows,
        }

    return job
