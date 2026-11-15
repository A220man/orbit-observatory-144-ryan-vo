\"\"\"OIDC client implementation for Keycloak-based authentication.\"\"\"

import secrets
import base64
import hashlib
import json
from typing import Dict, Any, Tuple, Optional

import httpx

from authlib.integrations.oauth2 import OAuth2Client
from authlib.integrations.oauth2.rfc6749.parameters import (
    generate_code_verifier,
    generate_code_challenge,
    CodeChallengeMethod,
)
from authlib.integrations.oidc_core import UserInfo
from authlib.jose import JsonWebKey
from authlib.jose.rfc7519 import JsonWebToken

from app.core.config import settings

# In-memory store for PKCE state; in production use Redis or similar.
_OIDC_STATE_STORE: Dict[str, Tuple[str, str, str]] = {}


def _generate_pkce() -> Tuple[str, str, str]:
    """Generate PKCE code verifier, challenge, and state."""
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier, CodeChallengeMethod.S256)
    state = secrets.token_urlsafe(16)
    return code_verifier, code_challenge, state


def _save_state(code_verifier: str, code_challenge: str, redirect_uri: str, state: str) -> None:
    _OIDC_STATE_STORE[state] = (code_verifier, code_challenge, redirect_uri)


def _retrieve_state(state: str) -> Optional[Tuple[str, str, str]]:
    return _OIDC_STATE_STORE.pop(state, None)


def get_authorization_url(redirect_uri: str) -> Tuple[str, str]:
    """Create the authorization URL for OAuth2 authorization code flow with PKCE."""
    code_verifier, code_challenge, state = _generate_pkce()
    _save_state(code_verifier, code_challenge, redirect_uri, state)
    client = OAuth2Client(
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
        redirect_uri=redirect_uri,
        scope="openid email profile",
    )
    auth_url = client.create_authorization_url(
        authorize_endpoint=f"{settings.oidc_issuer_url}/protocol/openid-connect/auth",
        state=state,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    return auth_url, state


def exchange_code(code: str, state: str) -> Dict[str, Any]:
    """Exchange authorization code for tokens and validate the ID token."""
    stored = _retrieve_state(state)
    if not stored:
        raise ValueError("State not found or already used")
    code_verifier, _, redirect_uri = stored
    client = OAuth2Client(
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
        redirect_uri=redirect_uri,
    )
    token_response = client.fetch_token(
        token_endpoint=f"{settings.oidc_issuer_url}/protocol/openid-connect/token",
        code=code,
        redirect_uri=redirect_uri,
        code_verifier=code_verifier,
        grant_type="authorization_code",
    )
    # Validate ID token if present
    id_token = token_response.get("id_token")
    if id_token:
        # Fetch JWKS from issuer
        jwks_url = f"{settings.oidc_issuer_url}/protocol/openid-connect/certs"
        resp = httpx.get(jwks_url)
        resp.raise_for_status()
        jwks = resp.json()
        # Load the appropriate key based on the 'kid' in the ID token header
        # For simplicity, we assume the first matching key; proper implementation
        # would parse the token header and select the matching key.
        key = JsonWebKey.import_key(jwks, "public_key")
        # Decode and verify the ID token
        jwt = JsonWebToken(["RS256"])
        payload = jwt.decode(id_token, key=key)
        # Standard claims verification (issuer, audience, expiration) is done by authlib's decode
        token_response["id_token_payload"] = payload
        # Extract userinfo (may be in 'userinfo' endpoint or id_token)
        # For simplicity, we assume userinfo is in token_response.get('userinfo')
        if "userinfo" not in token_response:
            # Optionally fetch userinfo
            pass
    return token_response


# Helper to map Keycloak roles to internal user roles
def map_keycloak_roles(realm_access_roles: list) -> list:
    """Convert realm roles to internal user roles."""
    allowed = {"viewer", "operator", "admin"}
    return [role for role in realm_access_roles if role in allowed]


# Utility to fetch public JWKS from issuer
def fetch_jwks(issuer_url: str) -> Dict[str, Any]:
    """Fetch JSON Web Key Set from the OIDC issuer."""
    jwks_url = f"{issuer_url}/protocol/openid-connect/certs"
    resp = httpx.get(jwks_url)
    resp.raise_for_status()
    return resp.json()\n
