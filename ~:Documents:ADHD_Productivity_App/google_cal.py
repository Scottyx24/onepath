"""
google_cal.py — Google Calendar integration for ADHD Productivity App
Uses manual OAuth code flow — compatible with Streamlit Cloud (no browser needed).
"""
import datetime
import json
from pathlib import Path

CREDS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent / "token.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import google.oauth2.credentials
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


def is_available():
    return GOOGLE_AVAILABLE


def has_credentials_file():
    return CREDS_FILE.exists()


def get_service():
    """Return an authenticated Google Calendar service or None."""
    if not GOOGLE_AVAILABLE:
        return None
    if not TOKEN_FILE.exists():
        return None
    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(str(TOKEN_FILE), "w") as f:
                f.write(creds.to_json())
        if creds and creds.valid:
            return build("calendar", "v3", credentials=creds)
    except Exception:
        pass
    return None


def get_auth_url():
    """
    Build the Google OAuth URL manually without opening a browser.
    Returns (client_id, auth_url) so app.py can store client_id for token exchange.
    """
    if not GOOGLE_AVAILABLE:
        raise RuntimeError("Google libraries not installed.")
    if not CREDS_FILE.exists():
        raise FileNotFoundError(
            f"credentials.json not found at {CREDS_FILE}. "
            "Download it from Google Cloud Console."
        )
    with open(str(CREDS_FILE), "r") as f:
        creds_data = json.load(f)

    # Support both 'installed' and 'web' credential types
    info = creds_data.get("installed") or creds_data.get("web")
    if not info:
        raise ValueError("Invalid credentials.json format.")

    client_id = info["client_id"]
    auth_uri = info.get("auth_uri", "https://accounts.google.com/o/oauth2/auth")

    from urllib.parse import urlencode
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = auth_uri + "?" + urlencode(params)
    return client_id, auth_url


def exchange_code_for_token(code):
    """
    Exchange the authorization code for tokens and save token.json.
    Returns True on success.
    """
    if not CREDS_FILE.exists():
        raise FileNotFoundError("credentials.json not found.")

    with open(str(CREDS_FILE), "r") as f:
        creds_data = json.load(f)

    info = creds_data.get("installed") or creds_data.get("web")
    if not info:
        raise ValueError("Invalid credentials.json format.")

    import urllib.request
    from urllib.parse import urlencode

    token_uri = info.get("token_uri", "https://oauth2.googleapis.com/token")
    data = urlencode({
        "code": code,
        "client_id": info["client_id"],
        "client_secret": info["client_secret"],
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode("utf-8")

    req = urllib.request.Request(token_uri, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req) as resp:
        token_data = json.loads(resp.read().decode("utf-8"))

    if "error" in token_data:
        raise RuntimeError(f"Token exchange failed: {token_data['error']} - {token_data.get('error_description', '')}")

    # Build a credentials-compatible token file
    token_json = {
        "token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_uri": token_uri,
        "client_id": info["client_id"],
        "client_secret": info["client_secret"],
        "scopes": SCOPES,
    }
    with open(str(TOKEN_FILE), "w") as f:
        json.dump(token_json, f)

    return True


def disconnect():
    """Remove token file to disconnect."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()


def get_upcoming_events(service, max_results=25):
    if not service:
        return []
    try:
        now = datetime.datetime.utcnow().isoformat() + "Z"
        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return result.get("items", [])
    except Exception:
        return []


def create_event(service, title, start_dt, end_dt, description="", color_id=None):
    """
    Create a Google Calendar event.
    color_id: 1-11 (Google Calendar color IDs)
    Returns the created event ID or None.
    """
    if not service:
        return None
    try:
        body = {
            "summary": title,
            "description": description,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "America/Chicago",
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "America/Chicago",
            },
        }
        if color_id:
            body["colorId"] = str(color_id)
        event = service.events().insert(calendarId="primary", body=body).execute()
        return event.get("id")
    except Exception as e:
        raise RuntimeError(f"Failed to create event: {e}")


def delete_event(service, event_id):
    if not service or not event_id:
        return
    try:
        service.events().delete(calendarId="primary", eventId=event_id).execute()
    except Exception:
        pass


def format_event_time(event):
    """Return a nicely formatted time string from a Google Calendar event dict."""
    start = event.get("start", {})
    dt_str = start.get("dateTime") or start.get("date", "")
    if not dt_str:
        return ""
    try:
        if "T" in dt_str:
            dt = datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            return dt.strftime("%I:%M %p")
        else:
            return "All day"
    except Exception:
        return dt_str[:10]
