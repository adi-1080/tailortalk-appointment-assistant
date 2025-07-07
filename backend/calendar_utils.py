import os
import json
import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_ID = "adityagupta5277@gmail.com"

# Load credentials JSON from environment variable
creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not creds_json:
    raise ValueError("Missing GOOGLE_CREDENTIALS_JSON environment variable")

# Parse JSON and create credentials
creds_dict = json.loads(creds_json)
credentials = service_account.Credentials.from_service_account_info(
    creds_dict,
    scopes=SCOPES
)

# Build the Google Calendar API service
service = build('calendar', 'v3', credentials=credentials)

def get_events():
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=now,
        maxResults=10,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events_result.get('items', [])

def book_event(summary, start_time, end_time):
    event = {
        'summary': summary,
        'start': {'dateTime': start_time, 'timeZone': 'Asia/Kolkata'},
        'end': {'dateTime': end_time, 'timeZone': 'Asia/Kolkata'}
    }
    event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    return event
