# Telegram Notifier

A simple Python library for sending notifications through Telegram bots.

## ✨ Features

- 📤 Send text messages with formatting (Markdown/HTML)
- 📷 Send photos and documents with captions
- 🔄 Automatic retry logic with exponential backoff
- ⚡ Rate limit handling
- 🛡️ Robust error handling
- 🔧 Simple configuration via environment variables
- 📦 No external dependencies (except `requests`)

## 🚀 Quick Start

### 1. Get Your Telegram Credentials

You'll need two things from Telegram:

**Bot Token:**
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy your bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

**Chat ID:**
1. Start a chat with your bot (send any message)
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Look for `"chat":{"id":12345678}` in the response

### 2. Set Environment Variables

```bash
export TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
export TELEGRAM_CHAT_ID="12345678"
```

### 3. Install the Package

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package
pip install -e .
```

### 4. Start Using It!

```python
from telegram_notifier import TelegramNotifier

# Create notifier (reads from environment variables)
tn = TelegramNotifier()

# Send simple messages
tn.send_text("🚀 Server started successfully!")
tn.send_text("Training complete! Accuracy: 94.2%")

# Send with formatting
tn.send_text("*Bold text* and _italic text_", parse_mode="MarkdownV2")

# Send photos/documents
tn.send_photo("training_plot.png", caption="📊 Training results")
tn.send_document("model.pkl", caption="💾 Trained model")
```

## 📋 Testing

Test your setup with the included test script:

```bash
python scripts/test_telegram_notifier.py --help
```

**Options:**
- `--token TOKEN`: Bot token (or use `TELEGRAM_BOT_TOKEN` env var)
- `--chat-id CHAT_ID`: Chat ID (or use `TELEGRAM_CHAT_ID` env var)
- `--photo PHOTO`: Path to test photo (optional)

**Example:**
```bash
# Using environment variables
python scripts/test_telegram_notifier.py

# Or with command line arguments
python scripts/test_telegram_notifier.py --token "YOUR_TOKEN" --chat-id "YOUR_CHAT_ID" --photo "test.jpg"
```

## 💡 Common Use Cases

**Server Monitoring:**
```python
tn.send_text("⚠️ High CPU usage detected: 89%")
```

**ML Training Updates:**
```python
tn.send_text(f"📈 Epoch {epoch}: Loss={loss:.4f}, Acc={acc:.2%}")
tn.send_photo("loss_curve.png", caption="Training progress")
```

**Deployment Notifications:**
```python
tn.send_text("✅ Deployment successful!")
tn.send_document("deployment.log", caption="📋 Deployment logs")
```

## 🔧 Advanced Configuration

You can also configure the notifier programmatically:

```python
tn = TelegramNotifier(
    token="your_token",
    chat_id="your_chat_id",
    timeout_seconds=30,
    max_retries=5
)
```

## 📖 API Reference

### `TelegramNotifier`

**Methods:**
- `send_text(text, parse_mode=None, ...)` - Send text message
- `send_photo(photo, caption=None, ...)` - Send photo
- `send_document(document, caption=None, ...)` - Send document/file

**Parameters:**
- `photo/document`: File path, URL, bytes, or file-like object
- `caption`: Optional caption (max 1024 characters)
- `parse_mode`: "MarkdownV2" or "HTML" for formatting
- `disable_notification`: Send silently
- `reply_to_message_id`: Reply to specific message

## 📄 Requirements

- Python 3.9+
- `requests` library (automatically installed)

## 🤝 Contributing

This is an experimental project. Feel free to submit issues or suggestions!

## 📝 License

Open source - feel free to use and modify as needed.