#!/bin/bash
set -e

# Start cron
echo "Starting cron service..."
service cron start

# Create data and logs directories if they don't exist
mkdir -p /app/data/logs

# Set appropriate permissions
chmod -R 755 /app/data/logs

# Log startup
echo "$(date) - Container starting up" >> /app/data/logs/startup.log

# Check if databases exist, if not, run initial update
if [ ! -f "/app/data/scraped_cards.json" ] || [ ! -f "/app/data/card_prices.json" ]; then
    echo "$(date) - Initial database setup required" >> /app/data/logs/startup.log
    echo "Running initial database update in the background..."
    # Run database update in the background with only critical messages shown
    python /app/update_databases.py all > /app/data/logs/initial_update.log 2>&1 &
    echo "For detailed progress, check logs at /app/data/logs/"
fi

# Print startup message (minimal)
echo "======================================"
echo "🚀 Outland MTG Finder"
echo "======================================"
echo "💻 Visit http://localhost:5000"
echo "📅 Cron updates: Sunday 1:00 AM"
echo "📝 Logs: /app/data/logs/"
echo "======================================" 

# Start Gunicorn with appropriate logging settings
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 4 --timeout 120 \
    --access-logfile /app/data/logs/access.log \
    --error-logfile /app/data/logs/error.log \
    --log-level warning app:app 