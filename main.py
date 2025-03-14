import time
import uuid
import uvicorn
import redis
import asyncio
import os
import undetected_chromedriver as uc
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any

# Initialize FastAPI app
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global WebDriver instance
driver = None

# Initialize Redis client
redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_client = redis.Redis(host=redis_host, port=6379, db=0)

# Global variable to store chat interactions (for Redis/memory caching)
chat_interactions = {}

# This dictionary will hold pending WS data for each chat_id.
# Depending on the mode, the value is either:
#   - mode "complete": { "future": Future, "chunks": [] }
#   - mode "stream": { "queue": asyncio.Queue() }
pending_ws_data: Dict[str, Dict[str, Any]] = {}

# Background task to clean up expired chat interactions
async def cleanup_expired_chats():
    while True:
        try:
            current_time = time.time()
            # Clean up expired entries from memory
            expired_chats = [cid for cid, data in chat_interactions.items() 
                             if data["expires_at"] <= current_time]
            
            for expired_chat_id in expired_chats:
                # Remove from memory
                del chat_interactions[expired_chat_id]
                # Remove from Redis
                redis_key = f"chat:interaction:{expired_chat_id}"
                redis_client.delete(redis_key)
            
            if expired_chats:
                print(f"Cleaned up {len(expired_chats)} expired chat interactions")
                
        except Exception as e:
            print(f"Error in cleanup task: {str(e)}")
            
        # Wait for 5 minutes before next cleanup
        await asyncio.sleep(300)

@app.on_event("startup")
async def startup_event():
    global driver, chat_interactions
    try:
        # Load existing chat interactions from Redis
        chat_keys = redis_client.keys('chat:interaction:*')
        for key in chat_keys:
            key_str = key.decode('utf-8')
            chat_id = key_str.split(':')[-1]
            value = redis_client.get(key)
            if value:
                chat_interactions[chat_id] = {"prompt": value.decode('utf-8'), "expires_at": time.time() + 300}
        print(f"Loaded {len(chat_interactions)} chat interactions from Redis")

        # Initialize browser
        driver = open_chatgpt_with_cookies()
        print("Browser started and ChatGPT loaded successfully at startup")
        
        # Start the background cleanup task
        asyncio.create_task(cleanup_expired_chats())
        print("Background cleanup task started")
        
    except Exception as e:
        print(f"Error during startup: {str(e)}")
        raise e

# Pydantic model for chat request
class ChatRequest(BaseModel):
    message: str

# Load cookies from a file
def load_cookies_from_txt(file_path):
    start_time = time.time()
    cookies = []
    with open(file_path, "r") as file:
        for line in file:
            parts = line.strip().split("\t")
            if len(parts) >= 7:
                cookie = {
                    "domain": parts[0],
                    "name": parts[5],
                    "value": parts[6],
                    "path": parts[2],
                    "secure": parts[3] == "TRUE",
                    "expiry": int(time.time()) + 3600 * 24 * 30
                }
                cookies.append(cookie)
    end_time = time.time()
    print(f"[⏱️] Cookie loading time: {end_time - start_time:.2f} seconds")
    return cookies

# Initialize Selenium WebDriver with DevTools Protocol enabled
def start_browser():
    global driver
    start_time = time.time()
    chrome_options = Options()

    # Base options for Docker environment
    # chrome_options.add_argument("--headless=new")  # Use new headless mode
    chrome_options.add_argument("--no-sandbox")  # Required for Docker
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    chrome_options.add_argument("--disable-gpu")  # Disable GPU hardware acceleration
    chrome_options.add_argument("--window-size=1920,1080")  # Set window size instead of maximize

    # Proxy and certificate settings
    proxy_host = os.environ.get('PROXY_HOST', 'localhost')
    proxy_port = os.environ.get('PROXY_PORT', '8080')
    chrome_options.add_argument("--proxy-bypass-list=<-loopback>")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument(f"--proxy-server={proxy_host}:{proxy_port}")

    # Additional flags to minimize CPU usage
    chrome_options.add_argument("--disable-gpu")
    # chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    # chrome_options.add_argument("--blink-settings=imagesEnabled=false")  # Disable image loading

    # Capabilities for logging and certificate acceptance
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    chrome_options.set_capability("acceptInsecureCerts", True)

    # Use undetected chromedriver with proper Docker configuration
    service = Service("./chromedriver")
    # Set specific Chrome version to avoid version mismatch issues
    driver = uc.Chrome(service=service, options=chrome_options, version_main=134)

    # Enable DevTools (CDP)
    driver.execute_cdp_cmd("Network.enable", {})
    
    end_time = time.time()
    print(f"[⏱️] Browser initialization time: {end_time - start_time:.2f} seconds")
    return driver

# Open ChatGPT and inject cookies
def open_chatgpt_with_cookies():
    global driver
    total_start_time = time.time()
    driver = start_browser()
    
    # Navigate to ChatGPT
    nav_start_time = time.time()
    chatgpt_url = "https://chat.openai.com"
    driver.get(chatgpt_url)
    time.sleep(2)  # Allow page to load completely
    
    # Load and set cookies
    cookies = load_cookies_from_txt("cookies.txt")
    cookie_set_start = time.time()
    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
            print(f"Cookie set: {cookie['name']}")
        except Exception as e:
            continue
    cookie_set_end = time.time()
    print(f"[⏱️] Cookie setting time: {cookie_set_end - cookie_set_start:.2f} seconds")
    
    # Refresh to apply cookies
    driver.refresh()
    time.sleep(2)  # Allow page to refresh
    nav_end_time = time.time()
    print(f"[⏱️] Navigation and cookie application time: {nav_end_time - nav_start_time:.2f} seconds")
    
    # # Find and click the chat selector
    # chat_selector = WebDriverWait(driver, 10).until(
    #     EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div/div[1]/div/main/div[1]/div[1]/div[2]/button"))
    # )
    # chat_selector.click()

    # # Click on "Temporary Chat" option
    # temp_chat = WebDriverWait(driver, 10).until(
    #     EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Temporary chat')]"))
    # )
    # temp_chat.click()

    return driver

# Handle chat interactions via Selenium
def interact_with_chat(message: str):
    global driver, chat_interactions
    try:
        # Find input field and send a message
        input_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='prompt-textarea']"))
        )
        
        # Generate a unique identifier for this chat interaction
        chat_id = str(uuid.uuid4())
        # Inject the chat_id in the prompt for later identification
        prompt = f"[ignore-this-code:{chat_id}] {message}"
        
        # Store in both memory and Redis with 5-minute expiration
        expiry_time = time.time() + 300  # 5 minutes from now
        chat_interactions[chat_id] = {"prompt": prompt, "expires_at": expiry_time}
        
        # Clean up expired entries from memory
        current_time = time.time()
        expired_chats = [cid for cid, data in chat_interactions.items() if data["expires_at"] <= current_time]
        for expired_chat_id in expired_chats:
            del chat_interactions[expired_chat_id]
        
        # Store in Redis with 5-minute expiration
        redis_key = f"chat:interaction:{chat_id}"
        redis_client.setex(redis_key, 300, prompt)
        
        input_field.click()
        input_field.send_keys(prompt)
        input_field.send_keys(Keys.RETURN)
        return {"chat_id": chat_id}
        # return {"status": "success", "message": "Message sent successfully", "chat_id": chat_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# HTTP endpoint for chat requests.
# If stream==true, return SSE events; otherwise, wait for the complete data.
@app.post("/chat")
async def chat_endpoint(request: ChatRequest, stream: bool = Query(False)):
    if not driver:
        raise HTTPException(status_code=500, detail="Browser initialization failed")
    
    # Trigger Selenium interaction.
    result = interact_with_chat(request.message)
    chat_id = result.get("chat_id")
    if not chat_id:
        raise HTTPException(status_code=500, detail="Failed to generate chat_id")
        
    # Depending on the mode, set up pending_ws_data.
    if stream:
        # Streaming mode: Create a queue for this chat_id.
        pending_ws_data[chat_id] = {"mode": "stream", "queue": asyncio.Queue()}
        
        # Optionally, you could kick off additional async tasks here if needed.
        async def event_generator():
            queue = pending_ws_data[chat_id]["queue"]
            while True:
                chunk = await queue.get()
                if chunk is None:
                    # End-of-stream indicator.
                    break
                yield f"data: {chunk}\n\n"
            # Final event (optional)
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(event_generator(), media_type="text/event-stream")
    
    else:
        # Complete mode: Create a future and a list to accumulate chunks.
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        pending_ws_data[chat_id] = {"mode": "complete", "future": future, "chunks": []}
        
        # Wait until the WebSocket signals completion with [DONE].
        complete_message = await future
        return {"chat_id": chat_id, "data": complete_message}

# WebSocket endpoint to receive chunked data.
# Expected messages: "chat_id:data: <chunk>"
# A chunk equal to "[DONE]" indicates completion.
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw_data = await websocket.receive_text()
            if ":" in raw_data:
                print(raw_data)
                chat_id, remainder = raw_data.split(":", 1)
                chat_id = chat_id.strip()
                if remainder.strip().lower().startswith("data:"):
                    chunk = remainder.strip()[len("data:"):].strip()
                    if chat_id in pending_ws_data:
                        record = pending_ws_data[chat_id]
                        if record["mode"] == "complete":
                            if "[DONE]" in chunk:
                                complete_message = "".join(record["chunks"])
                                if not record["future"].done():
                                    record["future"].set_result(complete_message)
                                del pending_ws_data[chat_id]
                            else:
                                record["chunks"].append(chunk)
                        elif record["mode"] == "stream":
                            if "[DONE]" in chunk:
                                await record["queue"].put(None)
                                del pending_ws_data[chat_id]
                            else:
                                await record["queue"].put(chunk)
    except WebSocketDisconnect:
        pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
