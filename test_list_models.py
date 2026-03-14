import google.generativeai as genai
GEMINI_API_KEY = "AIzaSyAbIl5EIhFOQ_GIW-iqi016kuG0slgbZJE"
genai.configure(api_key=GEMINI_API_KEY)
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
