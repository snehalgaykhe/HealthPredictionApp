
import json
import pathlib
import tomllib
import urllib.error
import urllib.request

secrets_path = pathlib.Path.home() / ".streamlit" / "secrets.toml"
secrets = tomllib.loads(secrets_path.read_text(encoding="utf-8"))
api_key = secrets["GEMINI_API_KEY"]

url = (
    "https://generativelanguage.googleapis.com/v1beta/"
   "models/gemini-3.6-flash:generateContent"
)

payload = {
    "contents": [
        {
            "parts": [
                {"text": "Reply with exactly: Gemini connection successful"}
            ]
        }
    ]
}

request = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    },
    method="POST",
)

try:
    with urllib.request.urlopen(request, timeout=30) as response:
        print("HTTP status:", response.status)
        data = json.loads(response.read().decode("utf-8"))
        print(json.dumps(data, indent=2)[:2000])

except urllib.error.HTTPError as error:
    print("HTTP status:", error.code)
    print(error.read().decode("utf-8")[:2000])

except Exception as error:
    print(type(error).__name__ + ":", str(error))
