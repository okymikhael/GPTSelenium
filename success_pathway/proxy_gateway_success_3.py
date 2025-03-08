import mitmproxy.http
import json
from mitmproxy import ctx
from collections.abc import Iterable


LOG_FILE = "network/dump.txt"  # Ensure this directory exists.
TARGET_URL_PATH = "https://chatgpt.com/backend-api/conversation"

class ProxyLogger:
    def __init__(self):
        pass

    def request(self, flow: mitmproxy.http.HTTPFlow) -> None:
        if TARGET_URL_PATH in flow.request.url and flow.request.method == "POST":
            request_data = {
                "type": "request",
                "timestamp": flow.request.timestamp_start,
                "method": flow.request.method,
                "url": flow.request.url,
                "headers": dict(flow.request.headers),
                "body": flow.request.get_text()[:500],
            }
            # self._log_data(request_data)
            
    def modify(self, data: bytes) -> bytes | Iterable[bytes]:
        self._log_data(data.decode().strip())
        return data

    def responseheaders(self, flow: mitmproxy.http.HTTPFlow):
        if TARGET_URL_PATH in flow.request.url and flow.request.method == "POST":
            content_type = flow.response.headers.get("content-type", "")
            ctx.log.info(f"responseheaders: content-type = {content_type}")
            if "text/event-stream" in content_type:
                # flow.response.stream = True  # Enable streaming mode.
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
            # if "text/event-stream" in content_type:
            #     response_data["note"] = "SSE response streamed in chunks."
            #     self._log_data(response_data)

    def _log_data(self, data):
        try:
            with open(LOG_FILE, "a") as f:
                f.write(f"{data} \n")
        except Exception as e:
            ctx.log.error(f"Failed to write to log file: {e}")

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
