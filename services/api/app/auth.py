import hashlib
import hmac

from fastapi import Header, HTTPException, status

from .config import get_settings


async def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    settings = get_settings()
    configured = settings.api_key.get_secret_value() if settings.api_key else ""
    if settings.environment == "local" and not configured:
        return
    if not configured or not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")
    if not hmac.compare_digest(
        hashlib.sha256(x_api_key.encode()).digest(), hashlib.sha256(configured.encode()).digest()
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")


def verify_webhook_signature(body: bytes, signature: str | None) -> bool:
    secret = get_settings().webhook_secret
    if not secret or not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.get_secret_value().encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.removeprefix("sha256="))
