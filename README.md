# ChatGPT Web Proxy Gateway & API

A sophisticated web application that functions as a proxy gateway for intercepting, analyzing, and manipulating HTTP/HTTPS traffic. This solution provides a comprehensive user interface for monitoring and interacting with captured network data in real-time.

## Core Capabilities

- Enterprise-grade HTTP/HTTPS traffic interception and logging
- Interactive web dashboard for network traffic analysis and visualization
- RESTful API endpoints for programmatic access and integration
- Advanced browser automation via Selenium WebDriver

## Docker Deployment Instructions

### Prerequisites

**IMPORTANT:** Before running the application, you must add your ChatGPT cookies to the project:

1. Create a `cookies.txt` file in the project root directory
2. Format your cookies in Netscape/Mozilla format with tab-separated values:
   ```
   domain\tHTTP-only-flag\tpath\tsecure-flag\texpiration\tname\tvalue
   ```
   Example:
   ```
   .openai.com\tTRUE\t/\tTRUE\t1718486400\t_puid\tyour-cookie-value
   ```

3. Run the application with Docker Compose:
   ```bash
   docker-compose up -d
   ```

4. Access the dashboard at http://localhost:8000

### Docker Compose Services

- **app**: Main FastAPI application with Selenium browser automation
- **redis**: Cache for chat interactions
- **proxy**: mitmproxy service for intercepting ChatGPT traffic

## Manual Deployment Instructions

1. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Initialize the proxy server:
   ```bash
   mitmproxy -s proxy_gateway.py
   ```
   or for headless operation:
   ```bash
   mitmdump -s proxy_gateway.py
   ```

3. Launch the application server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

4. Access the dashboard at http://localhost:8000

## System Configuration

- Proxy configuration parameters are defined in `proxy_gateway.py`
- Application server settings are managed in `main.py`
- Authentication cookies can be imported from `cookies.txt`
- Network traffic logs are stored in `network/dump.txt`

## Development Roadmap

- [x] Core proxy functionality implementation
- [x] Web interface and dashboard development
- [ ] Secure file upload and management system
- [ ] Media content preview and analysis tools
- [ ] OAuth 2.0 authentication integration
- [ ] Enterprise data persistence with PostgreSQL (30-day retention)

## Architecture Overview

This solution leverages a modern technology stack:
- **mitmproxy**: Enterprise-grade traffic interception and analysis
- **FastAPI/Uvicorn**: High-performance asynchronous web server
- **Selenium WebDriver**: Advanced browser automation and testing
- **Modern frontend**: Responsive HTML5/CSS3/JavaScript interface

## License

Proprietary software. All rights reserved.