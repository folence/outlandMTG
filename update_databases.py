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
                else:
                    logger.debug(f"Outland update: {progress}% - {message}")
                
        # Run the scraper with the callback
        outlandMTG_database.run_scraper(status_callback=progress_callback)
        
        elapsed = time.time() - start_time
        logger.info(f"Outland database update completed successfully in {elapsed:.2f} seconds")
        return True
    except Exception as e:
        logger.error(f"Error updating Outland database: {str(e)}")
        logger.debug(traceback.format_exc())  # Detailed stack trace at DEBUG level
        return False

def update_scryfall_database():
    """Update the Scryfall prices database"""
    start_time = time.time()
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
                else:
                    logger.debug(f"Scryfall update: {progress}% - {message}")
                
        # Run the scraper with the callback
        scryfall_prices.fetch_cards_over_one_dollar(status_callback=progress_callback)
        
        elapsed = time.time() - start_time
        logger.info(f"Scryfall database update completed successfully in {elapsed:.2f} seconds")
        return True
    except Exception as e:
        logger.error(f"Error updating Scryfall database: {str(e)}")
        logger.debug(traceback.format_exc())  # Detailed stack trace at DEBUG level
        return False

def main():
    """Main function to parse arguments and run appropriate updates"""
    start_time = time.time()
    logger.info("Database update script started")
    
    # Make sure data directory exists
    data_dir = utils.get_data_dir()
    logger.info(f"Using data directory: {data_dir}")
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        logger.error("No database type specified. Use 'outland', 'scryfall', or 'all'.")
        return 1
        
    db_type = sys.argv[1].lower()
    
    if db_type not in ['outland', 'scryfall', 'all']:
        logger.error(f"Invalid database type: {db_type}. Use 'outland', 'scryfall', or 'all'.")
        return 1
    
    success = True
    
    if db_type in ['outland', 'all']:
        logger.info("=== OUTLAND DATABASE UPDATE ===")
        outland_success = update_outland_database()
        if not outland_success:
            success = False
        logger.info("================================")
    
    if db_type in ['scryfall', 'all']:
        logger.info("=== SCRYFALL DATABASE UPDATE ===")
        scryfall_success = update_scryfall_database()
        if not scryfall_success:
            success = False
        logger.info("=================================")
    
    elapsed = time.time() - start_time
    
    if success:
        logger.info(f"All requested database updates completed successfully in {elapsed:.2f} seconds")
    else:
        logger.warning(f"Some database updates failed. Check the logs for details.")
        
    return 0 if success else 1

if __name__ == "__main__":
    # Set up root logger to catch any unconfigured loggers
    log_config.configure_root_logger()
    sys.exit(main()) 