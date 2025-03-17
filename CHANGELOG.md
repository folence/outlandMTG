# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2025-03-XX

### Added
- Comprehensive test suite with pytest
- Centralized logging system with rotation
- Health check endpoint
- Log viewing utility
- Docker support with proper volume mounting
- Automated database updates with scheduling
- Rate limiting for API endpoints
- Better error handling and user feedback
- Database status endpoint
- Coverage reporting for tests

### Changed
- Replaced print statements with proper logging
- Improved error handling across all modules
- Enhanced database update process with progress tracking
- Better organization of code structure
- Updated documentation with detailed setup and usage instructions
- Improved Docker configuration for better data persistence
- Enhanced logging configuration with separate log files per module

### Fixed
- Database update process reliability
- Error handling in API endpoints
- Log file rotation issues
- Docker volume mounting problems
- Rate limiting implementation
- Database status reporting

### Removed
- Deprecated print statements
- Redundant error handling code
- Outdated documentation

### Security
- Added rate limiting to prevent abuse
- Improved error message handling to prevent information leakage
- Better handling of sensitive data in logs

## [1.0.0] - Initial Release
- Basic EDHRec integration
- Outland.no card scraping
- Scryfall price comparison
- Simple web interface 