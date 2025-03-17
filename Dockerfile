# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    procps \
    cron \
    shadow \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Make entry point script executable
RUN chmod +x /app/docker-entrypoint.sh

# Create data directory structure with proper permissions
RUN mkdir -p /app/data/logs && \
    chmod -R 755 /app/data

# Setup cron job for database updates
RUN echo "0 1 * * 0 /usr/local/bin/python /app/update_databases.py all >> /app/data/logs/cron_update.log 2>&1" > /etc/cron.d/database-update && \
    chmod 0644 /etc/cron.d/database-update && \
    crontab /etc/cron.d/database-update

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PUID=99
ENV PGID=100

# Expose port
EXPOSE 5000

# Use entry point script
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command (can be overridden)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--access-logfile", "/app/data/logs/access.log", "--error-logfile", "/app/data/logs/error.log", "app:app"] 