import google.generativeai as genai

GEMINI_API_KEY = "AIzaSyAbIl5EIhFOQ_GIW-iqi016kuG0slgbZJE"
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")
prompt = """Analyze this image and identify the 1-4 key shoppable items (e.g. shoes, pants, shirt, bag).
Return a JSON array of strings, where each string is a highly specific search query in Thai for that item.
Example: ["รองเท้าผ้าใบ New Balance 530", "กระเป๋าสะพายข้างสีดำ", "กางเกงสแล็คผู้หญิงสีครีม", "เสื้อยืดสีขาว"]
Do not return markdown formatting, just the raw JSON array.
"""

with open('dummy.jpg', 'w') as f:
    f.write('dummy')
try:
    f = genai.upload_file('dummy.jpg')
    print("Failed")
except Exception as e:
    # Actually I need a real image to test... nevermind.
    pass
