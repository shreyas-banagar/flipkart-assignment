import csv
import datetime
import io
from typing import Callable

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import Date
from sqlalchemy.orm import Session

from database.db import engine
from models.product import Product

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None


def _parse_date(value: str, field_name: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(value.strip())
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid date format for '{field_name}'. Use YYYY-MM-DD.",
        )


def _get_ingest_metadata() -> tuple[list[str], set[str]]:
    # Include all table columns except created_at and those with explicit defaults.
    # Only exclude columns that have a server_default or default set, or where
    # autoincrement is explicitly True (i.e., numeric PKs managed by the DB).
    ingest_columns = []
    for column in Product.__table__.columns:
        if column.name == "created_at":
            continue
        if column.server_default is not None:
            continue
        if column.default is not None:
            continue
        if getattr(column, "autoincrement", None) is True:
            continue
        ingest_columns.append(column)
    expected_fields = [column.name for column in ingest_columns]
    date_fields = {column.name for column in ingest_columns if isinstance(column.type, Date)}
    if not expected_fields:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=("No ingestable columns were detected from the Product model. "
                    "Check model column definitions."),
        )

    return expected_fields, date_fields


def _copy_products_from_path(file_path: str, expected_fields: list[str], on_progress: Callable[[int], None] = None) -> int:
    if psycopg is None:
        raise RuntimeError(
            "psycopg is required for PostgreSQL COPY. Install psycopg[binary] or use the standard ingest path."
        )

    table_name = Product.__table__.name
    columns = ", ".join(expected_fields)
    copy_sql = f"COPY {table_name} ({columns}) FROM STDIN WITH CSV HEADER DELIMITER ','"

    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cursor:
            newline_count = 0
            last_chunk = b""
            with open(file_path, "rb") as file:
                with cursor.copy(copy_sql) as copy:
                    while chunk := file.read(16 * 1024):
                        copy.write(chunk)
                        newline_count += chunk.count(b"\n")
                        last_chunk = chunk
                        # Call on_progress with estimated number of lines written to COPY stream so far
                        if on_progress:
                            # subtract 1 for header line if it's already read
                            on_progress(max(newline_count - 1, 0))
        raw_conn.commit()
    finally:
        raw_conn.close()

    line_count = newline_count + (1 if last_chunk and not last_chunk.endswith(b"\n") else 0)
    final_count = max(line_count - 1, 0)
    if on_progress:
        on_progress(final_count)
    return final_count


def _ingest_from_reader(reader, expected_fields: list[str], date_fields: set[str], db: Session, batch_size: int, on_progress: Callable[[int], None] = None) -> int:
    header = next(reader, None)
    if not header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"CSV must include headers: {', '.join(expected_fields)}."),
        )

    # Build a case-insensitive header map (lowercased keys)
    header_map = {name.strip().lower(): index for index, name in enumerate(header)}
    expected_lc = [f.lower() for f in expected_fields]
    missing = set(expected_lc) - set(header_map.keys())
    if missing:
        missing_display = ", ".join(sorted(missing))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"CSV missing headers: {missing_display}. Expected headers (case-insensitive): {', '.join(expected_fields)}."),
        )

    # Map original field names to their column index using case-insensitive lookup
    field_indexes = {field: header_map[field.lower()] for field in expected_fields}
    batch = []
    total = 0
    insert_stmt = Product.__table__.insert()

    for row in reader:
        if not row:
            continue

        record = {}
        missing_value = False
        for field, index in field_indexes.items():
            value = row[index].strip() if index < len(row) else ""
            if not value:
                missing_value = True
                break
            record[field] = _parse_date(value, field) if field in date_fields else value

        if missing_value:
            continue

        # Defensive: ensure we only append non-empty records with expected keys
        if not record or set(record.keys()) != set(expected_fields):
            # skip malformed row but continue processing others
            continue

        batch.append(record)

        if len(batch) >= batch_size:
            db.execute(insert_stmt, batch)
            db.commit()
            total += len(batch)
            if on_progress:
                on_progress(total)
            batch.clear()

    if batch:
        db.execute(insert_stmt, batch)
        db.commit()
        total += len(batch)
        if on_progress:
            on_progress(total)

    return total


def ingest_products(file: UploadFile, db: Session, batch_size: int = 1000, on_progress: Callable[[int], None] = None) -> int:
    """Read CSV rows from the uploaded file and persist products in batches."""
    try:
        file.file.seek(0)
    except Exception:
        pass

    expected_fields, date_fields = _get_ingest_metadata()
    text_stream = io.TextIOWrapper(file.file, encoding="utf-8", newline="")
    reader = csv.reader(text_stream)
    return _ingest_from_reader(reader, expected_fields, date_fields, db, batch_size, on_progress)


def ingest_products_from_path(file_path: str, db: Session, batch_size: int = 1000, on_progress: Callable[[int], None] = None) -> int:
    """Read CSV rows from a saved file path and persist products in batches."""
    expected_fields, date_fields = _get_ingest_metadata()

    if engine.dialect.name == "postgresql" and psycopg is not None:
        return _copy_products_from_path(file_path, expected_fields, on_progress)

    with open(file_path, "rb") as file:
        text_stream = io.TextIOWrapper(file, encoding="utf-8", newline="")
        reader = csv.reader(text_stream)
        return _ingest_from_reader(reader, expected_fields, date_fields, db, batch_size, on_progress)
