# backend/main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json

from db import SessionLocal, engine, Base
from models import QAResult
from services.qa_runner import run_qa_sync

# Create all tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="QA Microservice")

# Allow frontend CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class RunRequest(BaseModel):
    url: str
    async_run: bool = False  # run in background

# Helper to save results
def save_result(db, url, findings):
    record = QAResult(
        url=url,
        title=findings.get("title"),
        findings=json.dumps(findings)
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

# Endpoint to run QA
@app.post("/run-test")
def run_test(payload: RunRequest, background_tasks: BackgroundTasks):
    url = payload.url

    if payload.async_run:
        # Run QA in background
        def bg_task(url=url):
            findings = run_qa_sync(url)
            db = SessionLocal()
            save_result(db, url, findings)
            db.close()
        background_tasks.add_task(bg_task)
        return {"status": "scheduled"}

    # synchronous run
    try:
        findings = run_qa_sync(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    db = SessionLocal()
    record = save_result(db, url, findings)
    db.close()
    return {"result_id": record.id, "findings": findings}

# Endpoint to list results
@app.get("/results")
def list_results(limit: int = 100):
    db = SessionLocal()
    rows = db.query(QAResult).order_by(QAResult.created_at.desc()).limit(limit).all()
    db.close()
    return rows

# Endpoint to get a single result by ID
@app.get("/results/{result_id}")
def get_result(result_id: int):
    db = SessionLocal()
    row = db.query(QAResult).filter(QAResult.id == result_id).first()
    db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Result not found")
    return row
