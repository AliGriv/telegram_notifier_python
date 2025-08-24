from dataclasses import dataclass, field

@dataclass(frozen=True)
class TelegramConfig:
    token: str
    default_chat_id: str | int
    base_url: str = "https://api.telegram.org"
    timeout_seconds: float = 10.0           # per-request timeout
    max_retries: int = 3                    # network & 5xx retries
    backoff_seconds: float = 1.0            # base backoff
    session_headers: dict[str, str] = field(default_factory=dict)  # optional static headers
