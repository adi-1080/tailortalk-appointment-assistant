import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional

import dateparser
import re
from dateutil import parser as dateutil_parser

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.1
)

tool_call_count = 0

# 🗓️ Tool 1: Availability Checker (still unstructured)
def check_calendar_availability(input_text: str) -> str:
    print(f"[TOOL] Checking availability for: {input_text}")

    try:
        backend_api = os.getenv('BACKEND_API')
        if not backend_api:
            return "Error: BACKEND_API not set"

        # Clean input to help with parsing
        cleaned_text = re.sub(r'\b(is|a|slot|available|free|at|on|the|for|check|if)\b', '', input_text.lower())
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

        print(f"[TOOL] Cleaned text: '{cleaned_text}'")

        desired_start = None

        # Try multiple parsing approaches
        for parse_input in [cleaned_text, input_text]:
            try:
                desired_start = dateparser.parse(
                    parse_input,
                    settings={
                        'TIMEZONE': 'Asia/Kolkata',
                        'RETURN_AS_TIMEZONE_AWARE': True,
                        'PREFER_DATES_FROM': 'future'
                    }
                )
                if desired_start:
                    print(f"[TOOL] Parsed datetime: {desired_start}")
                    break
            except Exception as e:
                print(f"[TOOL] Parsing failed for input '{parse_input}': {e}")

        if not desired_start:
            try:
                desired_start = dateutil_parser.parse(input_text, fuzzy=True)
                print(f"[TOOL] Fallback (dateutil) parsed: {desired_start}")
            except Exception as e:
                return "❌ Couldn't understand the time. Try something like 'Is 10 July 2025 at 3 PM available?'"

        desired_end = desired_start + timedelta(hours=1)

        # Fetch existing events
        response = requests.get(f"{backend_api}/events", timeout=10)
        if response.status_code != 200:
            return f"Error checking calendar: {response.status_code}"

        events = response.json()
        print(f"[TOOL] Found {len(events)} events")

        for event in events:
            start = event['start'].get('dateTime')
            end = event['end'].get('dateTime')
            if not start or not end:
                continue

            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)

            if desired_start < end_dt and desired_end > start_dt:
                return f"❌ Slot at {desired_start.strftime('%I:%M %p on %d %b %Y')} is already booked."

        return f"✅ Slot at {desired_start.strftime('%I:%M %p on %d %b %Y')} is available."

    except Exception as e:
        print(f"[TOOL] Availability check error: {str(e)}")
        return f"❌ Error checking calendar: {str(e)}"


# 🧾 Tool 2: Structured Booking with Pydantic
class BookingInput(BaseModel):
    title: str = Field(description="The title of the meeting")
    start_time: datetime = Field(description="Start time of the meeting (natural language or ISO)")
    end_time: Optional[datetime] = Field(description="End time of the meeting (optional)")

def book_meeting_structured(data) -> str:
    global tool_call_count
    tool_call_count += 1
    print(f"[TOOL] Booking tool called #{tool_call_count}: {data}")

    if tool_call_count > 1:
        return "Booking already completed. No need to book again."

    try:
        backend_api = os.getenv('BACKEND_API')
        if not backend_api:
            return "Error: BACKEND_API not set"

        # Accept dict, str, or BookingInput
        if isinstance(data, BookingInput):
            booking = data
        elif isinstance(data, dict):
            booking = BookingInput(**data)
        elif isinstance(data, str):
            import ast
            try:
                booking_dict = ast.literal_eval(data)
                booking = BookingInput(**booking_dict)
            except Exception as e:
                return f"❌ Could not parse booking input: {e}"
        else:
            return "❌ Invalid input type for booking."

        start = booking.start_time
        end = booking.end_time or (start + timedelta(hours=1))

        payload = {
            "summary": booking.title,
            "start_time": start.isoformat()
        }

        response = requests.post(f"{backend_api}/book", json=payload, timeout=10)
        if response.status_code == 200:
            link = response.json().get("event_link", "Booking complete")
            return f"📅 Meeting '{booking.title}' booked from {start.strftime('%I:%M %p')} to {end.strftime('%I:%M %p')} — [Open event]({link})"
        else:
            return f"❌ Booking failed with status {response.status_code}"

    except Exception as e:
        return f"❌ Booking error: {str(e)}"


# 🛠 Register tools
tools = [
    Tool(
        name="check_calendar_availability",
        func=check_calendar_availability,
        description="Check if a calendar slot is free. Use with queries like 'Is 10th July at 3PM available?'"
    ),
    StructuredTool.from_function(
        func=book_meeting_structured,
        name="book_meeting",
        description="Book a Google Calendar event. Provide title, start_time, and optionally end_time."
    )
]

# 🤖 Initialize Agent
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    max_iterations=3,
    early_stopping_method="generate",
    agent_kwargs={
        "system_message": """You are a helpful calendar assistant.

Your job is to:
1. Check slot availability using the check_calendar_availability tool.
2. Book meetings using book_meeting (only after confirmation or when clearly asked).
3. If the user says things like "Is 3PM on 10 July available?" → use check tool.
4. If they say "Book a meeting from 4pm to 5pm titled XYZ" → extract values and call book_meeting.
"""
    }
)

# 🚀 Agent runner
def run_agent(user_input: str) -> str:
    try:
        global tool_call_count
        tool_call_count = 0

        print("[AGENT] Received input:", user_input)
        import threading

        result = [None]
        exception = [None]

        def run_with_timeout():
            try:
                result[0] = agent.run(user_input)
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=run_with_timeout)
        thread.daemon = True
        thread.start()
        thread.join(timeout=30)

        if thread.is_alive():
            return "⚠️ Agent timed out (30s limit)"

        if exception[0]:
            raise exception[0]

        return result[0]

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"❌ Agent error: {str(e)}"
