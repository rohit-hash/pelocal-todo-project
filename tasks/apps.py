from django.apps import AppConfig
import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

class TasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tasks'

    def ready(self):
        # Create table if not exists using raw SQL
        from django.conf import settings
        db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                due_date TEXT,      -- ISO 8601 date string (YYYY-MM-DD)
                status TEXT NOT NULL CHECK (status IN ('pending','in_progress','done')) DEFAULT 'pending'
            );
            """)
            conn.commit()
            logger.info("Ensured tasks table exists.")
        except Exception as e:
            logger.exception("Error ensuring tasks table: %s", e)
        finally:
            conn.close()
