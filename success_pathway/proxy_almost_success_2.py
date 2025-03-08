import mitmproxy.http
import json
from mitmproxy import ctx
from mitmproxy import options
from mitmproxy.net import tls

# Define the file where we'll log all requests and responses
LOG_FILE = "network/file.json"  # Ensure the path is correct
TARGET_URL_PATH = "https://chatgpt.com/backend-api/conversation"  # Filter by specific URL path

class ProxyLogger:
    def __init__(self):
        self.counter = 0

    def request(self, flow: mitmproxy.http.HTTPFlow) -> None:
        # Check if the request is to the target URL path and it's a POST request
        if TARGET_URL_PATH == flow.request.url and flow.request.method == "POST":
            # Log request details here
            request_data = {
                "type": "request",
                "timestamp": flow.request.timestamp_start,
                "method": flow.request.method,
                "url": flow.request.url,
                "headers": dict(flow.request.headers),
                "body": flow.request.get_text()[:500],  # Capture the first 500 chars for brevity
            }
            self._log_data(request_data)

    def responseheaders(self, flow: mitmproxy.http.HTTPFlow):
        """
        Called after the response headers have been received.
        If it's an SSE response, enable streaming so we can capture chunks in real time.
        """
        if TARGET_URL_PATH == flow.request.url and flow.request.method == "POST":
            content_type = flow.response.headers.get("content-type", "")
            if content_type.startswith("text/event-stream"):
                flow.response.stream = True  # Enable streaming mode
                ctx.log.info(f"SSE streaming enabled for: {flow.request.url}")

    def responsechunk(self, flow: mitmproxy.http.HTTPFlow, chunk: bytes) -> bytes:
        """
        Called for each chunk of the response body when streaming is enabled.
        We can log or process the chunk here in real time.
        """
        if TARGET_URL_PATH == flow.request.url and flow.request.method == "POST":
            # Convert chunk to string
            chunk_str = chunk.decode("utf-8", errors="replace")
            self._log_data({"event_chunk": chunk_str})

        # Return the chunk unmodified (or modify if needed)
        return chunk

    def response(self, flow: mitmproxy.http.HTTPFlow) -> None:
        # Check if the response is for the target URL path and a POST request
        if TARGET_URL_PATH == flow.request.url and flow.request.method == "POST":
            # Log response details here
            response_data = {
                "type": "response",
                "timestamp": flow.response.timestamp_end,
                "status_code": flow.response.status_code,
                "url": flow.request.url,
                "headers": dict(flow.response.headers),
            }

            # Handle SSE (Server-Sent Events) stream
            if flow.response.headers.get("content-type", "").startswith("text/event-stream"):
                # Capture the live SSE events in real-time
                response_data["event_stream"] = self._capture_event_stream(flow)
            else:
                # If not SSE, log response body (e.g., for normal HTTP responses)
                response_data["body"] = flow.response.get_text()[:500]  # Capture the first 500 chars

            self._log_data(response_data)

    def _capture_event_stream(self, flow: mitmproxy.http.HTTPFlow):
        # Capture the SSE event stream live by continuously appending each chunk
        event_stream = []
        try:
            # We will manually read the response body in chunks
            body = flow.response.content.decode("utf-8")  # Decode entire content of the response
            for chunk in body.split("\n"):
                if chunk.strip():  # Ignore empty lines
                    event_stream.append(chunk)  # Append each event chunk

                    # Log each chunk directly to the file as it arrives
                    self._log_data({"event_chunk": chunk})

        except Exception as e:
            ctx.log.error(f"Error capturing SSE stream: {e}")
        return event_stream
    
    def _log_data(self, data):
        # Log the data to the JSON file continuously
        try:
            with open(LOG_FILE, "a") as f:
                json.dump(data, f)
                f.write("\n")  # Write each entry on a new line
        except Exception as e:
            ctx.log.error(f"Failed to write to log file: {e}")

# Instantiate the ProxyLogger class
proxy_logger = ProxyLogger()

def start():
    """
    mitmproxy will call 'start()' to register this addon.
    """
    return proxy_logger

def responseheaders(flow: mitmproxy.http.HTTPFlow):
    """
    Global hook that calls our addon's responseheaders method.
    """
    proxy_logger.responseheaders(flow)

def responsechunk(flow: mitmproxy.http.HTTPFlow, chunk: bytes) -> bytes:
    """
    Global hook that calls our addon's responsechunk method for each chunk.
    """
    return proxy_logger.responsechunk(flow, chunk)

def response(flow: mitmproxy.http.HTTPFlow) -> None:
    proxy_logger.response(flow)