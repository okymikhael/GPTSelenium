const messageInput = document.getElementById('messageInput');
const statusDiv = document.getElementById('status');
const messageContainer = document.getElementById('messageContainer');
let currentMessageDiv = null;

// Theme handling
function initializeTheme() {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const savedTheme = localStorage.getItem('theme');
    const theme = savedTheme || (prefersDark ? 'dark' : 'light');
    document.getElementById("hljs-light").disabled = prefersDark;
    document.getElementById("hljs-dark").disabled = !prefersDark;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    // Update placeholder text based on theme
    messageInput.placeholder = newTheme === 'light' ? 'Tanyalah hari ini tuan putih...' : 'Tanyalah hari ini tuan hitam...';
}

// Initialize theme based on saved preference or system preference
initializeTheme();

// Set initial placeholder text based on theme
const initialTheme = document.documentElement.getAttribute('data-theme');
messageInput.placeholder = initialTheme === 'light' ? 'Tanyalah hari ini tuan putih...' : 'Tanyalah hari ini tuan hitam...';

// Listen for system theme changes
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (!localStorage.getItem('theme')) {
        const theme = e.matches ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }
});

// Configure marked options
marked.setOptions({
    breaks: true,
    gfm: true
});

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

    // Create and display user message
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message sent';
    messageDiv.innerHTML = message;
    messageContainer.appendChild(messageDiv);
    messageContainer.scrollTop = messageContainer.scrollHeight;
    messageInput.value = '';

    // Remove welcome heading and quick actions
    const welcomeHeading = document.querySelector('.welcome-heading');
    const quickActions = document.querySelector('.quick-actions');
    if (welcomeHeading) welcomeHeading.remove();
    if (quickActions) quickActions.remove();
    document.querySelector('.input-container').classList.add('shifted');

    try {
        // statusDiv.textContent = 'Connected';
        // statusDiv.className = 'connected';

        // Create response message container
        currentMessageDiv = document.createElement('div');
        currentMessageDiv.className = 'message received';
        messageContainer.appendChild(currentMessageDiv);

        const response = await fetch('http://localhost:8000/chat?stream=true', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream'
            },
            credentials: 'same-origin',
            body: JSON.stringify({ message: message })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let currentContent = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const text = decoder.decode(value);
            if (text === '[DONE]') {
                currentMessageDiv = null;
                currentContent = "";
                break;
            }

            const lines = text.split('\n');
            for (const line of lines) {
                if (line.trim() === '') continue;
                if (line.trim() === 'data: [DONE]') {
                    currentMessageDiv = null;
                    currentContent = "";
                    break;
                }

                // Extract the JSON data from the line
                let jsonData = null;
                try {
                    const jsonStr = line.startsWith('data: ') ? line.slice(6).trim() : line.trim();
                    if (jsonStr === '[DONE]') continue;
                    jsonData = JSON.parse(jsonStr);
                } catch (e) {
                    // console.log('Skipping invalid JSON:', line);
                    continue;
                }

                // Process only JSON data that contains the 'v' parameter
                if (jsonData && typeof jsonData === 'object' && jsonData.v !== undefined && jsonData.v !== null) {
                    let messageText = '';
                    
                    // Check if the data is a message object with content
                    if (jsonData.message && jsonData.message.content && jsonData.message.content.parts) {
                        // messageText = jsonData.message.content.parts.join('');
                    }
                    // Check if it's a direct text value in 'v'
                    else if (typeof jsonData.v === 'string') {
                        messageText = jsonData.v;
                    }
                    // Handle object with emoji property
                    else if (typeof jsonData.v === 'object' && jsonData.v.emoji) {
                        messageText = jsonData.v.emoji;
                    }
                    // Handle array of objects with append operations
                    else if (Array.isArray(jsonData.v)) {
                        jsonData.v.forEach(item => {
                            if (item.o === 'append' && typeof item.v === 'string' && !item.p.includes('metadata')) {
                                messageText = item.v;
                            }
                        });
                    }
                    
                    
                    if (messageText) {
                        currentContent = currentContent + messageText;

                        currentMessageDiv.innerHTML = marked.parse(currentContent);
                        if (currentContent.includes("```")) {
                            const codeBlocks = currentMessageDiv.querySelectorAll("pre code");
                            codeBlocks.forEach((block) => {
                                hljs.highlightElement(block);
                                addCopyButton(block);
                            });

                            function addCopyButton(codeBlock) {
                                const button = document.createElement("button");
                                button.innerText = "Copy";
                                button.classList.add("copy-button");
                        
                                button.addEventListener("click", () => {
                                    const code = codeBlock.innerText;
                                    navigator.clipboard.writeText(code).then(() => {
                                        button.innerText = "Copied!";
                                        setTimeout(() => (button.innerText = "Copy"), 1500);
                                    });
                                });
                        
                                const wrapper = document.createElement("div");
                                wrapper.classList.add("code-wrapper");
                                codeBlock.parentNode.insertBefore(wrapper, codeBlock);
                                wrapper.appendChild(button);
                                wrapper.appendChild(codeBlock);
                            }                        
                        }

                        // messageContainer.scrollTop = messageContainer.scrollHeight;
                    }
                }
            }
        }
    } catch (error) {
        console.error('Error:', error);
        statusDiv.textContent = 'Disconnected';
        statusDiv.className = 'disconnected';
        
        if (currentMessageDiv) {
            currentMessageDiv.innerHTML += '\n\nError: Failed to connect to the server.';
        }
    }
}

messageInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        sendMessage();
    }
});