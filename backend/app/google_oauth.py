"""Google Identity Services credential verification."""

import httpx
from jose import JWTError, jwt

from app.config import GOOGLE_CLIENT_ID

GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"


class GoogleCredentialError(ValueError):
    pass


class GoogleProviderUnavailable(RuntimeError):
    pass


def verify_google_credential(credential: str) -> dict:
    if not GOOGLE_CLIENT_ID:
        raise GoogleProviderUnavailable("Google sign-in is not configured")

    try:
        header = jwt.get_unverified_header(credential)
        if header.get("alg") != "RS256" or not header.get("kid"):
            raise GoogleCredentialError("Invalid Google credential")

        response = httpx.get(GOOGLE_CERTS_URL, timeout=5.0)
        response.raise_for_status()
        signing_keys = response.json().get("keys", [])
        signing_key = next(
            (key for key in signing_keys if key.get("kid") == header["kid"]),
            None,
        )
        if signing_key is None:
            raise GoogleCredentialError("Google credential signing key is unknown")

        claims = jwt.decode(
            credential,
            signing_key,
            algorithms=["RS256"],
            audience=GOOGLE_CLIENT_ID,
            issuer=["accounts.google.com", "https://accounts.google.com"],
        )
    except httpx.HTTPError as error:
        raise GoogleProviderUnavailable("Could not reach Google's sign-in service") from error
    except JWTError as error:
        raise GoogleCredentialError("Google credential is invalid or expired") from error

    if not claims.get("sub") or not claims.get("email"):
        raise GoogleCredentialError("Google credential is missing account details")
    if claims.get("email_verified") not in (True, "true"):
        raise GoogleCredentialError("Verify your Google email before signing in")
    return claims
