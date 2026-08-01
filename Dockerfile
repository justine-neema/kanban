FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port for the app
EXPOSE 8000

# Run the application with gunicorn
CMD ["gunicorn", "kanbanproject.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
