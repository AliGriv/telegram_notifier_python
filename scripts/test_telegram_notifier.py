#!/usr/bin/env python3
"""
Simple test script for telegram_notifier.py

Before running:
1. Set environment variables:
   export TELEGRAM_BOT_TOKEN="your_bot_token_here"
   export TELEGRAM_CHAT_ID="your_chat_id_here"

2. Or pass them directly to the script:
   python test_telegram_notifier.py --token YOUR_TOKEN --chat-id YOUR_CHAT_ID --photo /path/to/image.jpg
"""

import argparse
from loguru import logger
import os
import sys
from pathlib import Path
from telegram_notifier.telegramNotifier import TelegramNotifier
import traceback


def main():
    parser = argparse.ArgumentParser(description='Test Telegram Notifier')
    parser.add_argument('--token', help='Bot token (or set TELEGRAM_BOT_TOKEN env var)')
    parser.add_argument('--chat-id', help='Chat ID (or set TELEGRAM_CHAT_ID env var)')
    parser.add_argument(
        '--photo',
        help='Path to test photo (optional, relative to this script)',
        default=str(Path(__file__).parent / "test_image.png")
    )
    args = parser.parse_args()

    try:
        # Create notifier
        logger.info("🤖 Creating Telegram notifier...")
        tn = TelegramNotifier(token=args.token, chat_id=args.chat_id)

        # Test 1: Simple text message
        logger.info("📤 Sending test message...")
        result = tn.send_text("🚀 Hello from telegram_notifier! This is a test message.")
        logger.info(f"✅ Message sent successfully! Message ID: {result['result']['message_id']}")

        # Test 2: Formatted message
        logger.info("📤 Sending formatted message...")
        formatted_msg = """
*Test Results:*
• Status: ✅ Success
• Time: Just now
• Module: telegram\\_notifier\\.py

_This message uses MarkdownV2 formatting_
        """.strip()

        result = tn.send_text(formatted_msg, parse_mode="MarkdownV2")
        logger.info(f"✅ Formatted message sent! Message ID: {result['result']['message_id']}")

        # Test 3: Test document sending
        logger.info("📤 Testing document sending (creating a simple test file)...")

        # Create a simple test file
        test_content = "This is a test file created by telegram_notifier test script."
        with open("test_file.txt", "w") as f:
            f.write(test_content)

        result = tn.send_document("test_file.txt", caption="📄 Test document from telegram_notifier")
        logger.info(f"✅ Document sent! Message ID: {result['result']['message_id']}")

        # Clean up test file
        os.remove("test_file.txt")
        logger.debug("🧹 Cleaned up test file")

        # Test 4: Send Photo with Caption
        photo_path = Path(args.photo)
        if photo_path.exists():
            logger.info(f"📤 Sending test photo from: {photo_path}")
            result = tn.send_photo(
                photo_path,
                caption="📸 Test photo from telegram_notifier!\n\nThis tests the send_photo functionality with a caption."
            )
            logger.info(f"✅ Photo sent successfully! Message ID: {result['result']['message_id']}")
        else:
            logger.warning(f"⚠️  Photo not found at {photo_path}, skipping photo test")
            logger.info("💡 To test photo sending, provide a valid image path with --photo")

        # Test 5: Test URL photo (using a public image)
        logger.info("📤 Testing URL photo sending...")
        try:
            result = tn.send_photo(
                "https://en.wikipedia.org/wiki/File:Abraham_Lincoln_1860.jpg",
                caption="🌐 This image was fetched from a URL by Telegram"
            )
            logger.info(f"✅ URL photo sent! Message ID: {result['result']['message_id']}")
        except Exception as e:
            logger.warning(f"⚠️  URL photo test failed: {e}")

        logger.info("\n🎉 All tests completed! Your telegram_notifier is working correctly.")

    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.info("\nMake sure to:")
        logger.info("1. Set TELEGRAM_BOT_TOKEN environment variable")
        logger.info("2. Set TELEGRAM_CHAT_ID environment variable")
        logger.info("3. Or pass --token and --chat-id arguments")
        sys.exit(1)

    except FileNotFoundError as e:
        logger.error(f"❌ File not found: {e}")
        sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Unexpected error occurred: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()