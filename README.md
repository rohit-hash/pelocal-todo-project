# pelocal-todo-project
Develop a web application using Python and Django/Flask/FastAPI for managing a To-Do list. The application should provide RESTful APIs for CRUD operations on tasks, utilize templates for rendering user interfaces, and store task data in a database.
## Requirements
- Python 3.10+
- Django 5+
- pytest, pytest-django

## Setup
pip install django pytest pytest-django


python manage.py migrate  # creates default Django tables

python manage.py runserver

## Usage
Web UI:

List: http://localhost:8000/

Add: http://localhost:8000/add/

APIs:

Create: POST /api/tasks/

List: GET /api/tasks/

Get one: GET /api/tasks/{id}/

Update: PUT /api/tasks/{id}/

Delete: DELETE /api/tasks/{id}/

## PostMan Collection

## https://api.postman.com/collections/11626653-86e96c02-6b21-4431-bb48-2a5a30fe3794?access_key=PMAT-01KAE7P5NZJMHRWA97V4EAZCNS
