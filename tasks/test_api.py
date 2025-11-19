import json
import os
import sqlite3
import pytest
from django.conf import settings
from django.test import Client

DB_PATH = os.path.join(settings.BASE_DIR, 'db.sqlite3')

@pytest.fixture(autouse=True)
def clean_db():
    # Reset tasks table before each test
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks;")
    conn.commit()
    conn.close()
    yield

def test_create_task(client: Client):
    payload = {
        "title": "Test Task",
        "description": "Desc",
        "due_date": "2025-12-31",
        "status": "pending"
    }
    res = client.post('/api/tasks/', data=json.dumps(payload), content_type='application/json')
    assert res.status_code == 201
    data = res.json()
    assert data['title'] == "Test Task"
    assert data['status'] == "pending"

def test_list_tasks(client: Client):
    # create two
    client.post('/api/tasks/', data=json.dumps({"title": "A"}), content_type='application/json')
    client.post('/api/tasks/', data=json.dumps({"title": "B"}), content_type='application/json')
    res = client.get('/api/tasks/')
    assert res.status_code == 200
    data = res.json()
    assert len(data['tasks']) == 2

def test_get_single_task(client: Client):
    res = client.post('/api/tasks/', data=json.dumps({"title": "Single"}), content_type='application/json')
    tid = res.json()['id']
    res2 = client.get(f'/api/tasks/{tid}/')
    assert res2.status_code == 200
    assert res2.json()['title'] == 'Single'

def test_update_task_status(client: Client):
    res = client.post('/api/tasks/', data=json.dumps({"title": "Update"}), content_type='application/json')
    tid = res.json()['id']
    res2 = client.put(f'/api/tasks/{tid}/', data=json.dumps({"status":"done"}), content_type='application/json')
    assert res2.status_code == 200
    assert res2.json()['status'] == 'done'

def test_delete_task(client: Client):
    res = client.post('/api/tasks/', data=json.dumps({"title": "Delete"}), content_type='application/json')
    tid = res.json()['id']
    res2 = client.delete(f'/api/tasks/{tid}/')
    assert res2.status_code == 200
    assert res2.json()['deleted'] == tid

def test_validation_errors(client: Client):
    res = client.post('/api/tasks/', data=json.dumps({"description":"no title"}), content_type='application/json')
    assert res.status_code == 400
    assert 'title is required' in res.json()['errors']
