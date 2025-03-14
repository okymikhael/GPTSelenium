import mitmproxy.http
import json
import redis
import os
from mitmproxy import ctx
from collections.abc import Iterable
import asyncio
import websockets

# Initialize WebSocket client
app_host = os.environ.get('APP_HOST', 'localhost')
app_port = os.environ.get('APP_PORT', '8000')
ws_url = f"ws://{app_host}:{app_port}/ws"
ws_client = None
ws_lock = asyncio.Lock()  # Add lock for thread-safe WebSocket operations

LOG_FILE = "network/dump.txt"  # Ensure this directory exists.
TARGET_URL_PATH = "https://chatgpt.com/backend-api/conversation"

# Initialize Redis client
redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_client = redis.Redis(host=redis_host, port=6379, db=0)

class ProxyLogger:
    def __init__(self):
        chat_interaction = None
        pass

    def request(self, flow: mitmproxy.http.HTTPFlow) -> None:
        if TARGET_URL_PATH in flow.request.url and flow.request.method == "POST":
            try:
                request_body = json.loads(flow.request.get_text())
                if 'messages' in request_body:
                    for message in request_body['messages']:
                        content = message.get('content', {})
                        if isinstance(content, dict) and 'parts' in content:
                            for part in content['parts']:
                                if "[ignore-this-code:" in part:
                                    chat_id = part.split(':')[1].split(']')[0]
                                    redis_key = f"chat:interaction:{chat_id}"

                                    # Check if chat interaction exists in Redis
                                    if redis_client.exists(redis_key):
                                        # # Store message ID in Redis
                                        # message_id = request_body['messages'][0]['id']
                                        # redis_client.set(redis_key, message_id)
                                        # Retrieve chat interaction from Redis
                                        self.chat_interaction = chat_id
                                        ctx.log.info(f"chat: {self.chat_interaction}")
                                
            except json.JSONDecodeError:
                ctx.log.error("Failed to parse request JSON")

    async def send_to_websocket(self, chat_id: str, data: str):
        global ws_client, ws_lock
        async with ws_lock:  # Ensure thread-safe WebSocket operations
            try:
                async with websockets.connect(ws_url) as ws:
                    ctx.log.info(f"Sending Chunk...")
                    await ws.send(f"{chat_id}:data: {data}")
            except Exception as e:
                ctx.log.error(f"WebSocket error: {e}")
                
    # async def send_to_websocket(self, chat_id: str, data: str):
    #     global ws_client, ws_lock
    #     async with ws_lock:  # Ensure thread-safe WebSocket operations
    #         try:
    #             if ws_client is None or ws_client.closed:  # Corrected: No 'await' needed
    #                 ws_client = await websockets.connect(ws_url)
    #             await ws_client.send(f"{chat_id}:data: {data}")
    #             ctx.log.info(f"Successfully sent chunk to WebSocket")
    #         except Exception as e:
    #             ctx.log.error(f"WebSocket error: {e}")
    #             if ws_client:
    #                 try:
    #                     await ws_client.close()
    #                 except:
    #                     pass
    #             ws_client = None  # Reset connection if an error occurs

    def modify(self, data: bytes) -> bytes | Iterable[bytes]:
        asyncio.create_task(self.send_to_websocket(self.chat_interaction, data.decode('utf-8')))
        return data

    def responseheaders(self, flow: mitmproxy.http.HTTPFlow):
        if TARGET_URL_PATH in flow.request.url and flow.request.method == "POST":
            content_type = flow.response.headers.get("content-type", "")
            ctx.log.info(f"responseheaders: content-type = {content_type}")
            if "text/event-stream" in content_type:
                flow.response.stream = self.modify
                ctx.log.info(f"SSE streaming enabled for: {flow.request.url}")

    def response(self, flow: mitmproxy.http.HTTPFlow) -> None:
        if TARGET_URL_PATH in flow.request.url and flow.request.method == "POST":
            response_data = {
                "type": "response",
                "timestamp": flow.response.timestamp_end,
                "status_code": flow.response.status_code,
                "url": flow.request.url,
                "headers": dict(flow.response.headers),
            }
            content_type = flow.response.headers.get("content-type", "")
            if "text/event-stream" in content_type:
                response_data["note"] = "SSE response streamed in chunks."
                # self._log_data(response_data)

    # def _log_data(self, data):
    #     try:
    #         with open(LOG_FILE, "a") as f:
    #             f.write(f"{json.dumps(data)} \n")
    #     except Exception as e:
    #         ctx.log.error(f"Failed to write to log file: {e}")

# Instantiate the addon.
proxy_logger = ProxyLogger()

def start():
    return proxy_logger

def request(flow: mitmproxy.http.HTTPFlow):
    proxy_logger.request(flow)

def responseheaders(flow: mitmproxy.http.HTTPFlow):
    proxy_logger.responseheaders(flow)

def response(flow: mitmproxy.http.HTTPFlow):
    proxy_logger.response(flow)