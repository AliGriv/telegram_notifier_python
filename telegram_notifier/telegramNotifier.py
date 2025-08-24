"""
telegram_notifier.py

Environment variables (recommended):
  TELEGRAM_BOT_TOKEN  -> your BotFather token (e.g., 123456:ABC-DEF...)
  TELEGRAM_CHAT_ID    -> default destination chat id (user or group)

Basic usage:
  from telegram_notifier import TelegramNotifier
  tn = TelegramNotifier()  # reads env vars by default
  tn.send_text("Training finished ✅")
  tn.send_photo("/path/to/image.png", caption="Loss curve")

Advanced:
  tn = TelegramNotifier(chat_id=another_chat_id)          # override default chat
  tn.send_text("**bold**", parse_mode="MarkdownV2")       # formatting
  tn.send_photo(image_bytes, caption="inline bytes!")     # bytes or file-like
  tn.send_photo("https://example.com/image.jpg")          # URL (Telegram fetches)

No external dependencies beyond 'requests'.
"""

from __future__ import annotations

import io
from loguru import logger
import os
import pathlib
import time
import typing as t
import requests
from telegram_notifier.telegramConfig import TelegramConfig



class TelegramNotifier:
    """
    Minimal, robust Telegram notification client.

    - Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from env by default.
    - Provides send_text() and send_photo() for notifications.
    - Handles rate limits (429) using Telegram's 'retry_after' hint.
    - Retries transient errors with exponential backoff.
    """

    def __init__(
        self,
        token: str | None = None,
        chat_id: str | int | None = None,
        *,
        base_url: str = "https://api.telegram.org",
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
        session_headers: dict[str, str] | None = None,
        session: requests.Session | None = None,
    ) -> None:
        token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

        if not token:
            raise ValueError("Missing bot token. Set TELEGRAM_BOT_TOKEN or pass token=...")
        if chat_id is None:
            raise ValueError("Missing default chat id. Set TELEGRAM_CHAT_ID or pass chat_id=...")

        # Convert string chat_id to int if it's numeric
        if isinstance(chat_id, str) and chat_id.lstrip('-').isdigit():
            chat_id = int(chat_id)

        self._cfg = TelegramConfig(
            token=token,
            default_chat_id=chat_id,
            base_url=base_url.rstrip("/"),
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
            session_headers=session_headers or {},
        )
        self._session = session or requests.Session()
        if self._cfg.session_headers:
            self._session.headers.update(self._cfg.session_headers)

    # ----------------------------- Public API -----------------------------

    def send_text(
        self,
        text: str,
        *,
        chat_id: str | int | None = None,
        parse_mode: t.Literal["MarkdownV2", "HTML"] | None = None,
        disable_web_page_preview: bool = True,
        disable_notification: bool = False,
        protect_content: bool = False,
        reply_to_message_id: int | None = None,
    ) -> dict[str, t.Any]:
        """
        Send a plain text message (optionally formatted).

        Args:
            text: Message text to send
            chat_id: Override default chat ID
            parse_mode: Text formatting mode
            disable_web_page_preview: Disable link previews
            disable_notification: Send silently
            protect_content: Protect content from forwarding/saving
            reply_to_message_id: Reply to specific message

        Returns:
            Telegram API response dict

        Raises:
            TelegramAPIError: On API errors
            ValueError: On invalid input
        """
        if not text.strip():
            raise ValueError("Message text cannot be empty")

        # Validate text length (Telegram limit is 4096 characters)
        if len(text) > 4096:
            logger.warning(f"Message length {len(text)} exceeds Telegram limit of 4096 characters")
            text = text[:4093] + "..."

        payload = {
            "chat_id": chat_id or self._cfg.default_chat_id,
            "text": text,
            "disable_web_page_preview": disable_web_page_preview,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        return self._post_json("sendMessage", json=payload)

    def send_photo(
        self,
        photo: str | bytes | pathlib.Path | io.BufferedIOBase,
        *,
        chat_id: str | int | None = None,
        caption: str | None = None,
        parse_mode: t.Literal["MarkdownV2", "HTML"] | None = None,
        disable_notification: bool = False,
        protect_content: bool = False,
        filename: str | None = None,
        reply_to_message_id: int | None = None,
    ) -> dict[str, t.Any]:
        """
        Send a photo.

        Args:
            photo: Photo to send. May be:
                - Path to a local file (str or Path)
                - A URL string (starts with http/https) -> Telegram fetches it
                - Raw bytes
                - A file-like object (opened in binary mode)
            chat_id: Override default chat ID
            caption: Photo caption (max 1024 characters)
            parse_mode: Caption formatting mode
            disable_notification: Send silently
            protect_content: Protect content from forwarding/saving
            filename: Filename for bytes/file-like objects
            reply_to_message_id: Reply to specific message

        Returns:
            Telegram API response dict

        Raises:
            TelegramAPIError: On API errors
            FileNotFoundError: If local file doesn't exist
            ValueError: On invalid input
        """
        # Validate caption length
        if caption and len(caption) > 1024:
            logger.warning(f"Caption length {len(caption)} exceeds Telegram limit of 1024 characters")
            caption = caption[:1021] + "..."

        data = {
            "chat_id": chat_id or self._cfg.default_chat_id,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
        }
        if caption:
            data["caption"] = caption
        if parse_mode:
            data["parse_mode"] = parse_mode
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id

        # Case 1: URL string -> send as JSON (Telegram fetches remotely)
        if isinstance(photo, str) and photo.lower().startswith(("http://", "https://")):
            data["photo"] = photo
            return self._post_json("sendPhoto", data=data)

        # Case 2: local path or other formats -> file upload
        files = None
        close_file = None
        try:
            if isinstance(photo, (str, pathlib.Path)):
                # treat as local path
                path = pathlib.Path(photo)
                if not path.exists():
                    raise FileNotFoundError(f"Photo file not found: {path}")
                if not path.is_file():
                    raise ValueError(f"Path is not a file: {path}")

                f = path.open("rb")
                close_file = f
                files = {"photo": (path.name, f)}
            elif isinstance(photo, bytes):
                if len(photo) == 0:
                    raise ValueError("Photo bytes cannot be empty")
                files = {"photo": (filename or "photo.jpg", io.BytesIO(photo))}
            elif hasattr(photo, "read"):
                # file-like
                name = getattr(photo, "name", None)
                files = {"photo": (filename or (os.path.basename(name) if name else "photo.jpg"), photo)}
            else:
                raise TypeError(
                    "Unsupported 'photo' type. Use path, URL, bytes, or a binary file-like object."
                )

            return self._post_multipart("sendPhoto", data=data, files=files)
        finally:
            if close_file:
                close_file.close()

    def send_document(
        self,
        document: str | bytes | pathlib.Path | io.BufferedIOBase,
        *,
        chat_id: str | int | None = None,
        caption: str | None = None,
        parse_mode: t.Literal["MarkdownV2", "HTML"] | None = None,
        disable_notification: bool = False,
        protect_content: bool = False,
        filename: str | None = None,
        reply_to_message_id: int | None = None,
    ) -> dict[str, t.Any]:
        """
        Send a document/file.

        Similar to send_photo but for general files.
        """
        if caption and len(caption) > 1024:
            logger.warning(f"Caption length {len(caption)} exceeds Telegram limit of 1024 characters")
            caption = caption[:1021] + "..."

        data = {
            "chat_id": chat_id or self._cfg.default_chat_id,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
        }
        if caption:
            data["caption"] = caption
        if parse_mode:
            data["parse_mode"] = parse_mode
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id

        # Handle URL case
        if isinstance(document, str) and document.lower().startswith(("http://", "https://")):
            data["document"] = document
            return self._post_json("sendDocument", data=data)

        # Handle file upload
        files = None
        close_file = None
        try:
            if isinstance(document, (str, pathlib.Path)):
                path = pathlib.Path(document)
                if not path.exists():
                    raise FileNotFoundError(f"Document file not found: {path}")
                if not path.is_file():
                    raise ValueError(f"Path is not a file: {path}")

                f = path.open("rb")
                close_file = f
                files = {"document": (path.name, f)}
            elif isinstance(document, bytes):
                if len(document) == 0:
                    raise ValueError("Document bytes cannot be empty")
                files = {"document": (filename or "document.bin", io.BytesIO(document))}
            elif hasattr(document, "read"):
                name = getattr(document, "name", None)
                files = {"document": (filename or (os.path.basename(name) if name else "document.bin"), document)}
            else:
                raise TypeError(
                    "Unsupported 'document' type. Use path, URL, bytes, or a binary file-like object."
                )

            return self._post_multipart("sendDocument", data=data, files=files)
        finally:
            if close_file:
                close_file.close()

    # Optional convenience aliases
    def send_message(self, *args, **kwargs) -> dict[str, t.Any]:
        return self.send_text(*args, **kwargs)

    def send_file(self, *args, **kwargs) -> dict[str, t.Any]:
        return self.send_document(*args, **kwargs)

    def __enter__(self) -> "TelegramNotifier":
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close session on exit."""
        self._session.close()

    # --------------------------- Internal helpers -------------------------

    def _endpoint(self, method: str) -> str:
        return f"{self._cfg.base_url}/bot{self._cfg.token}/{method}"

    def _post_json(self, method: str, json: dict | None = None, data: dict | None = None) -> dict[str, t.Any]:
        """
        POST JSON or form-encoded data (no files). Handles retries & rate limits.
        """
        url = self._endpoint(method)
        attempt = 0
        while True:
            try:
                logger.debug(f"Making request to {method} (attempt {attempt + 1})")
                resp = self._session.post(
                    url,
                    json=json,
                    data=data,
                    timeout=self._cfg.timeout_seconds,
                )
                return self._handle_response(resp)
            except _Retryable as e:
                attempt = self._sleep_backoff_or_raise(e, attempt)

    def _post_multipart(self, method: str, data: dict, files: dict[str, t.Any]) -> dict[str, t.Any]:
        """
        POST multipart/form-data (file upload). Handles retries & rate limits.
        """
        url = self._endpoint(method)
        attempt = 0
        while True:
            try:
                logger.debug(f"Making multipart request to {method} (attempt {attempt + 1})")
                resp = self._session.post(
                    url,
                    data=data,
                    files=files,
                    timeout=self._cfg.timeout_seconds,
                )
                return self._handle_response(resp)
            except _Retryable as e:
                attempt = self._sleep_backoff_or_raise(e, attempt)

    def _handle_response(self, resp: requests.Response) -> dict[str, t.Any]:
        """
        Parse and validate Telegram API responses. Raises on errors with context.
        Handles 429 rate limits using 'retry_after'.
        """
        # Handle network-level retryable errors
        if resp.status_code >= 500:
            raise _Retryable(f"Server error: {resp.status_code}")

        try:
            data = resp.json()
        except ValueError as e:
            if resp.status_code >= 500:
                raise _Retryable(f"Server returned non-JSON: {resp.status_code}")
            raise TelegramAPIError(f"Non-JSON response: {resp.status_code} {resp.text[:200]}") from e

        # Success path
        if resp.ok and data.get("ok", False):
            logger.debug(f"Request successful: {data.get('result', {}).get('message_id', 'N/A')}")
            return data

        # Known rate-limit shape
        if resp.status_code == 429 or (isinstance(data, dict) and data.get("error_code") == 429):
            retry_after = 1
            params = data.get("parameters") or {}
            if isinstance(params, dict) and "retry_after" in params:
                retry_after = int(params["retry_after"])
            logger.warning(f"Rate limited, waiting {retry_after}s")
            raise RateLimited(f"Rate limited: retry after {retry_after}s", retry_after=retry_after)

        # Other API errors
        error_code = data.get("error_code", resp.status_code)
        description = data.get("description", "Unknown error")
        logger.error(f"Telegram API error {error_code}: {description}")
        raise TelegramAPIError(f"Telegram API error ({error_code}): {description}")

    def _sleep_backoff_or_raise(self, exc: "_Retryable", attempt: int) -> int:
        """
        Exponential backoff with special handling for 429.
        """
        if attempt >= self._cfg.max_retries:
            logger.error(f"Max retries ({self._cfg.max_retries}) exceeded")
            # out of retries -> re-raise underlying error
            raise exc  # type: ignore[misc]

        # Respect Telegram's explicit retry_after if present
        if isinstance(exc, RateLimited):
            sleep_time = exc.retry_after
            logger.info(f"Rate limited, sleeping for {sleep_time}s")
            time.sleep(sleep_time)
        else:
            # Exponential backoff: base * 2^attempt
            sleep_time = self._cfg.backoff_seconds * (2 ** attempt)
            logger.info(f"Retrying in {sleep_time}s (attempt {attempt + 1})")
            time.sleep(sleep_time)
        return attempt + 1


# ------------------------------ Exceptions -------------------------------

class TelegramAPIError(Exception):
    """Generic Telegram API error."""


class _Retryable(Exception):
    """Marker for retryable errors (network failures, 5xx, rate limit)."""


class RateLimited(_Retryable, TelegramAPIError):
    def __init__(self, message: str, *, retry_after: int) -> None:
        super().__init__(message)
        self.retry_after = retry_after


# ------------------------------ Utility functions -------------------------------

def create_notifier_from_env() -> TelegramNotifier:
    """Convenience function to create a notifier from environment variables."""
    return TelegramNotifier()


def send_notification(message: str, **kwargs) -> dict[str, t.Any]:
    """Quick one-off notification using environment variables."""
    notifier = create_notifier_from_env()
    return notifier.send_text(message, **kwargs)