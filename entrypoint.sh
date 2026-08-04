#!/bin/bash

echo "Starting application..."

# Run migrations after build
python manage.py migrate

# Start Gunicorn
gunicorn --workers=4 --bind=0.0.0.0:8000 kanbanproject.wsgi:application