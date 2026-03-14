from duckduckgo_search import DDGS
ddgs = DDGS()
results = list(ddgs.text("ช้อปปี้ iphone 17", max_results=2))
print(results)
