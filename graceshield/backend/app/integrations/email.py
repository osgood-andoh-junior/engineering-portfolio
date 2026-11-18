import httpx

from app.core.config import Settings
from app.core.exceptions import DomainError


def send_account_email(settings: Settings, recipient: str, purpose: str, raw_token: str) -> None:
    if (
        not settings.email_enabled
        or not settings.email_api_token.get_secret_value()
        or not settings.email_api_url.startswith("https://")
        or not settings.email_from
    ):
        raise DomainError(
            "email_unavailable", "Email delivery is not configured. No email was sent.", 503
        )
    route = "verify-email" if purpose == "verify" else "reset-password"
    link = f"{settings.frontend_origin}/{route}#token={raw_token}"
    try:
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            result = client.post(
                settings.email_api_url,
                headers={"Authorization": f"Bearer {settings.email_api_token.get_secret_value()}"},
                json={
                    "from": settings.email_from,
                    "to": recipient,
                    "subject": f"GraceShield account {purpose}",
                    "text": f"Open this single-use link: {link}",
                },
            )
            result.raise_for_status()
    except httpx.HTTPError:
        raise DomainError(
            "email_unavailable",
            "Email delivery could not be confirmed. Please try again later.",
            503,
        ) from None
