import requests
from bs4 import BeautifulSoup

url = "https://www.ultratop.be/nl/ultratop50"
response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
response.raise_for_status()
soup = BeautifulSoup(response.text, "lxml")
print("Paginatitel:", soup.title.get_text(" ", strip=True) if soup.title else "geen")
print("Aantal tabellen:", len(soup.select("table")))
print("Aantal links:", len(soup.select("a")))
for table in soup.select("table")[:3]:
    print("\nTABEL:")
    print(table.get_text(" | ", strip=True)[:1500])
print("\nTEST KLAAR")
