"""
Telegram Notifier - Simple notification client for Python.

A minimal, robust Telegram notification client with:
- Simple text and photo/document sending
- Rate limiting and retry logic
- No external dependencies (except requests)
- Type hints and modern Python support

Basic usage:
    from telegram_notifier import TelegramNotifier

    tn = TelegramNotifier()  # Reads from env vars
    tn.send_text("Hello from Python! 🚀")
    tn.send_photo("chart.png", caption="Training results")
"""

__version__ = "0.1.0"

from .telegramNotifier import TelegramNotifier, TelegramAPIError, RateLimited
from .telegramConfig import TelegramConfig

__all__ = [
    "TelegramNotifier",
    "TelegramAPIError",
    "RateLimited",
    "TelegramConfig",
    "__version__",
]