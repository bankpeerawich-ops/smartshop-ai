def get_jaccard_similarity(str1, str2):
    a = set(str1.lower().split())
    b = set(str2.lower().split())
    if not a or not b: return 0
    return len(a.intersection(b)) / len(a.union(b))

def check(query, title):
    q_lower = query.lower()
    t_lower = title.lower()
    q_clean = q_lower.replace('"', '').strip()
    q_words = [w for w in q_clean.split() if len(w) > 1]
    
    brands = ["iphone", "samsung", "oppo", "vivo", "xiaomi", "realme", "sony", "hublot", "rolex", "nike", "adidas", "apple", "pixel", "ไอโฟน"]
    query_brands = [b for b in brands if b in q_clean]
    
    if query_brands:
        other_brands = [b for b in brands if b not in query_brands and b in t_lower]
        # Map "iphone" and "ไอโฟน" and "apple" as same
        eq = {"iphone", "ไอโฟน", "apple"}
        if any(b in query_brands for b in eq):
            other_brands = [b for b in other_brands if b not in eq]

        if other_brands:
            return "BLOCKED BY BRAND"

    if q_words:
        # Cross language check
        lang_map = {"ไอโฟน": "iphone", "iphone": "ไอโฟน"}
        matches = 0
        for w in q_words:
            if w in t_lower:
                matches += 1
            elif w in lang_map and lang_map[w] in t_lower:
                matches += 1
        
        score = matches / len(q_words)
        if score < 0.6: # Relaxed from 1.0
            return f"BLOCKED BY KEYWORD (Score: {score})"
            
    return "PASSED"

print(f"Iphone 15 vs Xiaomi: {check('iPhone 15', 'Xiaomi 15T')}")
print(f"Iphone 15 vs Apple iPhone 15: {check('iPhone 15', 'Apple iPhone 15 128GB')}")
print(f"ไอโฟน 15 vs Apple iPhone 15: {check('ไอโฟน 15', 'Apple iPhone 15 128GB')}")
