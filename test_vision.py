import google.generativeai as genai
import sys

GEMINI_API_KEY = "AIzaSyAbIl5EIhFOQ_GIW-iqi016kuG0slgbZJE"
genai.configure(api_key=GEMINI_API_KEY)

try:
    model = genai.GenerativeModel("gemini-2.5-flash")
    print("Model initialized successfully")
except Exception as e:
    print(f"Error: {e}")
