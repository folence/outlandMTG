#!/bin/bash
set -e

# Apply user/group permissions if specified
if [ ! -z ${PUID} ] && [ ! -z ${PGID} ]; then
    echo "Setting permissions based on PUID: ${PUID} and PGID: ${PGID}"
    
    # Create user and group if they don't exist
    groupmod -o -g "$PGID" www-data || true
    usermod -o -u "$PUID" www-data || true
    
    # Update permissions of app directories
    chown -R www-data:www-data /app/data /app/data/logs || true
fi

# Start cron
echo "Starting cron service..."
service cron start || true

# Create data and logs directories if they don't exist
mkdir -p /app/data/logs

# Set appropriate permissions
chmod -R 755 /app/data/logs

# Log startup
echo "$(date) - Container starting up" >> /app/data/logs/startup.log
echo "🚀 Starting Outland MTG Finder..."

# Check if databases exist, if not, run initial update
if [ ! -f "/app/data/scraped_cards.json" ] || [ ! -f "/app/data/card_prices.json" ]; then
    echo "📊 Initial database setup required" | tee -a /app/data/logs/startup.log
    echo "⏳ Running initial database update in the background..."
    # Run database update in the background with only critical messages shown
    python /app/update_databases.py all > /app/data/logs/initial_update.log 2>&1 &
    echo "📓 For detailed progress, check logs at /app/data/logs/"
else
    # Check if databases are too old (more than 14 days)
    OUTLAND_AGE=999
    SCRYFALL_AGE=999
    
    if [ -f "/app/data/scraped_cards.json" ]; then
        OUTLAND_AGE=$((($(date +%s) - $(date -r /app/data/scraped_cards.json +%s)) / 86400))
    fi
    
    if [ -f "/app/data/card_prices.json" ]; then
        SCRYFALL_AGE=$((($(date +%s) - $(date -r /app/data/card_prices.json +%s)) / 86400))
    fi
    
    if [ $OUTLAND_AGE -gt 14 ] || [ $SCRYFALL_AGE -gt 14 ]; then
        echo "⚠️ Databases are older than 14 days, updating in background..." | tee -a /app/data/logs/startup.log
        python /app/update_databases.py all > /app/data/logs/background_update.log 2>&1 &
    else
        echo "✅ Using existing databases (Outland: ${OUTLAND_AGE} days old, Scryfall: ${SCRYFALL_AGE} days old)" | tee -a /app/data/logs/startup.log
    fi
fi

# Print startup message (minimal)
echo "======================================"
echo "🚀 Outland MTG Finder"
echo "======================================"
echo "💻 Visit http://localhost:5000"
echo "📅 Cron updates: Sunday 1:00 AM"
echo "📝 Logs: /app/data/logs/"
echo "======================================"

# Execute the CMD from the Dockerfile (usually gunicorn)
exec "$@" 