# Frequently Asked Questions (FAQ)

This document addresses common questions and issues that users may encounter while using the Telegram Channel Saver.

## General Questions

### What is Telegram Channel Saver?

Telegram Channel Saver is a Python tool designed to help you save and analyze content from Telegram channels. It allows you to download messages, media, and track user activity in channels you have access to.

### Is this tool official or affiliated with Telegram?

No, this is an independent tool and is not officially affiliated with or endorsed by Telegram. It uses the official Telegram API through the Telethon library.

### Is using this tool against Telegram's Terms of Service?

This tool is designed for personal use and uses official Telegram API methods. However, please use it responsibly and be aware of Telegram's [Terms of Service](https://telegram.org/tos) and [API Terms of Service](https://core.telegram.org/api/terms). Misuse of the tool (such as excessive scraping or spamming) may violate these terms.

## Setup and Installation

### Why am I getting an error about missing dependencies?

Make sure you've installed all required dependencies by running:
```bash
pip install -r requirements.txt
```

### Where do I get the API_ID and API_HASH?

1. Visit [my.telegram.org/apps](https://my.telegram.org/apps)
2. Log in with your Telegram account
3. Create a new application if you don't have one
4. Your API_ID and API_HASH will be displayed on the page

### How do I store my API credentials securely?

Create a `.env` file in the project root with the following content:
```
API_ID=your_api_id
API_HASH=your_api_hash
```
The application will automatically load these values when started.

## Usage Questions

### How many messages can I download at once?

By default, the tool can download any number of messages, but there are rate limits to consider:
- Telegram API has rate limits that prevent too many requests in a short period
- The tool has built-in delays to respect these limits
- For very large channels (10,000+ messages), it's recommended to download in batches

### Why am I getting "FloodWaitError"?

This error occurs when you've made too many requests to the Telegram API in a short period. The error will include a wait time (in seconds). The tool will automatically wait for the specified time before continuing. To reduce the frequency of these errors:
- Increase the delay between requests in `src/config.py`
- Download fewer messages at once
- Run the tool less frequently

### Can I download messages from a private channel?

Yes, but you must be a member of the channel. The tool can only access channels that your Telegram account has access to.

### How do I search for specific messages?

From the main menu, select the option to search messages. You can search by:
- Text content
- Date range
- Message ID
- User messages

### Where are downloaded files stored?

By default:
- Database files are stored in `temp/channel_saver/`
- Media files are stored in `temp/videos/` and other appropriate directories
- You can change these paths in `src/config.py`

## Troubleshooting

### The application crashes when downloading media

This could be due to several reasons:
1. Insufficient disk space
2. Large media files
3. Network interruptions

Solutions:
- Free up disk space
- Set media size limits in `src/config.py`
- Check your internet connection stability
- Try downloading media in smaller batches

### I can't authenticate with my Telegram account

Check the following:
1. Verify your API_ID and API_HASH are correct
2. Make sure you're entering the correct phone number (with country code)
3. Check if your account has any restrictions
4. If using 2FA, ensure you're entering the correct password

### The tool is running very slowly

This may be due to:
1. Rate limiting by Telegram API
2. Large number of messages being processed
3. Slow internet connection
4. Computer resource limitations

Optimization tips:
- Increase the delay parameters in `src/config.py` to reduce rate limit errors
- Download in smaller batches
- Close other applications using your network
- Run during off-peak hours

### How do I reset my session?

If you need to log in with a different account or your session is corrupted:
1. Delete the session file(s) in `temp/channel_saver/`
2. Restart the application
3. You'll be prompted to log in again

### My question isn't answered here

If you have additional questions or issues:
1. Check the documentation in the `docs/` directory
2. Look for similar issues in the project repository
3. Consider opening a new issue in the repository with details about your problem 