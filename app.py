# frontend/app.py

import streamlit as st
import requests
import os


A = os.get_env("BACKEND_API")
API_URL = f"{A}/chat"

st.set_page_config(page_title="TailorTalk", page_icon="🧵")
st.title("🧵 TailorTalk - Appointment Assistant")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display past messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input field for user
if prompt := st.chat_input("Book a meeting..."):
    # Display user message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Send to FastAPI backend
    with st.spinner("Thinking..."):
        try:
            response = requests.post(API_URL, json={"message": prompt}, timeout=35)  # Increased timeout
            data = response.json()
            
            if "error" in data:
                reply = f"❌ Error: {data['error']}"
            else:
                reply = data.get("response", "⚠️ Sorry, I didn't understand.")
                
        except requests.exceptions.Timeout:
            reply = "⏰ Request timed out. The agent is taking too long to respond."
        except requests.exceptions.ConnectionError:
            reply = "🔌 Connection error. Please check if the backend server is running."
        except Exception as e:
            reply = f"❌ Error: {str(e)}"

    # Display bot response
    st.chat_message("assistant").markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
