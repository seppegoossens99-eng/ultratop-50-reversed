"""Read a complete, dated Ultratop 50 Vlaanderen from the existing aCharts source."""
import json
import re
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

SOURCE = 'https://acharts.co/belgium_singles_top_50'
ROOT = Path(__file__).resolve().parent

def parse_chart(document, today=None):
    soup = BeautifulSoup(document, 'html.parser')
    table = soup.select_one('#ChartTable')
    if table is None:
        raise ValueError('Geen Ultratop-tabel gevonden; bestaande gegevens blijven behouden.')
    data=[]
    for row in table.select('tr[itemprop="itemListElement"]'):
        pos=row.select_one('[itemprop="position"]')
        title=row.select_one('.cPrinciple [itemprop="name"]')
        artist=row.select_one('.cPrinciple [itemprop="byArtist"] [itemprop="name"]')
        if not all((pos,title,artist)):
            raise ValueError('Onvolledige hitlijstregel')
        cells=row.find_all('td',recursive=False)
        position=int(pos.get_text(strip=True).rstrip('.'))
        previous=cells[1].get_text(' ',strip=True).strip('() ') if len(cells)>1 else ''
        peak=cells[4] if len(cells)>5 else None
        weeks=cells[5] if len(cells)>5 else None
        peak_text=peak.get_text(' ',strip=True) if peak else ''
        weeks_text=weeks.get_text(' ',strip=True) if weeks else ''
        # The cells also carry their column labels in responsive layouts.
        peak_match=re.search(r'\d+',peak_text)
        weeks_match=re.search(r'\d+',weeks_text)
        if not peak_match or not weeks_match:
            raise ValueError('Piekpositie of aantal weken ontbreekt')
        credits=[item.get_text(' ',strip=True) for item in row.select('.cPrinciple [itemprop="byArtist"] [itemprop="name"]')]
        data.append({'this_week':position,'last_week':int(previous) if previous.isdigit() else None,
                     'song':title.get_text(' ',strip=True),'artist':' & '.join(credits),'artists':credits,
                     'peak_position':int(peak_match.group()),'weeks_on_chart':int(weeks_match.group())})
    if len(data)!=50 or sorted(x['this_week'] for x in data)!=list(range(1,51)):
        raise ValueError('Geen volledige rangschikking van 1 tot 50')
    text=soup.get_text(' ',strip=True)
    match=re.search(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+20\d{2}\b',text)
    if not match:
        raise ValueError('Geen chartdatum gevonden')
    chart_date=datetime.strptime(match.group(),'%B %d, %Y').date()
    today=today or datetime.now(ZoneInfo('Europe/Brussels')).date()
    if not 0 <= (today-chart_date).days <= 16:
        raise ValueError('De bronhitlijst is verouderd of ligt in de toekomst')
    return {'date':chart_date.isoformat(),'source':SOURCE,'data':sorted(data,key=lambda x:x['this_week'],reverse=True)}

def load_chart():
    for attempt in range(3):
        try:
            response=requests.get(SOURCE,headers={'User-Agent':'Mozilla/5.0','Accept-Language':'nl-BE,nl;q=0.9,en;q=0.8'},timeout=40)
            response.raise_for_status()
            (ROOT/'chart_source.html').write_text(response.text,encoding='utf-8')
            chart=parse_chart(response.text)
            (ROOT/'chart_snapshot.json').write_text(json.dumps(chart,ensure_ascii=False,indent=2),encoding='utf-8')
            return chart
        except (requests.RequestException,ValueError):
            if attempt==2:
                raise
            time.sleep(3)
