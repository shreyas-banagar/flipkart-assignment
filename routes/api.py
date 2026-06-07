import os
import tempfile
import threading
import uuid
import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.db import SessionLocal
from models.product import Product
from models.verification_log import VerificationLog
from models.user import User
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


def _verify_user_role(username: str, expected_role: str, db: Session) -> None:
    user = db.scalars(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username '{username}' not found.",
        )
    if user.role != expected_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Only users with role '{expected_role}' can perform this action.",
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/ingest", summary="Ingest product CSV data", status_code=status.HTTP_202_ACCEPTED)
async def ingest_data(
    background_tasks: BackgroundTasks,
    username: str = Form(..., description="Username of the warehouse manager."),
    file: UploadFile = File(...),
    batch_size: int = Query(1000, gt=0, le=10000, description="Rows to write per database commit batch."),
    db: Session = Depends(get_db),
):
    """Start ingestion of a CSV file in the background.

    The Swagger UI will render a browse button for file upload.
    """
    _verify_user_role(username, "warehouse-manager", db)

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
def get_ingest_status(
    task_id: str,
    username: str = Query(..., description="Username of the warehouse manager."),
    db: Session = Depends(get_db),
):
    _verify_user_role(username, "warehouse-manager", db)

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


@router.post("/products/validate", summary="Validate product details on-the-floor", status_code=status.HTTP_200_OK)
async def validate_product(
    wid: str = Form(..., description="Unique Warehouse ID (from barcode)."),
    username: str = Form(..., description="Username of the warehouse operator."),
    file: UploadFile = File(..., description="Captured image of the physical product."),
    db: Session = Depends(get_db),
):
    """Validate product details and log the validation event."""
    _verify_user_role(username, "warehouse-operator", db)

    product = db.scalars(select(Product).where(Product.wid == wid)).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with WID '{wid}' not found.",
        )

    # Save uploaded file
    upload_dir = os.path.join("data", "uploads", "validations")
    os.makedirs(upload_dir, exist_ok=True)
    
    file_ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    with open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)

    # Log the verification event
    db_file_path = file_path.replace("\\", "/")
    log_entry = VerificationLog(
        wid=wid,
        user_id=username,
        image_path=db_file_path,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    return {
        "wid": product.wid,
        "ean": product.ean,
        "manufacturing_date": product.manufacturing_date,
        "expiry_date": product.expiry_date,
        "verification_log_id": log_entry.id,
        "verified_at": log_entry.verified_at,
    }


@router.get("/reports/verification", summary="Generate verification report", status_code=status.HTTP_200_OK)
def get_verification_report(
    start_date: datetime.date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: datetime.date = Query(..., description="End date (YYYY-MM-DD)"),
    username: str = Query(..., description="Username of the QA manager."),
    db: Session = Depends(get_db),
):
    """Generate a report of all verification activities within a date range.
    Only users with the quality-assurance-manager role can access this.
    """
    _verify_user_role(username, "quality-assurance-manager", db)

    # Convert dates to datetime for correct filtering
    start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
    end_datetime = datetime.datetime.combine(end_date, datetime.time.max)

    logs = db.scalars(
        select(VerificationLog)
        .where(VerificationLog.verified_at >= start_datetime)
        .where(VerificationLog.verified_at <= end_datetime)
        .order_by(VerificationLog.verified_at.desc())
    ).all()

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_verifications": len(logs),
        "verifications": [
            {
                "id": log.id,
                "wid": log.wid,
                "operator_username": log.user_id,
                "image_path": log.image_path,
                "verified_at": log.verified_at,
            }
            for log in logs
        ]
    }
