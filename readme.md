# Outland MTG Card Finder

A web application to help Magic: The Gathering players find budget cards from Outland.no and identify underpriced cards comparing Outland.no prices with Scryfall's international market prices.

## Features

- **EDHRec Integration**: Search for commander recommendations from EDHRec and find those cards at Outland below your specified price
- **Underpriced Card Search**: Find cards that are significantly cheaper at Outland compared to international market prices
- **Automated Database Updates**: Databases automatically update weekly (every Sunday at 1:00 AM)
- **Docker Support**: Easy deployment with Docker
- **Improved Logging System**: Comprehensive logging with rotation and minimal terminal output
- **Test Suite**: Comprehensive test coverage for core functionality
- **Health Monitoring**: Built-in health check endpoint and database status monitoring
- **Rate Limiting**: Protection against API abuse
- **Error Handling**: Comprehensive error handling and user feedback
- **Cross-Platform Support**: Works on both Windows and Unix-based systems
- **Utility Module**: Centralized utilities for path handling and common operations

## Prerequisites

- Python 3.9 or higher
- Docker (optional, for containerized deployment)
- Git

## Quick Start

### Using Docker (Recommended)

1. Clone the repository:

   ```bash
   git clone https://github.com/folence/outlandMTG.git
   cd outlandMTG
   ```

2. Build and run with Docker:

   ```bash
   docker build -t outland-mtg .
   docker run -p 5000:5000 -v $(pwd)/data:/app/data outland-mtg
   ```

3. Access the application at: <http://localhost:5000>

### Manual Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/folence/outlandMTG.git
   cd outlandMTG
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:

   ```bash
   python app.py
   ```

5. Access the application at: <http://localhost:5000>

## Development Setup

1. Install development dependencies:

   ```bash
   pip install -r test_requirements.txt
   ```

2. Run tests:

   ```bash
   # Run all tests
   pytest

   # Run tests with coverage report
   pytest --cov=.

   # Run only unit tests
   pytest -m unit

   # Run only integration tests
   pytest -m integration

   # Skip slow tests
   pytest -m "not slow"
   ```

## Project Structure

```
outlandMTG/
├── app.py                 # Main application entry point
├── EDH_search.py          # EDHRec integration
├── underpriced_cards.py   # Price comparison logic
├── update_databases.py    # Database update script
├── log_config.py          # Logging configuration
├── view_logs.py           # Log viewing utility
├── utils.py               # Utility functions and path handling
├── tests/                 # Test suite
├── data/                  # Data directory (created on first run)
│   └── logs/              # Application logs
├── requirements.txt       # Production dependencies
├── test_requirements.txt  # Development dependencies
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose configuration
└── README.md              # This file
```

## Cross-Platform Support

The application is designed to work on both Windows and Unix-based systems:

- **Path Handling**: Uses platform-independent path handling via Python's `pathlib`
- **Log Viewing**: Adapts to the platform when viewing logs (PowerShell on Windows, cat/tail on Unix)
- **Data Storage**: Automatically uses the appropriate data directory for your platform
- **Environment Detection**: Automatically detects if running in Docker, Windows, or Unix-like systems

## Utility Module

The `utils.py` module provides centralized utilities for the entire application:

- **Path Management**:
  - Platform-independent path handling for data, logs, and configuration
  - Automatic directory creation when needed
  - Functions like `get_data_dir()`, `get_log_dir()`, and `get_log_file()`

- **File Operations**:
  - Loading and saving JSON files with error handling
  - Pickle file operations for serializing Python objects
  - File size and age calculation

- **Data Processing**:
  - Card name normalization and cleaning
  - Price extraction and currency conversion
  - Timestamp formatting

- **HTTP and Networking**:
  - Safe request handling with exponential backoff
  - Rate limiting decorators
  - Configurable retry logic

- **Date and Time**:
  - Next scheduled update calculation
  - Human-readable timestamp formatting
  - File age calculation

## Data Storage

Database files are stored in the data directory:

- Windows: `.\data\` (relative to the application directory)
- Linux/Docker: `/app/data/` (when running in Docker)

The app includes:

- `scraped_cards.json`: Outland.no inventory data
- `card_prices.json`: Scryfall price data
- `LegendaryCreatures.json`: list of legendary creatures

When using Docker, you can mount a volume to this directory to persist the data between container restarts.

## Automated Updates

The application is configured to automatically update both databases every Sunday at 1:00 AM. The first time you run the application, it will automatically start an initial database update in the background.

You can also manually trigger updates from the command line:

```bash
# Update all databases
python update_databases.py all

# Update only Outland database
python update_databases.py outland

# Update only Scryfall database
python update_databases.py scryfall
```

## Logs

Logs are stored in the logs directory:

- Windows: `.\data\logs\` (relative to the application directory)
- Linux/Docker: `/app/data/logs/` (when running in Docker)

Log files include:

- `app.log`: Main application logs
- `outlandMTG_database.log`: Outland database scraper logs
- `scryfall_prices.log`: Scryfall price fetcher logs
- `database_updates.log`: Database update process logs
- `access.log`: Gunicorn access logs
- `error.log`: Gunicorn error logs
- `startup.log`: Application startup information

### Viewing Logs

The application comes with a log viewing utility that works on both Windows and Unix-based systems:

```bash
# List all available log files
python view_logs.py

# View the last 100 lines of a specific log file
python view_logs.py app.log

# View the last 50 lines of the error log
python view_logs.py error.log --lines 50

# View the entire log file
python view_logs.py database_updates.log --lines 0
```

### Logging Features

The application uses a centralized logging configuration with the following features:

- **Log Rotation**: Logs are automatically rotated when they reach 10MB, with 5 backup files kept
- **Minimal Console Output**: Only warnings and errors are shown in the console by default
- **Detailed File Logs**: Complete logs are stored in files for debugging
- **Module-specific Logs**: Each component writes to its own log file for easier troubleshooting

You can adjust logging levels in `log_config.py` if needed:

- `DEFAULT_LOG_LEVEL`: Controls logging detail in files (default: INFO)
- `DEFAULT_CONSOLE_LEVEL`: Controls logging detail in console (default: WARNING)

## API Endpoints

- `GET /`: Home page
- `GET /health`: Health check endpoint
- `GET /database_status`: Database status information
- `GET /search_commanders`: Search for commanders
- `POST /search_commander`: Search for cards for a specific commander

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is available under the MIT License. See the [LICENSE](LICENSE) file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes and version history.

## Unraid Setup

This application can be run as a Docker container in Unraid. Here's how to set it up:

### Using Docker Compose Template

1. Install the Docker Compose Manager plugin in Unraid
2. Add this repository as a template
3. Deploy using the template

### Manual Setup

1. **Add a new Docker container with these settings**:
   - **Repository**: `ghcr.io/folence/outlandmtg:latest` or specify your own built image
   - **Network Type**: Bridge
   - **Port**: 5000:5000
   - **Appdata Path**: `/mnt/user/appdata/outlandmtg/`

2. **Configure environment variables**:
   - `TZ=Europe/Oslo` (adjust to your timezone)
   - `PUID=99` (your Unraid user ID)
   - `PGID=100` (your Unraid group ID)
   - `LOG_LEVEL=INFO`
   - `CONSOLE_LOG_LEVEL=WARNING`

3. **Add volume mappings**:
   - `/mnt/user/appdata/outlandmtg/data:/app/data`

### Accessing the Application

After starting the container, the application will be available at:
<http://your-unraid-ip:5000>

### Notes for Unraid Users

- The container will automatically update databases on first run or if they're more than 14 days old
- Logs are stored in `/mnt/user/appdata/outlandmtg/data/logs/`
- Weekly database updates happen every Sunday at 1:00 AM
- For troubleshooting, check the container logs or the application logs

### Permissions

If you encounter permission issues, make sure the `PUID` and `PGID` values match your user. You can find these values by running:

```bash
id username
```

Replace `username` with your Unraid username.
