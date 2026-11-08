# Telegram Channel Saver Setup Guide

This document provides detailed instructions for setting up your development environment to work on the Telegram Channel Saver project.

## Prerequisites

Before you begin, ensure that you have the following installed on your system:

- Python 3.8 or higher
- pip (Python package manager)
- Git

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/telegram-channel-saver.git
cd telegram-channel-saver
```

### 2. Create a Virtual Environment

It's recommended to use a virtual environment to keep dependencies isolated:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

Install the required packages:

```bash
pip install -r requirements.txt

# For development, install additional packages
pip install -r requirements-dev.txt  # if available
```

### 4. Telegram API Credentials

To use the Telegram API, you need to obtain API credentials:

1. Visit [https://my.telegram.org/auth](https://my.telegram.org/auth) and log in with your Telegram account
2. Go to "API Development Tools"
3. Create a new application (if you haven't already)
4. Note your **API ID** and **API Hash**

### 5. Configuration

1. Create a copy of the example configuration file:

```bash
cp config.example.ini config.ini
```

2. Edit `config.ini` with your API credentials and other settings:

```ini
[Telegram]
api_id = YOUR_API_ID
api_hash = YOUR_API_HASH
phone = YOUR_PHONE_NUMBER  # with country code, e.g., +12345678901

[Storage]
download_folder = downloads
```

## Running the Application

### Running in Development Mode

```bash
python main.py
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific tests
pytest tests/test_specific_feature.py

# Run with coverage report
pytest --cov=telegram_channel_saver
```

## Development Tools

### Code Linting

We use flake8 for linting:

```bash
# Check code style
flake8 telegram_channel_saver

# Auto-format code (if using Black)
black telegram_channel_saver
```

### Type Checking

We use mypy for type checking:

```bash
mypy telegram_channel_saver
```

## Project Structure

Here's an overview of the key directories and files in the project:

```
telegram-channel-saver/
├── telegram_channel_saver/  # Main package directory
│   ├── __init__.py
│   ├── main.py             # Entry point
│   ├── client.py           # Telegram client implementation
│   ├── downloader.py       # Media downloading functionality
│   └── utils/              # Utility functions
├── tests/                  # Test files
├── docs/                   # Documentation
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
└── config.example.ini      # Example configuration file
```

## Troubleshooting

### Common Issues

#### Authentication Problems

If you encounter authentication issues:
- Verify your API credentials
- Check your phone number format (include country code)
- Ensure you have internet connectivity

#### Import Errors

If you see import errors:
- Make sure you have activated the virtual environment
- Verify all dependencies are installed correctly

#### Rate Limiting

If you encounter `FloodWaitError`:
- Reduce the frequency of requests
- Add delays between operations
- Implement exponential backoff

### Getting Help

If you encounter any issues that aren't covered here:
1. Check the [FAQ document](faq.md)
2. Search for similar issues in the GitHub repository
3. Open a new issue with a detailed description of the problem

## Additional Resources

- [Telethon Documentation](https://docs.telethon.dev/en/stable/) - The Python Telegram client library used in this project
- [Telegram API Documentation](https://core.telegram.org/api) - Official Telegram API documentation 