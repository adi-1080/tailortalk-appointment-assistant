from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.calendar_utils import get_events, book_event
from datetime import datetime, timedelta
from backend.langchain_agent import run_agent
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
import requests

app = FastAPI()

origins = ["*"]

app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/events")
def fetch_events():
    return get_events()

@app.post("/book")
async def book(request: Request):
    data = await request.json()
    summary = data.get("summary", "Untitled Event")
    start_time = data.get("start_time")

    if not start_time:
        return {"error": "Missing start_time in request"}
    
    start = datetime.fromisoformat(start_time)
    end = start + timedelta(hours=1)
    event = book_event(summary, start.isoformat(), end.isoformat())
    
    return {"status": "booked", "event_link": event.get("htmlLink")}

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user_message = data.get("message")
        
        if not user_message:
            return {"error": "No message provided"}
        
        print(f"[CHAT] Processing message: {user_message}")
        
        # Run original langchain agent with timeout
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, run_agent, user_message)
        
        if not response:
            return {"error": "No response from agent"}
        
        print(f"[CHAT] Response: {response}")
        return {"response": response}
    
    except asyncio.TimeoutError:
        print("[ERROR] Chat endpoint timed out")
        return {"error": "Request timed out - agent took too long to respond"}
    except Exception as e:
        print(f"[ERROR] Chat endpoint error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": f"Internal server error: {str(e)}"}

# Scheduler to ping the server every 10 minutes

def ping_self():
    try:
        url = "https://tailortalk-appointment-assistant.onrender.com/"  # Change to your deployed URL if needed
        print(f"Pinging {url} to keep server awake...")
        requests.get(url)
    except Exception as e:
        print(f"Ping failed: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(ping_self, 'interval', minutes=10)
scheduler.start()