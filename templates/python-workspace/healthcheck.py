import os
import urllib.request
from urllib.parse import urlsplit

request = urllib.request.Request("http://127.0.0.1:8000/api/health", headers={"Host": urlsplit(os.environ.get("APP_ORIGIN", "http://127.0.0.1:8000")).netloc})
with urllib.request.urlopen(request, timeout=3) as response:
    assert response.status == 200
