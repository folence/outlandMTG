#!/usr/bin/env python3
"""
Outland MTG Log Viewer

A simple utility to view logs from the Outland MTG application.
"""

import os
import sys
import argparse
import subprocess
import utils

def list_log_files():
    """List all log files in the log directory"""
    log_dir = utils.get_log_dir()
    log_files = []
    
    try:
        for file in os.listdir(log_dir):
            if file.endswith('.log'):
                log_files.append(file)
    except Exception as e:
        print(f"Error listing log files: {str(e)}")
    
    return sorted(log_files)

def print_log_list():
    """Print a list of available log files"""
    log_files = list_log_files()
    
    if not log_files:
        print("No log files found in the log directory.")
        return
    
    print(f"Available log files in {utils.get_log_dir()}:")
    print()
    
    for file in log_files:
        log_path = utils.get_log_dir() / file
        size = utils.get_file_size(log_path)
        modified = os.path.getmtime(log_path)
        
        # Convert size to human-readable format
        if size < 1024:
            size_str = f"{size} bytes"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size / (1024 * 1024):.1f} MB"
            
        # Format modified time
        time_str = utils.format_timestamp(modified)
        
        print(f"{file:<25} {size_str:<10} Last modified: {time_str}")

def view_log_file(log_file, lines=100):
    """View the specified log file"""
    log_path = utils.get_log_file(log_file)
    
    if not os.path.exists(log_path):
        print(f"Error: Log file '{log_file}' not found.")
        return False
    
    try:
        # Display the log file contents
        if utils.IS_WINDOWS:
            # Windows approach using PowerShell
            if lines == 0:
                # View entire file
                subprocess.run(['type', str(log_path)], check=True, shell=True)
            else:
                # Get the last N lines
                subprocess.run(['powershell', '-Command', f"Get-Content -Tail {lines} {log_path}"], check=True, shell=True)
        else:
            # Unix approach
            if lines == 0:
                # View entire file
                subprocess.run(['cat', str(log_path)], check=True)
            else:
                # Get the last N lines
                subprocess.run(['tail', f'-n{lines}', str(log_path)], check=True)
                
        return True
    except Exception as e:
        print(f"Error viewing log file: {str(e)}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='View Outland MTG logs')
    parser.add_argument('log_file', nargs='?', help='Log file to view', default=None)
    parser.add_argument('--lines', '-n', type=int, default=100, help='Number of lines to show (default: 100, 0 for all)')
    parser.add_argument('--list', '-l', action='store_true', help='List available log files')
    
    args = parser.parse_args()
    
    if args.list or not args.log_file:
        print_log_list()
        return 0
    
    return 0 if view_log_file(args.log_file, args.lines) else 1

if __name__ == "__main__":
    sys.exit(main()) 