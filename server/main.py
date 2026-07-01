"""FastAPI server for Siakang Academic Monitoring.

This API provides endpoints for:
- CRUD operations for task monitoring
- Start/Stop monitoring processes
- View logs and scraped data
- Login validation and semester fetching

Server uses:
- FastAPI for REST API
- SQLite for persistence
- Subprocess for running worker processes
"""

import os
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db, get_db_connection
from .models import TaskCreate, TaskUpdate, ApiResponse
from .manager import (
    start_process, stop_process, get_logs, restore_running_tasks,
    get_last_values, cleanup_task_files, run_process_once, clear_logs,
    clear_data, check_process_status,
)

try:
    from scraper_lib import SiakangScraper
except ImportError:  # pragma: no cover - fallback when project root not on sys.path
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        from scraper_lib import SiakangScraper
    except ImportError:
        SiakangScraper = None


# CORS origins are configurable via env. Wildcard "*" disables credentials:
# browsers and the CORS spec forbid wildcard origin together with credentials.
_origins_env = os.getenv("CORS_ORIGINS", "*").strip()
if _origins_env == "*":
    _allow_origins = ["*"]
    _allow_credentials = False
else:
    _allow_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]
    _allow_credentials = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    restore_running_tasks()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/verify-pin")
def verify_pin(payload: dict = Body(...)):
    pin = payload.get("pin")
    app_pin = os.getenv("APP_PIN")
    if not app_pin:
        raise HTTPException(status_code=500, detail="PIN not configured")
    if pin == app_pin:
        return {"success": True}
    raise HTTPException(status_code=401, detail="PIN incorrect")

@app.get("/tasks", response_model=ApiResponse[List[dict]])
def list_tasks():
    conn = get_db_connection()
    tasks = conn.execute('SELECT * FROM tasks ORDER BY position ASC, id ASC').fetchall()
    conn.close()
    
    task_list = [dict(t) for t in tasks]
    for task in task_list:
        if task['status'] == 'running':
            check_process_status(task['id'])
    
    conn = get_db_connection()
    tasks = conn.execute('SELECT * FROM tasks ORDER BY position ASC, id ASC').fetchall()
    conn.close()
    
    return ApiResponse(code=200, message="Success", data=[dict(t) for t in tasks])

@app.put("/tasks/reorder", response_model=ApiResponse[None])
def reorder_tasks(ordered_ids: List[int] = Body(...)):
    conn = get_db_connection()
    for index, task_id in enumerate(ordered_ids):
        conn.execute('UPDATE tasks SET position = ? WHERE id = ?', (index, task_id))
    conn.commit()
    conn.close()
    return ApiResponse(code=200, message="Tasks reordered")

@app.post("/tasks", response_model=ApiResponse[dict])
def create_task(task: TaskCreate):
    conn = get_db_connection()
    c = conn.execute(
        'INSERT INTO tasks (name, login_id, password, chat_id, target_semester_code, interval, monitor_type, target_courses, whatsapp_number, notify_without_grades_telegram, notify_without_grades_whatsapp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (task.name, task.login_id, task.password, task.chat_id, task.target_semester_code, task.interval, task.monitor_type, task.target_courses, task.whatsapp_number, int(task.notify_without_grades_telegram), int(task.notify_without_grades_whatsapp))
    )
    task_id = c.lastrowid
    conn.commit()
    conn.close()
    return ApiResponse(code=201, message="Task created", data={"id": task_id, **task.dict(), "status": "stopped"})

@app.put("/tasks/{task_id}", response_model=ApiResponse[None])
def update_task(task_id: int, task: TaskUpdate):
    conn = get_db_connection()
    
    fields = task.dict(exclude_unset=True)
    if not fields:
        return ApiResponse(code=400, message="No fields to update")
        
    query = "UPDATE tasks SET " + ", ".join(f"{k} = ?" for k in fields.keys()) + " WHERE id = ?"
    values = list(fields.values()) + [task_id]
    
    conn.execute(query, values)
    conn.commit()
    conn.close()
    
    return ApiResponse(code=200, message="Task updated")

@app.delete("/tasks/{task_id}", response_model=ApiResponse[None])
def delete_task(task_id: int):
    stop_process(task_id)
    cleanup_task_files(task_id)
    conn = get_db_connection()
    conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    return ApiResponse(code=200, message="Task deleted")

@app.post("/tasks/{task_id}/start", response_model=ApiResponse[None])
def start_task_endpoint(task_id: int):
    success, msg = start_process(task_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return ApiResponse(code=200, message=msg)

@app.post("/tasks/{task_id}/stop", response_model=ApiResponse[None])
def stop_task_endpoint(task_id: int, force: bool = False):
    success, msg = stop_process(task_id, force=force)
    return ApiResponse(code=200, message=msg)

@app.get("/tasks/{task_id}/logs", response_model=ApiResponse[str])
def get_logs_endpoint(task_id: int):
    return ApiResponse(code=200, message="Success", data=get_logs(task_id))

@app.delete("/tasks/{task_id}/logs", response_model=ApiResponse[None])
def clear_logs_endpoint(task_id: int):
    success, msg = clear_logs(task_id)
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return ApiResponse(code=200, message=msg)

@app.delete("/tasks/{task_id}/data", response_model=ApiResponse[None])
def clear_data_endpoint(task_id: int):
    success, msg = clear_data(task_id)
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return ApiResponse(code=200, message=msg)

@app.get("/tasks/{task_id}/data", response_model=ApiResponse[dict | list])
def get_data_endpoint(task_id: int):
    data = get_last_values(task_id)
    return ApiResponse(code=200, message="Success", data=data if data else [])

@app.post("/tasks/{task_id}/refresh", response_model=ApiResponse[None])
def refresh_task_data(task_id: int):
    success, msg = run_process_once(task_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return ApiResponse(code=200, message=msg)

@app.post("/check-semesters")
def check_semesters(credentials: dict = Body(...)):
    login_id = credentials.get("login_id")
    password = credentials.get("password")
    
    if not login_id or not password:
        raise HTTPException(status_code=400, detail="Missing login_id or password")
        
    if not SiakangScraper:
        raise HTTPException(status_code=500, detail="Scraper library not loaded")
        
    scraper = SiakangScraper(login_id, password)
    success, msg = scraper.login()
    
    if not success:
        raise HTTPException(status_code=401, detail=f"Login failed: {msg}")
        
    semesters = scraper.get_semesters()
    return {"semesters": semesters}
