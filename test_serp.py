import requests
import json

SERPAPI_KEY = "8b6b6adcf2ca95393292d6e065a93d20ce384357f91bba4028e5eca717770c66"
params = {
    "engine": "google_shopping",
    "gl": "th",
    "hl": "th",
    "q": "ไอโฟน 15",
    "api_key": SERPAPI_KEY
}

response = requests.get("https://serpapi.com/search.json", params=params)
if response.status_code == 200:
    data = response.json()
    with open('serp_output.json', 'w') as f:
        json.dump(data.get("shopping_results", [])[:5], f, indent=2, ensure_ascii=False)
    print("Success")
else:
    print("Error:", response.status_code, response.text)
