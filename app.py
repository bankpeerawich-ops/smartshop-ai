import json
import hashlib
import sqlite3
import datetime
from flask import Flask, request, jsonify, send_from_directory, session
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import tempfile
import google.generativeai as genai
import psycopg2
from psycopg2.extras import RealDictCursor

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyAX_tMW8cdF_OvQdIY08gpAIcdYscK4eis")
genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__, static_url_path='', static_folder='.')
app.secret_key = os.environ.get('SECRET_KEY', 'smartshop_super_secret_key_123')

DATABASE_URL = os.environ.get('DATABASE_URL') # Set this on Render/Supabase

DATABASE = 'database.db'

def get_db_connection():
    if DATABASE_URL:
        # PostgreSQL (Production)
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        # SQLite (Local)
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    if DATABASE_URL:
        # PostgreSQL Syntax
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                query TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        # SQLite Syntax
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                query TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
    conn.commit()
    conn.close()

try:
    init_db()
except Exception as e:
    print(f"[WARNING] Could not init DB on startup: {e}")

import requests

SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "8b6b6adcf2ca95393292d6e065a93d20ce384357f91bba4028e5eca717770c66")

# In-memory "database" to store recent search groups so we can fetch them by ID later
RECENT_SEARCH_CACHE = {}

def get_jaccard_similarity(str1, str2):
    a = set(str1.lower().split())
    b = set(str2.lower().split())
    if not a or not b:
        return 0
    return len(a.intersection(b)) / len(a.union(b))

def fetch_serpapi(query):
    params = {
        "engine": "google_shopping",
        "gl": "th",
        "hl": "th",
        "q": query,
        "api_key": SERPAPI_KEY
    }
    
    q_lower = query.lower()
    accessories = ["เคส", "case", "ฟิล์ม", "film", "กระจก", "สายชาร์จ", "charger", "ซิลิโคน", "silicone", "ปก", "cover", "หัวชาร์จ", "อะแดปเตอร์", "adapter", "battery", "แบต", "สายนาฬิกา", "ขาตั้ง", "mount", "strap", "สายคล้อง", "box only", "กล่องเปล่า", "ถุง", "bag only", "กางเกง", "เสื้อ", "รองเท้า"] # Expanded
    # If query specifically contains an accessory, don't filter it
    is_acc_query = any(acc in q_lower for acc in accessories)
    
    try:
        response = requests.get("https://serpapi.com/search.json", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        shopping_results = data.get("shopping_results", [])
        
        products = []
        for i, item in enumerate(shopping_results):
            title = item.get("title", "")
            t_lower = title.lower()
            
            # Anti-accessories filter
            if not is_acc_query:
                is_acc_item = any(acc in t_lower for acc in accessories)
                if is_acc_item: continue
            
            extracted_price = item.get("extracted_price", 0)
            if not extracted_price:
                continue
                
            # Original exact store name
            source = item.get("source", "Store")
            link = item.get("link", item.get("product_link", ""))
            thumbnail = item.get("thumbnail", "")
            rating = item.get("rating", 4.0)
            if not isinstance(rating, (int, float)):
                rating = 4.0
                
            # Stricter Keyword Matching
            q_clean = q_lower.replace('"', '').strip()
            q_words = [w for w in q_clean.split() if len(w) > 1]
            
            # --- BRAND GUARDIAN ---
            # Added Thai and common variations
            brands = ["iphone", "samsung", "oppo", "vivo", "xiaomi", "realme", "sony", "hublot", "rolex", "nike", "adidas", "apple", "pixel", "ไอโฟน", "ซัมซุง"]
            query_brands = [b for b in brands if b in q_clean]
            
            if query_brands:
                other_brands = [b for b in brands if b not in query_brands and b in t_lower]
                
                # Equivalence set for Apple
                apple_set = {"iphone", "ไอโฟน", "apple", "ipad", "macbook", "airpods"}
                if any(b in query_brands for b in apple_set):
                    # Filter out other apple keywords from 'other_brands' to avoid self-blocking
                    other_brands = [b for b in other_brands if b not in apple_set]

                if other_brands:
                    continue # Strictly block foreign brands (e.g. Xiaomi in iPhone search)

                # Ensure at least some brand context is kept
                is_apple_q = any(b in query_brands for b in apple_set)
                if is_apple_q:
                    if not any(b in t_lower for b in apple_set):
                        continue
                else:
                    if not any(b in t_lower for b in query_brands):
                        continue
            
            # --- KEYWORD SENTINEL (Cross-language aware) ---
            if q_words:
                lang_map = {"ไอโฟน": "iphone", "iphone": "ไอโฟน", "ซัมซุง": "samsung", "samsung": "ซัมซุง"}
                matches = 0
                for w in q_words:
                    if w in t_lower:
                        matches += 1
                    elif w in lang_map and lang_map[w] in t_lower:
                        matches += 1
                
                # Relaxed matching for general goods (like snacks), strict for high-value brands
                is_high_value = any(b in query_brands for b in ["iphone", "samsung", "ps5", "rolex", "apple"])
                threshold = 0.6 if is_high_value else 0.3 # 30% match is enough for general items
                
                if matches / len(q_words) < threshold:
                    continue
            
            # Price Heuristic for Electronics (High-value items)
            # If search is for a phone/tablet/laptop, prices < 5000 are likely accessories
            electronic_keywords = ["iphone", "ipad", "macbook", "samsung", "galaxy", "laptop", "tablet", "watch", "ultra", "ps5", "nintendo"]
            if any(k in q_lower for k in electronic_keywords) and extracted_price < 4000:
                if not is_acc_query:
                    continue

            # Determine if official/trusted
            source_lower = source.lower()
            is_official = False
            official_keywords = ["mall", "official", "banana", "jib", "advice", "power buy", "studio7", "apple", "istudio", "it city", "mercular", "samsung", "lotus", "big c", "tops", "makro", "7-eleven", "watson", "boots"]
            if any(k in source_lower for k in official_keywords) or (source_lower in ["shopee", "lazada", "tiktok"] and item.get("rating", 0) >= 4.5):
                is_official = True
                
            found = False
            for p in products:
                # Grouping logic: Check if titles are similar or both contain the core query
                sim = get_jaccard_similarity(title, p['name'])
                
                # Check if they share the same brand and model (approx)
                p_name_lower = p['name'].lower()
                
                # 1. High similarity match
                is_similar = sim >= 0.3 # Relaxed from 0.35
                
                # 2. Key identifiers match (e.g. if both have "iphone 15" and "128gb")
                key_match = False
                important_specs = ["128gb", "256gb", "512gb", "1tb", "pro", "max", "ultra", "plus"]
                specs_in_q = [s for s in important_specs if s in q_lower]
                if specs_in_q:
                    # If query has specs, both must have those specs to group
                    if all(s in t_lower for s in specs_in_q) and all(s in p_name_lower for s in specs_in_q):
                        # and they must share the brand
                        shared_brands = [b for b in brands if b in t_lower and b in p_name_lower]
                        if shared_brands:
                            key_match = True
                
                if is_similar or key_match:
                    p['listings'].append({
                        'title': title,
                        'platform': source,
                        'price': extracted_price,
                        'rating': rating,
                        'link': link,
                        'is_official': is_official
                    })
                    # Update representative image if current product image is missing
                    if not p['image'] and thumbnail:
                        p['image'] = thumbnail
                    found = True
                    break
                    
            if not found:
                pid = f"serp_{len(products)}_{hash(title) % 10000}"
                new_prod = {
                    'id': pid,
                    'name': title,
                    'category': 'live_search',
                    'image': thumbnail,
                    'tags': [query],
                    'listings': [{
                        'title': title, # Keep exact name from store
                        'platform': source,
                        'price': extracted_price,
                        'rating': rating,
                        'link': link,
                        'is_official': is_official
                    }]
                }
                products.append(new_prod)
                
        return products
    except Exception as e:
        print(f"SerpAPI Error: {e}")
        return []

def ai_understand_query(query):
    q = query.lower().strip()
    if not q:
        return {'base': '', 'expansions': []}

    knowledge_base = {
        'airpods': {
            'base': 'AirPods',
            'expansions': ['AirPods Pro', 'AirPods 3rd Gen', 'หูฟัง Apple']
        },
        'nike': {
            'base': 'Nike Shoes',
            'expansions': ['Nike Air Force', 'Nike Dunk', 'รองเท้าวิ่ง']
        },
        'air force': {
            'base': 'Nike Air Force',
            'expansions': ['Air Force 1', 'AF1 White', 'รองเท้าผ้าใบ']
        },
        'iphone': {
            'base': 'iPhone',
            'expansions': ['iPhone 15', 'iPhone 15 Pro', 'iPhone 15 128GB']
        },
        'ไอโฟน': {
            'base': 'iPhone',
            'expansions': ['iPhone 15', 'iPhone 15 Pro Max', 'Apple iPhone']
        },
        'ps5': {
            'base': 'PlayStation 5',
            'expansions': ['PS5 Disc Edition', 'PS5 Console', 'เครื่องเกม Sony']
        },
        'เกม': {
            'base': 'Gaming Console',
            'expansions': ['PlayStation 5', 'Nintendo Switch', 'Xbox']
        }
    }

    for key, val in knowledge_base.items():
        if key in q or q in key:
            return val

    # Generic expansion for unknown queries
    return {
        'base': query,
        'expansions': [f'{query} รุ่นใหม่ล่าสุด', f'{query} ราคาถูก', f'รีวิว {query}']
    }

def ai_recommend_deal(product):
    if not product or not product.get('listings'):
        return None

    listings = product['listings']
    best_listing = listings[0]
    
    # Heuristic: base score on rating and price, with a large bonus for official/trusted stores
    def calc_score(listing):
        # Prevent division by zero, prioritize lower price. 
        # Price is typically 100-50000. 
        price_factor = 100000 / max(listing['price'], 1) 
        rating_factor = listing['rating'] * 10
        official_bonus = 500 if listing.get('is_official') else 0
        return price_factor + rating_factor + official_bonus

    score = calc_score(best_listing)

    for i in range(1, len(listings)):
        listing = listings[i]
        current_score = calc_score(listing)
        if current_score > score:
            score = current_score
            best_listing = listing

    lowest_price_listing = min(listings, key=lambda x: x['price'])
    
    if best_listing.get('is_official'):
        if best_listing['price'] == lowest_price_listing['price']:
            reason_text = "เป็นร้านค้าทางการ (Official/Trusted) ที่ขายถูกที่สุด มั่นใจได้ 100%"
        else:
            reason_text = "แนะนำร้านค้าทางการ (Official) ที่มีความน่าเชื่อถือสูง แม้ราคาจะไม่ใช่ระดับต่ำสุดแต่คุ้มค่าความเสี่ยง"
    elif best_listing['price'] == lowest_price_listing['price']:
        reason_text = "ราคาถูกที่สุดเมื่อเทียบกับทุกร้านที่พบ"
    else:
        reason_text = "คะแนนร้านค้าดีเยี่ยมและราคาคุ้มค่าที่สุด"

    result = dict(best_listing)
    result['reason'] = reason_text
    return result

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

import random

@app.route('/api/trending', methods=['GET'])
def get_trending():
    # Live randomized trending data
    queries = ["สมาร์ทโฟน", "หูฟังไร้สาย", "รองเท้าผ้าใบ", "นาฬิกาสมาร์ทวอทช์", "แท็บเล็ต", "กระเป๋าแบรนด์เนม", "กล้องดิจิตอล", "เครื่องชงกาแฟ", "ทีวี 4K", "เครื่องฟอกอากาศ"]
    q = random.choice(queries)
    results = fetch_serpapi(q)
    
    if not results:
        return jsonify([])
        
    # Shuffle the top results and return up to 4
    trending_items = results[:8]
    random.shuffle(trending_items)
    return jsonify(trending_items[:4])

@app.route('/api/search', methods=['GET'])
def search_products():
    query = request.args.get('q', '').strip()
    
    # Save search history if user is logged in
    user_id = session.get('user_id')
    if user_id and query:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('INSERT INTO search_history (user_id, query) VALUES (?, ?)', (user_id, query))
        conn.commit()
        conn.close()
        
    # 1. Get AI Expansions
    ai_insight = ai_understand_query(query)
    
    # 2. Live SerpAPI Fetch
    results = fetch_serpapi(query)
    
    # If the direct query yielded too few results and we have an AI expansion, 
    # we could theoretically search the expansion too, but for speed, let's stick to the direct query results.
    
    # Cache the results to support the /compare/id endpoint
    for r in results:
        RECENT_SEARCH_CACHE[r['id']] = r
        
    return jsonify({
        'insight': ai_insight,
        'results': results,
        'fallback': results[0] if results else None
    })

@app.route('/api/product/<product_id>', methods=['GET'])
def get_product(product_id):
    product = RECENT_SEARCH_CACHE.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
        
    recommendation = ai_recommend_deal(product)
    
    return jsonify({
        'product': product,
        'recommendation': recommendation
    })

# --- Image Vision Endpoint ---
@app.route('/api/upload-image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'ไม่พบไฟล์รูปภาพ'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'ไฟล์รูปภาพไม่ถูกต้อง'}), 400
        
    try:
        import PIL.Image as PILImage
        import io

        # Read image bytes directly for PIL (no file.save needed first)
        img_bytes = file.read()
        img = PILImage.open(io.BytesIO(img_bytes))

        # Save temp copy for cleanup purposes
        temp_dir = tempfile.gettempdir()
        filename = secure_filename(file.filename) if file.filename else "upload.jpg"
        temp_path = os.path.join(temp_dir, filename)
        img.save(temp_path)

        
        # Using gemini-flash-latest for better quota stability
        model = genai.GenerativeModel("gemini-flash-latest")
        prompt = """Analyze this image and identify shoppable items.
CRITICAL RULES:
1. If the image is a product shot of a single item (e.g. a bag of snacks, a phone, a box), identify it as ONE SINGLE object representing the whole product. Do NOT identify parts of the packaging (like logos, small drawings, or nutritional info) as separate items.
2. If the image is a lifestyle photo (e.g. a model wearing multiple things), identify the 1-5 most prominent shoppable items (shirt, pants, bag, etc.).
3. Each object MUST be a realistic category for shopping.
4. If it is one clear product, return an array with exactly ONE object.

Return ONLY a valid JSON array of objects. Do not wrap it in markdown.
Each object must have:
"label": short Thai name (e.g. "ยำยำช้างน้อย รสข้าวโพด")
"query": specific Thai search query for this exact item
"cheaper_query": Thai search query for a similar look but cheaper alternative (optional)
"box": [ymin, xmin, ymax, xmax] 0-1000 integers.
"""
        # Pass image directly as PIL object
        response = model.generate_content([img, prompt])
        
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
            text = text[:text.rfind("```")]
        elif text.startswith("```"):
            text = text[3:]
            text = text[:text.rfind("```")]
            
        try:
            items = json.loads(text.strip())
            if not isinstance(items, list):
                items = [items]
        except json.JSONDecodeError:
            # Fallback if json fails
            items = [{"label": "สินค้าที่พบ", "query": response.text[:80], "box": [0,0,1000,1000]}]
        
        os.remove(temp_path)
        
        return jsonify({'items': items})
        
    except Exception as e:
        print(f"Vision API Error: {e}")
        return jsonify({'error': f'เกิดข้อผิดพลาดในการวิเคราะห์รูปภาพ: {str(e)}'}), 500

# --- Authentication & History Endpoints ---

def save_search_history(user_id, query):
    """Save a search query to history (works with both SQLite and PostgreSQL)."""
    try:
        conn = get_db_connection()
        if DATABASE_URL:
            c = conn.cursor()
            c.execute('INSERT INTO search_history (user_id, query) VALUES (%s, %s)', (user_id, query))
        else:
            c = conn.cursor()
            c.execute('INSERT INTO search_history (user_id, query) VALUES (?, ?)', (user_id, query))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[History] Could not save: {e}")

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({'error': 'กรุณากรอกชื่อผู้ใช้และรหัสผ่าน'}), 400
    if len(username) < 3:
        return jsonify({'error': 'ชื่อผู้ใช้ต้องมีอย่างน้อย 3 ตัวอักษร'}), 400
    if len(password) < 6:
        return jsonify({'error': 'รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร'}), 400
        
    hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
    
    try:
        conn = get_db_connection()
        if DATABASE_URL:
            c = conn.cursor()
            c.execute('INSERT INTO users (username, password) VALUES (%s, %s)', (username, hashed_pw))
        else:
            c = conn.cursor()
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_pw))
        conn.commit()
        conn.close()
        return jsonify({'message': 'สมัครสมาชิกสำเร็จ!'})
    except Exception as e:
        err = str(e).lower()
        if 'unique' in err or 'duplicate' in err:
            return jsonify({'error': 'ชื่อผู้ใช้นี้มีอยู่ในระบบแล้ว'}), 400
        return jsonify({'error': f'เกิดข้อผิดพลาด: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({'error': 'กรุณากรอกชื่อผู้ใช้และรหัสผ่าน'}), 400

    try:
        conn = get_db_connection()
        if DATABASE_URL:
            c = conn.cursor(cursor_factory=RealDictCursor)
            c.execute('SELECT * FROM users WHERE username = %s', (username,))
        else:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE username = ?', (username,))
        
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return jsonify({'message': 'เข้าสู่ระบบสำเร็จ!', 'username': user['username']})
        else:
            return jsonify({'error': 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง'}), 401
    except Exception as e:
        return jsonify({'error': f'เกิดข้อผิดพลาด: {str(e)}'}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return jsonify({'message': 'ออกจากระบบเรียบร้อย'})

@app.route('/api/user', methods=['GET'])
def get_user():
    user_id = session.get('user_id')
    if user_id:
        return jsonify({'logged_in': True, 'username': session.get('username')})
    return jsonify({'logged_in': False})

@app.route('/api/history', methods=['GET'])
def get_history():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'กรุณาเข้าสู่ระบบก่อน'}), 401
        
    try:
        conn = get_db_connection()
        if DATABASE_URL:
            c = conn.cursor(cursor_factory=RealDictCursor)
            c.execute('''
                SELECT query, MAX(timestamp) as ts 
                FROM search_history 
                WHERE user_id = %s 
                GROUP BY query 
                ORDER BY ts DESC 
                LIMIT 10
            ''', (user_id,))
        else:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('''
                SELECT query, MAX(timestamp) as ts 
                FROM search_history 
                WHERE user_id = ? 
                GROUP BY query 
                ORDER BY ts DESC 
                LIMIT 10
            ''', (user_id,))
        
        history = c.fetchall()
        conn.close()
        return jsonify([row['query'] for row in history])
    except Exception as e:
        return jsonify([])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
