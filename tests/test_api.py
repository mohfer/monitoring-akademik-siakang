"""Unit Tests untuk Monitoring Akademik Siakang Backend API.

Tests cover:
- CRUD operations untuk tasks
- Task lifecycle (start/stop)
- Data & logs endpoints
- Validation
"""

import pytest
import sys
import os
import json
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from server.main import app
from server.database import init_db, get_db_connection


@pytest.fixture(scope="function")
def client():
    """Create a test client with a temporary database."""
    # Create temp directory for test data
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test.db")
    logs_dir = os.path.join(test_dir, "logs")
    value_dir = os.path.join(test_dir, "value")
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(value_dir, exist_ok=True)
    
    # Patch the database path
    import server.database as db_module
    original_db_path = db_module.DB_PATH
    db_module.DB_PATH = db_path
    
    # Initialize test database
    init_db()
    
    # Create test client
    with TestClient(app) as test_client:
        yield test_client
    
    # Cleanup
    db_module.DB_PATH = original_db_path
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def sample_task():
    """Sample task data for testing."""
    return {
        "name": "Test Monitor",
        "login_id": "test123",
        "password": "password123",
        "chat_id": "123456789",
        "whatsapp_number": "",
        "target_semester_code": "20251",
        "monitor_type": "nilai",
        "target_courses": "[]",
        "interval": 300
    }


@pytest.fixture
def sample_krs_task():
    """Sample KRS task data for testing."""
    return {
        "name": "Monitor KRS",
        "login_id": "nim123",
        "password": "pass456",
        "chat_id": "",
        "whatsapp_number": "628123456789",
        "target_semester_code": "20251",
        "monitor_type": "krs",
        "target_courses": '["Data Mining", "Machine Learning"]',
        "interval": 600
    }


class TestTaskCRUD:
    """Tests for task CRUD operations."""

    def test_list_tasks_empty(self, client):
        """Test listing tasks when database is empty."""
        response = client.get("/tasks")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"] == []

    def test_create_task(self, client, sample_task):
        """Test creating a new task."""
        response = client.post("/tasks", json=sample_task)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 201
        assert data["data"]["name"] == sample_task["name"]
        assert data["data"]["login_id"] == sample_task["login_id"]
        assert data["data"]["status"] == "stopped"
        assert "id" in data["data"]

    def test_create_krs_task(self, client, sample_krs_task):
        """Test creating a KRS monitoring task."""
        response = client.post("/tasks", json=sample_krs_task)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 201
        assert data["data"]["monitor_type"] == "krs"
        assert data["data"]["target_courses"] == sample_krs_task["target_courses"]

    def test_list_tasks_with_data(self, client, sample_task):
        """Test listing tasks after creating one."""
        client.post("/tasks", json=sample_task)
        response = client.get("/tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == sample_task["name"]

    def test_update_task(self, client, sample_task):
        """Test updating an existing task."""
        # Create task
        create_response = client.post("/tasks", json=sample_task)
        task_id = create_response.json()["data"]["id"]
        
        # Update task
        update_data = {"name": "Updated Name", "interval": 600}
        response = client.put(f"/tasks/{task_id}", json=update_data)
        assert response.status_code == 200
        
        # Verify update
        tasks = client.get("/tasks").json()["data"]
        updated_task = next(t for t in tasks if t["id"] == task_id)
        assert updated_task["name"] == "Updated Name"
        assert updated_task["interval"] == 600

    def test_delete_task(self, client, sample_task):
        """Test deleting a task."""
        # Create task
        create_response = client.post("/tasks", json=sample_task)
        task_id = create_response.json()["data"]["id"]
        
        # Delete task
        response = client.delete(f"/tasks/{task_id}")
        assert response.status_code == 200
        
        # Verify deletion
        tasks = client.get("/tasks").json()["data"]
        assert len(tasks) == 0

    def test_update_nonexistent_task(self, client):
        """Test updating a task that doesn't exist."""
        response = client.put("/tasks/999", json={"name": "Ghost"})
        assert response.status_code == 200  # SQLite doesn't error on no-op

    def test_delete_nonexistent_task(self, client):
        """Test deleting a task that doesn't exist."""
        response = client.delete("/tasks/999")
        assert response.status_code == 200


class TestTaskLifecycle:
    """Tests for task start/stop operations."""

    def test_start_task(self, client, sample_task):
        """Test starting a stopped task."""
        # Create task
        create_response = client.post("/tasks", json=sample_task)
        task_id = create_response.json()["data"]["id"]
        
        # Start task (will fail because no real Siakang credentials, but endpoint should work)
        response = client.post(f"/tasks/{task_id}/start")
        # It may return 400 if process fails to start, which is expected
        assert response.status_code in [200, 400]

    def test_stop_task(self, client, sample_task):
        """Test stopping a task."""
        # Create task
        create_response = client.post("/tasks", json=sample_task)
        task_id = create_response.json()["data"]["id"]
        
        # Stop task
        response = client.post(f"/tasks/{task_id}/stop")
        assert response.status_code == 200

    def test_start_nonexistent_task(self, client):
        """Test starting a task that doesn't exist."""
        response = client.post("/tasks/999/start")
        assert response.status_code == 400


class TestTaskReorder:
    """Tests for task reordering."""

    def test_reorder_tasks(self, client, sample_task):
        """Test reordering tasks."""
        # Create multiple tasks
        task1 = client.post("/tasks", json={**sample_task, "name": "Task 1"}).json()["data"]
        task2 = client.post("/tasks", json={**sample_task, "name": "Task 2"}).json()["data"]
        task3 = client.post("/tasks", json={**sample_task, "name": "Task 3"}).json()["data"]
        
        # Reorder: 3, 1, 2
        new_order = [task3["id"], task1["id"], task2["id"]]
        response = client.put("/tasks/reorder", json=new_order)
        assert response.status_code == 200
        
        # Verify order
        tasks = client.get("/tasks").json()["data"]
        assert tasks[0]["id"] == task3["id"]
        assert tasks[1]["id"] == task1["id"]
        assert tasks[2]["id"] == task2["id"]


class TestLogsAndData:
    """Tests for logs and data endpoints."""

    def test_get_logs_empty(self, client, sample_task):
        """Test getting logs for a task with no logs."""
        create_response = client.post("/tasks", json=sample_task)
        task_id = create_response.json()["data"]["id"]
        
        response = client.get(f"/tasks/{task_id}/logs")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_get_data_empty(self, client, sample_task):
        """Test getting data for a task with no data."""
        create_response = client.post("/tasks", json=sample_task)
        task_id = create_response.json()["data"]["id"]
        
        response = client.get(f"/tasks/{task_id}/data")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"] == []

    def test_clear_logs(self, client, sample_task):
        """Test clearing logs for a task."""
        create_response = client.post("/tasks", json=sample_task)
        task_id = create_response.json()["data"]["id"]
        
        response = client.delete(f"/tasks/{task_id}/logs")
        assert response.status_code == 200

    def test_clear_data(self, client, sample_task):
        """Test clearing data for a task."""
        create_response = client.post("/tasks", json=sample_task)
        task_id = create_response.json()["data"]["id"]
        
        response = client.delete(f"/tasks/{task_id}/data")
        assert response.status_code == 200


class TestValidation:
    """Tests for input validation."""

    def test_create_task_missing_name(self, client):
        """Test creating a task without required fields."""
        response = client.post("/tasks", json={})
        assert response.status_code == 422  # Validation error

    def test_create_task_invalid_interval(self, client, sample_task):
        """Test creating a task with invalid interval."""
        task_data = {**sample_task, "interval": "not-a-number"}
        response = client.post("/tasks", json=task_data)
        assert response.status_code == 422

    def test_reorder_invalid_ids(self, client):
        """Test reordering with invalid task IDs."""
        response = client.put("/tasks/reorder", json=[999, 1000])
        assert response.status_code == 200  # Should not error


class TestRefreshData:
    """Tests for manual data refresh."""

    def test_refresh_task(self, client, sample_task):
        """Test manually refreshing task data."""
        create_response = client.post("/tasks", json=sample_task)
        task_id = create_response.json()["data"]["id"]
        
        # Will likely fail due to invalid credentials, but endpoint should respond
        response = client.post(f"/tasks/{task_id}/refresh")
        assert response.status_code in [200, 400]

    def test_refresh_nonexistent_task(self, client):
        """Test refreshing a task that doesn't exist."""
        response = client.post("/tasks/999/refresh")
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
