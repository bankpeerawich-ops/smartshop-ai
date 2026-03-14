import google.generativeai as genai
GEMINI_API_KEY = "AIzaSyAbIl5EIhFOQ_GIW-iqi016kuG0slgbZJE"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-flash-latest")
try:
    response = model.generate_content("Hello")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
