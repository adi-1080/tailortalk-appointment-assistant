import os
import json
import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_ID = "adityagupta5277@gmail.com"

# Load credentials from credentials/service_account.json
creds_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials', 'service_account.json')
if not os.path.exists(creds_path):
    raise ValueError(f"Google credentials file not found at {creds_path}")

credentials = service_account.Credentials.from_service_account_file(
    creds_path,
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
