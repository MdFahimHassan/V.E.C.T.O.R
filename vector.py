import speech_recognition as sr
import os
import subprocess
import time
import random
from google import genai
from google.genai import types
from dotenv import load_dotenv # <--- Add this import

# Load the secret .env file safely into local environment variables
load_dotenv()

# ==========================================
# 🧠 CORE ENGINE CONFIGURATION
# ==========================================
# Instead of hardcoding, Python pulls it directly from system memory
API_KEY = os.getenv("GEMINI_API_KEY")

try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    print(f"[System Error] Failed to initialize AI client: {e}")
    client = None

def listen_command():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 4000
    recognizer.dynamic_energy_threshold = True
    
    with sr.Microphone() as source:
        print("\n[V.E.C.T.O.R.] System active. Listening...")
        recognizer.adjust_for_ambient_noise(source, duration=2)
        audio = recognizer.listen(source, phrase_time_limit=5)

    try:
        print("[V.E.C.T.O.R.] Parsing audio data...")
        command = recognizer.recognize_google(audio)
        return command.lower()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        return ""

def query_ai_with_retry(prompt, max_retries=3):
    """
    Tries to connect to Google's brain. If a 503 occurs, it automatically 
    backs off and retries before throwing an error.
    """
    delay = 2.0  # Base wait time in seconds
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt
            )
            return response.text
        except Exception as e:
            # Check if the server is telling us it's overloaded
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                if attempt < max_retries - 1:
                    # Add random jitter so we don't hit the server at the exact same millisecond
                    jitter = random.uniform(0.5, 1.5)
                    total_sleep = (delay * (2 ** attempt)) + jitter
                    print(f"[V.E.C.T.O.R.] Neural core busy. Retrying automatically in {total_sleep:.1f}s...")
                    time.sleep(total_sleep)
                    continue
            
            # If it's a different error or we ran out of retries, print failure
            print(f"[V.E.C.T.O.R.] Connection dropped: {e}")
            return None

def execute_command(command):
    print(f"-> Parsed Text: '{command}'")
    
    if "shutdown program" in command or "exit" in command:
        print("[V.E.C.T.O.R.] Deactivating core engine. Goodbye, sir.")
        return False
        
    elif "open notepad" in command:
        print("[V.E.C.T.O.R.] Opening Notepad application, sir.")
        subprocess.Popen(["notepad.exe"])
        
    elif "open chrome" in command:
        print("[V.E.C.T.O.R.] Launching Google Chrome browser, sir.")
        chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        if os.path.exists(chrome_path):
            subprocess.Popen([chrome_path])
        else:
            print("[V.E.C.T.O.R.] Error: Chrome path not found.")
            
    # 🧠 THE UPGRADED BRAIN FALLBACK
    else:
        if client:
            print("[V.E.C.T.O.R.] Querying neural core networks...")
            ai_response = query_ai_with_retry(command)
            
            if ai_response:
                print(f"\n[V.E.C.T.O.R.]: {ai_response}\n")
            else:
                print("[V.E.C.T.O.R.] Neural networks completely congested right now, sir. Try again shortly.")
        else:
            print("[V.E.C.T.O.R.] AI Core client offline.")
            
    return True

if __name__ == "__main__":
    running = True
    while running:
        user_speech = listen_command()
        if user_speech:
            running = execute_command(user_speech)