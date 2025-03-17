#!/usr/bin/env python3
"""
Database Update Script for Outland MTG Finder

This script is designed to be run by cron to automatically update
the Outland and Scryfall databases. It can be called with arguments
to update specific databases or all databases.

Usage:
  python update_databases.py all     # Update both databases
  python update_databases.py outland  # Update only Outland database
  python update_databases.py scryfall # Update only Scryfall database
"""

import outlandMTG_database
import scryfall_prices
import os
import sys
import time
import datetime
import log_config
import traceback
import utils

# Get a configured logger for this module
logger = log_config.get_logger(__name__, 'database_updates.log')

def update_outland_database():
    """Update the Outland MTG database"""
    start_time = time.time()
    print("Starting Outland database update...")
    logger.info("Starting Outland database update")
    
    try:
        # Basic progress callback for logging
        def progress_callback(status=None, progress=None, message=None, details=None):
            if details:
                logger.debug(f"Outland update: {details}")  # Downgraded to DEBUG level
            if progress is not None and message:
                # Only log at INFO level for significant progress (every 10%)
                if progress % 10 == 0 or progress == 100:
                    logger.info(f"Outland update: {progress}% - {message}")
                    if progress % 20 == 0:  # Print less frequently to console
                        print(f"Outland update: {progress}% - {message}")
                else:
                    logger.debug(f"Outland update: {progress}% - {message}")
                
        # Run the scraper with the callback
        outlandMTG_database.run_scraper(status_callback=progress_callback)
        
        elapsed = time.time() - start_time
        minutes, seconds = divmod(elapsed, 60)
        completion_message = f"Outland database update completed successfully in {int(minutes)}m {int(seconds)}s"
        print(f"✅ {completion_message}")
        logger.info(completion_message)
        return True
    except Exception as e:
        error_message = f"Error updating Outland database: {str(e)}"
        print(f"❌ {error_message}")
        logger.error(error_message)
        logger.debug(traceback.format_exc())  # Detailed stack trace at DEBUG level
        return False

def update_scryfall_database():
    """Update the Scryfall prices database"""
    start_time = time.time()
    print("Starting Scryfall database update...")
    logger.info("Starting Scryfall database update")
    
    try:
        # Basic progress callback for logging
        def progress_callback(status=None, progress=None, message=None, details=None):
            if details:
                logger.debug(f"Scryfall update: {details}")  # Downgraded to DEBUG level
            if progress is not None and message:
                # Only log at INFO level for significant progress (every 10%)
                if progress % 10 == 0 or progress == 100:
                    logger.info(f"Scryfall update: {progress}% - {message}")
                    if progress % 20 == 0:  # Print less frequently to console
                        print(f"Scryfall update: {progress}% - {message}")
                else:
                    logger.debug(f"Scryfall update: {progress}% - {message}")
                
        # Run the scraper with the callback
        scryfall_prices.fetch_cards_over_one_dollar(status_callback=progress_callback)
        
        elapsed = time.time() - start_time
        minutes, seconds = divmod(elapsed, 60)
        completion_message = f"Scryfall database update completed successfully in {int(minutes)}m {int(seconds)}s"
        print(f"✅ {completion_message}")
        logger.info(completion_message)
        return True
    except Exception as e:
        error_message = f"Error updating Scryfall database: {str(e)}"
        print(f"❌ {error_message}")
        logger.error(error_message)
        logger.debug(traceback.format_exc())  # Detailed stack trace at DEBUG level
        return False

def main():
    """Main function to parse arguments and run appropriate updates"""
    start_time = time.time()
    print("Database update script started")
    logger.info("Database update script started")
    
    # Make sure data directory exists
    data_dir = utils.get_data_dir()
    print(f"Using data directory: {data_dir}")
    logger.info(f"Using data directory: {data_dir}")
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        error_message = "No database type specified. Use 'outland', 'scryfall', or 'all'."
        print(f"❌ {error_message}")
        logger.error(error_message)
        return 1
        
    db_type = sys.argv[1].lower()
    
    if db_type not in ['outland', 'scryfall', 'all']:
        error_message = f"Invalid database type: {db_type}. Use 'outland', 'scryfall', or 'all'."
        print(f"❌ {error_message}")
        logger.error(error_message)
        return 1
    
    success = True
    
    if db_type in ['outland', 'all']:
        print("\n=== OUTLAND DATABASE UPDATE ===")
        logger.info("=== OUTLAND DATABASE UPDATE ===")
        outland_success = update_outland_database()
        if not outland_success:
            success = False
        print("================================\n")
        logger.info("================================")
    
    if db_type in ['scryfall', 'all']:
        print("\n=== SCRYFALL DATABASE UPDATE ===")
        logger.info("=== SCRYFALL DATABASE UPDATE ===")
        scryfall_success = update_scryfall_database()
        if not scryfall_success:
            success = False
        print("=================================\n")
        logger.info("=================================")
    
    elapsed = time.time() - start_time
    minutes, seconds = divmod(elapsed, 60)
    
    if success:
        completion_message = f"All requested database updates completed successfully in {int(minutes)}m {int(seconds)}s"
        print(f"✅ {completion_message}")
        logger.info(completion_message)
    else:
        warning_message = f"Some database updates failed. Check the logs for details."
        print(f"⚠️ {warning_message}")
        logger.warning(warning_message)
        
    return 0 if success else 1

if __name__ == "__main__":
    # Set up root logger to catch any unconfigured loggers
    log_config.configure_root_logger()
    sys.exit(main()) 