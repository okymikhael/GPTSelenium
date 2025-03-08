import time
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, Response
import uvicorn
import undetected_chromedriver as uc
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from typing import Optional
from pydantic import BaseModel
from lxml import etree
from io import StringIO

app = FastAPI()
driver = None
prompt_start = 2

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
    start_time = time.time()
    try:
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})  # Enable network logs

        # Use undetected chromedriver with error handling
        service = Service("./chromedriver")
        driver = uc.Chrome(service=service, options=chrome_options)

        # Enable DevTools (CDP) with error handling
        try:
            driver.execute_cdp_cmd("Network.enable", {})
        except Exception as e:
            print(f"[Warning] CDP initialization failed: {str(e)}")
        
        end_time = time.time()
        print(f"[⏱️] Browser initialization time: {end_time - start_time:.2f} seconds")
        return driver
    except Exception as e:
        print(f"[Error] Browser initialization failed: {str(e)}")
        raise

# Initialize ChatGPT session
def initialize_chatgpt(max_retries=3, retry_delay=2):
    global driver
    
    for attempt in range(max_retries):
        try:
            driver = start_browser()
            
            # Navigate to ChatGPT
            chatgpt_url = "https://chat.openai.com"
            driver.get(chatgpt_url)
            time.sleep(3)  # Allow page to load completely
            
            # Load and set cookies
            cookies = load_cookies_from_txt("cookies.txt")
            for cookie in cookies:
                try:
                    if 'expiry' in cookie:
                        # Ensure expiry is an integer
                        cookie['expiry'] = int(cookie['expiry'])
                    driver.add_cookie(cookie)
                except Exception as e:
                    print(f"[Warning] Failed to add cookie: {str(e)}")
                    continue
            
            # Refresh to apply cookies
            driver.get(chatgpt_url)
            time.sleep(3)  # Allow page to refresh

            try:
                # Wait for the page to be interactive
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Find and click the chat selector
                chat_selector = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div/div[1]/div[2]/main/div[1]/div[1]/div/div[1]/div/div[2]"))
                )
                chat_selector.click()

                # Click on "Temporary Chat" option
                temp_chat = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Temporary chat')]")),
                )
                temp_chat.click()
                return True
                
            except Exception as e:
                print(f"[Warning] Failed to initialize chat interface: {str(e)}")
                if driver:
                    driver.quit()
                raise
                
        except Exception as e:
            print(f"[Warning] Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            if driver:
                driver.quit()
            driver = None
            
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            else:
                print("[Error] All initialization attempts failed")
                raise
    
    return False

# Send message and get response
async def send_message_and_get_response(message: str) -> str:
    global prompt_start
    previous_content = ""
    first_copy_found = True
    
    try:
        input_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='prompt-textarea']"))
        )
        
        # PROMPT_HELPER = "please answer using html tag only and make it colorfull and dont explain outside html tag"
        PROMPT_HELPER = ""
        
        input_field.click()
        input_field.send_keys(f"{message}, {PROMPT_HELPER}")
        input_field.send_keys(Keys.RETURN)
        
        print(f"[Sent] Message from ChatGPT:")

        while True:
            try:
                result = WebDriverWait(driver, 0.1).until(
                    EC.visibility_of_element_located((By.XPATH, f"/html/body/div[1]/div/div[1]/div[2]/main/div[1]/div[1]/div/div/article[{prompt_start}]/div/div/div/div/div[1]/div/div/div"))
                )
                
                html_content = result.get_attribute('outerHTML')
                
                # Validate HTML content
                if not html_content or not html_content.strip():
                    print("[Warning] Empty HTML content received")
                    continue

                # Remove thinking
                html_content = html_content.replace('<div class="result-thinking markdown prose w-full break-words dark:prose-invert dark"><p data-start="0" data-end="7" data-is-last-node=""></p></div>', '')

                # Remove thinking
                html_content = html_content.replace('markdown prose w-full break-words dark:prose-invert dark"></div>', '')

                # Remove the Edit button SVG content first
                html_content = html_content.replace('<button class="flex select-none items-center gap-1"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="icon-xs"><path d="M2.5 5.5C4.3 5.2 5.2 4 5.5 2.5C5.8 4 6.7 5.2 8.5 5.5C6.7 5.8 5.8 7 5.5 8.5C5.2 7 4.3 5.8 2.5 5.5Z" fill="currentColor" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"></path><path d="M5.66282 16.5231L5.18413 19.3952C5.12203 19.7678 5.09098 19.9541 5.14876 20.0888C5.19933 20.2067 5.29328 20.3007 5.41118 20.3512C5.54589 20.409 5.73218 20.378 6.10476 20.3159L8.97693 19.8372C9.72813 19.712 10.1037 19.6494 10.4542 19.521C10.7652 19.407 11.0608 19.2549 11.3343 19.068C11.6425 18.8575 11.9118 18.5882 12.4503 18.0497L20 10.5C21.3807 9.11929 21.3807 6.88071 20 5.5C18.6193 4.11929 16.3807 4.11929 15 5.5L7.45026 13.0497C6.91175 13.5882 6.6425 13.8575 6.43197 14.1657C6.24513 14.4392 6.09299 14.7348 5.97903 15.0458C5.85062 15.3963 5.78802 15.7719 5.66282 16.5231Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path><path d="M14.5 7L18.5 11" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path></svg>Edit</button>', '')

                # Remove the code block header div
                html_content = html_content.replace('<div class="flex items-center text-token-text-secondary px-4 py-2 text-xs font-sans justify-between rounded-t-[5px] h-9 bg-token-sidebar-surface-primary dark:bg-token-main-surface-secondary select-none"></div>', '')

                try:
                        # Validate HTML structure
                    try:
                        parser = etree.HTMLParser()
                        etree.parse(StringIO(html_content), parser)
                        
                        # Convert HTML to Markdown
                        import html2text
                        h = html2text.HTML2Text()
                        h.ignore_links = False
                        h.ignore_images = False
                        html_content = h.handle(html_content)
                    except etree.ParseError as e:
                        print(f"[Warning] HTML validation failed: {str(e)}")
                        continue

                    # Only yield the new content
                    if html_content != previous_content:
                        # Find the longest common prefix between previous and current content
                        common_length = 0
                        min_length = min(len(previous_content), len(html_content))
                        while common_length < min_length and previous_content[common_length] == html_content[common_length]:
                            common_length += 1
                            
                        # Extract only the new content
                        new_content = html_content[common_length:]
                        if new_content.strip():  # Only send if there's actual new content
                            previous_content = html_content
                            # Remove extra newlines and whitespace
                            cleaned_content = "\n".join(line for line in new_content.splitlines() if line.strip())
                            if cleaned_content:
                                print(cleaned_content)
                                yield cleaned_content

                except Exception as e:
                    print(f"[Warning] HTML to Markdown conversion failed: {str(e)}")
                    continue
                
                # Check if response is complete
                try:
                    element = WebDriverWait(driver, 0.1).until(
                        EC.visibility_of_element_located((By.XPATH, f"/html/body/div[1]/div/div[1]/div[2]/main/div[1]/div[1]/div/div/article[{prompt_start}]/div/div/div/div/div[2]"))
                    )
                    
                    if element.is_displayed():
                        if first_copy_found < 6: # Loop the process 5 times to make sure all data is processed
                            first_copy_found += 1
                            continue
                        else:
                            prompt_start += 2
                            yield "[END-OF-MESSAGE-SOREAN]"
                            break
                except:
                    continue
                
            except Exception:
                await asyncio.sleep(0.1)
                continue
            
    except Exception as e:
        yield f"Error: {str(e)}"

# WebSocket endpoint for real-time response streaming
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            message = await websocket.receive_text()
            async for response in send_message_and_get_response(message):
                await websocket.send_text(response)
    except Exception as e:
        await websocket.close()

# HTTP endpoint that waits for complete response
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        response = None
        async for result in send_message_and_get_response(request.message):
            response = result
        return Response(content=response, media_type="text/plain")
    except Exception as e:
        return Response(content=str(e), status_code=500)

# Startup event to initialize ChatGPT
@app.on_event("startup")
def startup_event():
    try:
        if not initialize_chatgpt():
            print("[Error] ChatGPT initialization returned False")
            raise Exception("Failed to initialize ChatGPT: initialization returned False")
    except Exception as e:
        print(f"[Error] ChatGPT initialization failed with error: {str(e)}")
        raise Exception(f"Failed to initialize ChatGPT: {str(e)}")

# Shutdown event to close the browser
@app.on_event("shutdown")
def shutdown_event():
    if driver:
        driver.quit()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
