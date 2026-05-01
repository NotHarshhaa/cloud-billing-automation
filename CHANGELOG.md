# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-05-01

### Security Fixes
- Fixed encryption key type mismatch in JWT token generation
- Added SSL verification for all webhook communications (WebhookChannel and SlackChannel)
- Implemented URL validation for webhook endpoints to prevent SSRF attacks
- Added Slack-specific domain validation for webhook URLs
- Fixed mutable default argument security issue in SecurityPolicy

### Bug Fixes
- Fixed Windows compatibility issue with file permissions in credential storage
- Fixed CLI import path error in doctor command
- Replaced bare except clauses with specific exception types
- Added missing schedule dependency to requirements.txt

### Improvements
- Updated development status from Alpha to Beta
- Enhanced error handling with specific exception types
- Improved input validation for webhook URLs
- Added comprehensive URL validation before HTTP requests

### Changed
- Version bump to 0.6.0 for security improvements

## [0.5.4] - 2026-02-01

### Features
- Machine Learning forecasting with advanced models
- Cost optimization engine with AI-powered recommendations
- Automated report scheduler with flexible scheduling

## [0.2.0] - 2026-02-01

### Improvements
- Added comprehensive logging configuration
- Enhanced error handling and validation
- Fixed configuration bugs and improved CLI structure
- Improved package structure and dependency management

## [0.1.0] - 2026-02-01

### Initial Release
- Multi-cloud billing data collection (AWS, Azure, GCP)
- Cost analysis and breakdown by multiple dimensions
- Budget monitoring and alerting system
- Anomaly detection with statistical methods
- Rich CLI interface with professional output
- Comprehensive credential management
- Multi-channel notifications (Email, Slack, Webhook)
