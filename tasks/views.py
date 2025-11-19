# Create your views here.
import json
import sqlite3
import os
import logging
from django.http import JsonResponse, HttpResponseNotAllowed, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.conf import settings

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(settings.BASE_DIR, 'db.sqlite3')

def dict_from_row(cursor, row):
    cols = [c[0] for c in cursor.description]
    return {c: row[i] for i, c in enumerate(cols)}

def validate_task_payload(data, partial=False):
    errors = []
    # required fields for create
    if not partial:
        if 'title' not in data or not str(data['title']).strip():
            errors.append('title is required')
        if 'status' not in data:
            data['status'] = 'pending'
    # validate status
    if 'status' in data and data['status'] not in ['pending','in_progress','done']:
        errors.append("status must be one of ['pending','in_progress','done']")
    # validate due_date format (basic check)
    if 'due_date' in data and data['due_date']:
        # very light validation: YYYY-MM-DD length check
        s = str(data['due_date'])
        if len(s) != 10 or s[4] != '-' or s[7] != '-':
            errors.append('due_date must be YYYY-MM-DD')
    return errors

# -------- API: Collection (GET list, POST create)
@csrf_exempt
def tasks_collection(request):
    if request.method == 'GET':
        logger.info("Listing tasks")
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, title, description, due_date, status FROM tasks ORDER BY id DESC")
            rows = cur.fetchall()
            tasks = []
            for row in rows:
                tasks.append({
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'due_date': row[3],
                    'status': row[4],
                })
            return JsonResponse({'tasks': tasks}, status=200)
        except Exception as e:
            logger.exception("Error listing tasks: %s", e)
            return JsonResponse({'error': 'internal_server_error'}, status=500)
        finally:
            conn.close()

    if request.method == 'POST':
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'error': 'invalid_json'}, status=400)

        errors = validate_task_payload(payload, partial=False)
        if errors:
            return JsonResponse({'errors': errors}, status=400)

        title = payload.get('title')
        description = payload.get('description') or ''
        due_date = payload.get('due_date') or None
        status = payload.get('status', 'pending')

        logger.info("Creating task: %s", title)
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO tasks (title, description, due_date, status) VALUES (?, ?, ?, ?)",
                (title, description, due_date, status)
            )
            conn.commit()
            task_id = cur.lastrowid
            return JsonResponse({
                'id': task_id,
                'title': title,
                'description': description,
                'due_date': due_date,
                'status': status
            }, status=201)
        except Exception as e:
            logger.exception("Error creating task: %s", e)
            return JsonResponse({'error': 'internal_server_error'}, status=500)
        finally:
            conn.close()

    return HttpResponseNotAllowed(['GET', 'POST'])

# -------- API: Item (GET one, PUT update, DELETE)
@csrf_exempt
def tasks_item(request, task_id: int):
    if request.method == 'GET':
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, title, description, due_date, status FROM tasks WHERE id = ?", (task_id,))
            row = cur.fetchone()
            if not row:
                return JsonResponse({'error': 'not_found'}, status=404)
            task = {
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'due_date': row[3],
                'status': row[4],
            }
            return JsonResponse(task, status=200)
        except Exception as e:
            logger.exception("Error retrieving task %s: %s", task_id, e)
            return JsonResponse({'error': 'internal_server_error'}, status=500)
        finally:
            conn.close()

    if request.method == 'PUT':
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'error': 'invalid_json'}, status=400)

        errors = validate_task_payload(payload, partial=True)
        if errors:
            return JsonResponse({'errors': errors}, status=400)

        fields = []
        values = []
        for key in ['title', 'description', 'due_date', 'status']:
            if key in payload:
                fields.append(f"{key} = ?")
                values.append(payload[key] if key != 'description' else (payload[key] or ''))
        if not fields:
            return JsonResponse({'error': 'no_fields_to_update'}, status=400)

        logger.info("Updating task %s with %s", task_id, payload)
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.cursor()
            values.append(task_id)
            sql = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?"
            cur.execute(sql, tuple(values))
            if cur.rowcount == 0:
                return JsonResponse({'error': 'not_found'}, status=404)
            conn.commit()

            cur.execute("SELECT id, title, description, due_date, status FROM tasks WHERE id = ?", (task_id,))
            row = cur.fetchone()
            task = {
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'due_date': row[3],
                'status': row[4],
            }
            return JsonResponse(task, status=200)
        except Exception as e:
            logger.exception("Error updating task %s: %s", task_id, e)
            return JsonResponse({'error': 'internal_server_error'}, status=500)
        finally:
            conn.close()

    if request.method == 'DELETE':
        logger.info("Deleting task %s", task_id)
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            if cur.rowcount == 0:
                return JsonResponse({'error': 'not_found'}, status=404)
            conn.commit()
            return JsonResponse({'deleted': task_id}, status=200)
        except Exception as e:
            logger.exception("Error deleting task %s: %s", task_id, e)
            return JsonResponse({'error': 'internal_server_error'}, status=500)
        finally:
            conn.close()

    return HttpResponseNotAllowed(['GET', 'PUT', 'DELETE'])

# -------- HTML pages (Templates)

def task_list_page(request):
    # server-side render using API data via direct DB query to avoid circular HTTP
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, title, description, due_date, status FROM tasks ORDER BY id DESC")
        tasks = [{
            'id': row[0],
            'title': row[1],
            'description': row[2],
            'due_date': row[3],
            'status': row[4],
        } for row in cur.fetchall()]
    finally:
        conn.close()
    return render(request, 'tasks/list.html', {'tasks': tasks})

@csrf_exempt
def task_add_page(request):
    if request.method == 'GET':
        return render(request, 'tasks/add.html')

    if request.method == 'POST':
        # the template will submit JSON via fetch; for non-JS fallback, process form fields too
        content_type = request.META.get('CONTENT_TYPE', '')
        try:
            if 'application/json' in content_type:
                payload = json.loads(request.body.decode('utf-8'))
                title = payload.get('title')
                description = payload.get('description') or ''
                due_date = payload.get('due_date') or None
                status = payload.get('status', 'pending')
            else:
                title = request.POST.get('title')
                description = request.POST.get('description') or ''
                due_date = request.POST.get('due_date') or None
                status = request.POST.get('status', 'pending')
        except Exception:
            return HttpResponseBadRequest("Invalid payload")

        errors = validate_task_payload({'title': title, 'description': description, 'due_date': due_date, 'status': status}, partial=False)
        if errors:
            return render(request, 'tasks/add.html', {'errors': errors, 'form': {'title': title, 'description': description, 'due_date': due_date, 'status': status}})

        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO tasks (title, description, due_date, status) VALUES (?, ?, ?, ?)",
                        (title, description, due_date, status))
            conn.commit()
        finally:
            conn.close()
        return redirect('task_list_page')

    return HttpResponseNotAllowed(['GET', 'POST'])
