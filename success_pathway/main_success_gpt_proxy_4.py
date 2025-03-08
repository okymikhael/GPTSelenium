import time
import undetected_chromedriver as uc
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

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

# Global WebDriver instance
driver = None

# Initialize Selenium WebDriver with DevTools Protocol enabled
def start_browser():
    global driver
    start_time = time.time()
    chrome_options = Options()

    # Base options
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Proxy and certificate settings
    chrome_options.add_argument("--proxy-bypass-list=<-loopback>")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--proxy-server=localhost:8080")

    # Additional flags to minimize CPU usage
    chrome_options.add_argument("--disable-gpu")  # Disable GPU hardware acceleration
    chrome_options.add_argument("--disable-extensions")  # Disable extensions
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")  # Disable image loading

    # Capabilities for logging and certificate acceptance
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    chrome_options.set_capability("acceptInsecureCerts", True)

    # Use undetected chromedriver
    service = Service("./chromedriver")
    driver = uc.Chrome(service=service, options=chrome_options)

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
    return driver

# Handle chat interactions
def interact_with_chat():
    global driver
    try:
        # Find and click the chat selector
        chat_selector = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div/div[1]/div[2]/main/div[1]/div[1]/div/div[1]/div/div[2]"))
        )
        chat_selector.click()

        # Click on "Temporary Chat" option
        temp_chat = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Temporary chat')]"))
        )
        temp_chat.click()

        # Find input field and send a message
        message_start_time = time.time()
        input_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='prompt-textarea']"))
        )
        
        command = "Hi,"
        ask = f"{command} Write a simple 'Hello, World!' program in HTML and CSS."
        
        input_field.click()
        input_field.send_keys(ask)
        input_field.send_keys(Keys.RETURN)

        time.sleep(1000) # stop selenium to closing app

    except Exception as e:
        print("[Error]", e)

if __name__ == "__main__":
    open_chatgpt_with_cookies()
    interact_with_chat()
