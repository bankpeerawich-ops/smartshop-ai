import google.generativeai as genai
import json

GEMINI_API_KEY = "AIzaSyAbIl5EIhFOQ_GIW-iqi016kuG0slgbZJE"
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")
gemini_file = genai.upload_file("Cat03.jpg")
prompt = """
Identify the key objects in this image.
Return a valid JSON array of objects. Each object must have:
"label": a short Thai description (e.g. "แมว", "ปลอกคอ")
"search_query": a specific Thai search query for shopping (e.g. "ปลอกคอแมวสีแดง")
"box": [ymin, xmin, ymax, xmax] where values are 0-1000
"""
response = model.generate_content([gemini_file, prompt])
print(response.text)
