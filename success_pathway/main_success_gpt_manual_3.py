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

# Initialize Selenium WebDriver with DevTools Protocol enabled
def start_browser():
    start_time = time.time()
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Configure proxy with error handling
    chrome_options.add_argument("--proxy-bypass-list=<-loopback>")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--proxy-server=localhost:8080")
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

    try:
        chat_start_time = time.time()
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
        chat_setup_end = time.time()
        print(f"[⏱️] Chat setup time: {chat_setup_end - chat_start_time:.2f} seconds")

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

        print(f"[Sent] Message to ChatGPT: {ask}")
        message_end_time = time.time()
        print(f"[⏱️] Message sending time: {message_end_time - message_start_time:.2f} seconds")
        
        response_start_time = time.time()
        while True:
            try:
                # Get the response element and extract its HTML
                result = WebDriverWait(driver, 0.1).until(
                        EC.visibility_of_element_located((By.XPATH, "/html/body/div[1]/div/div[1]/div[2]/main/div[1]/div[1]/div/div/article[2]/div/div/div/div/div[1]/div/div/div"))
                    )
                
                # Get the outerHTML and convert to Markdown
                try:
                    # Get the text content and convert to Markdown
                    html_content = result.get_attribute('outerHTML')
                    # Remove edit button from HTML content
                    html_content = html_content.replace('<button class="flex select-none items-center gap-1"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="icon-xs"><path d="M2.5 5.5C4.3 5.2 5.2 4 5.5 2.5C5.8 4 6.7 5.2 8.5 5.5C6.7 5.8 5.8 7 5.5 8.5C5.2 7 4.3 5.8 2.5 5.5Z" fill="currentColor" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"></path><path d="M5.66282 16.5231L5.18413 19.3952C5.12203 19.7678 5.09098 19.9541 5.14876 20.0888C5.19933 20.2067 5.29328 20.3007 5.41118 20.3512C5.54589 20.409 5.73218 20.378 6.10476 20.3159L8.97693 19.8372C9.72813 19.712 10.1037 19.6494 10.4542 19.521C10.7652 19.407 11.0608 19.2549 11.3343 19.068C11.6425 18.8575 11.9118 18.5882 12.4503 18.0497L20 10.5C21.3807 9.11929 21.3807 6.88071 20 5.5C18.6193 4.11929 16.3807 4.11929 15 5.5L7.45026 13.0497C6.91175 13.5882 6.6425 13.8575 6.43197 14.1657C6.24513 14.4392 6.09299 14.7348 5.97903 15.0458C5.85062 15.3963 5.78802 15.7719 5.66282 16.5231Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path><path d="M14.5 7L18.5 11" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path></svg>Edit</button>', '')
                    print(f"\n[Response from ChatGPT]:\n{html_content}")
                    
                    # Save markdown content to file
                    filename = "chatgpt_response.md"
                    with open(filename, "w") as f:
                        f.write(html_content)
                    print(f"[✓] Response saved to {filename}")
                except Exception as e:
                    print("Error:", e)

                # Stop until copy text visible
                element = WebDriverWait(driver, 0.1).until(
                    EC.visibility_of_element_located((By.XPATH, "/html/body/div[1]/div/div[1]/div[2]/main/div[1]/div[1]/div/div/article[2]/div/div/div/div/div[2]"))
                )

                # Check if the element is visible
                is_visible = element.is_displayed()
                if is_visible:
                    response_end_time = time.time()
                    print(f"[⏱️] Response processing time: {response_end_time - response_start_time:.2f} seconds")
                    print("[✅] Message sent successfully!")
                    time.sleep(1000)
                    break
            except Exception as e:
                continue
            
            time.sleep(0.1)
            
        total_end_time = time.time()
        print(f"[⏱️] Total execution time: {total_end_time - total_start_time:.2f} seconds")
        print("[x] Done!")

    except Exception as e:
        print("[Error]", e)

if __name__ == "__main__":
    open_chatgpt_with_cookies()
