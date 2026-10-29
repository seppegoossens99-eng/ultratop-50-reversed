import requests
from bs4 import BeautifulSoup
url = "https://acharts.co/belgium_singles_top_50"
r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=30)
r.raise_for_status()
soup = BeautifulSoup(r.text, "lxml")
print("Page:", soup.title.get_text(" ", strip=True))
for i, table in enumerate(soup.select("table")):
    print(f"TABLE {i}: class={table.get('class')} id={table.get('id')} rows={len(table.select('tr'))}")
    for row in table.select("tr")[:3]:
        print("ROW HTML:", str(row)[:3500])
print("TEST COMPLETE")
