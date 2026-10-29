import requests
from bs4 import BeautifulSoup

URLS = [
    "https://acharts.co/belgium_singles_top_50",
    "https://www.ultratop.be/nl/ultratop50",
]
for url in URLS:
    print(f"\n=== {url} ===", flush=True)
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; ChartChecker/1.0)"}, timeout=30)
        print("HTTP status:", r.status_code)
        print("Final URL:", r.url)
        print("Content length:", len(r.content))
        if r.ok:
            soup = BeautifulSoup(r.text, "lxml")
            print("Title:", soup.title.get_text(" ", strip=True) if soup.title else "(none)")
            print("Page excerpt:", soup.get_text(" ", strip=True)[:1800])
        else:
            print("Access denied or page unavailable")
    except requests.RequestException as exc:
        print("Request failed:", exc)
print("\nTEST COMPLETED")
