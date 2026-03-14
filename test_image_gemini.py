import google.generativeai as genai
import sys

GEMINI_API_KEY = "AIzaSyAbIl5EIhFOQ_GIW-iqi016kuG0slgbZJE"
genai.configure(api_key=GEMINI_API_KEY)

try:
    with open('dummy.jpg', 'w') as f:
        f.write('dummy')
        pass
    gemini_file = genai.upload_file('dummy.jpg')
    model = genai.GenerativeModel("gemini-2.5-flash") # Wait, 2.5 flash
    prompt = "Identify this product exactly."
    response = model.generate_content([gemini_file, prompt])
    print(response.text)
except Exception as e:
    import traceback
    traceback.print_exc()
