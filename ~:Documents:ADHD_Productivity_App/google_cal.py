"""
google_cal.py — Google Calendar integration for ADHD Productivity App
"""
import datetime
import json
import os
from pathlib import Path

CREDS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent / "token.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
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
    Generate the Google OAuth authorization URL.
    Returns (flow, auth_url) tuple.
    """
    if not GOOGLE_AVAILABLE:
        raise RuntimeError("Google libraries not installed.")
    if not CREDS_FILE.exists():
        raise FileNotFoundError(
            f"credentials.json not found at {CREDS_FILE}. "
            "Download it from Google Cloud Console."
        )
    flow = Flow.from_client_secrets_file(
        str(CREDS_FILE),
        scopes=SCOPES,
        redirect_uri="urn:ietf:wg:oauth:2.0:oob"
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    return flow, auth_url


def exchange_code_for_token(flow, code):
    """
    Exchange the authorization code for credentials and save token.json.
    Returns True on success.
    """
    flow.fetch_token(code=code)
    creds = flow.credentials
    with open(str(TOKEN_FILE), "w") as f:
        f.write(creds.to_json())
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
