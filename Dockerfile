FROM python:3.10-slim

WORKDIR /app

# Install Chrome dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    libxss1 \
    libnss3 \
    libglib2.0-0 \
    libfontconfig1 \
    libxrender1 \
    libasound2 \
    libxtst6 \
    libxcursor1 \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /tmp/downloads \
    && chmod -R 777 /tmp/downloads \
    && mkdir -p /tmp/.X11-unix \
    && chmod 1777 /tmp/.X11-unix

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY proxy_gateway.py .

# Copy chromedriver (will be mounted as volume in docker-compose)
# COPY chromedriver .
# RUN chmod +x /app/chromedriver

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV REDIS_HOST=redis
ENV PROXY_HOST=proxy
ENV PROXY_PORT=8080
ENV DISPLAY=:99

# Create a script to start Xvfb and then run the application
RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1920x1080x24 -ac &\nsleep 1\nuvicorn main:app --host 0.0.0.0 --port 8000' > /app/start.sh \
    && chmod +x /app/start.sh

# Run the application with Xvfb
CMD ["/app/start.sh"]