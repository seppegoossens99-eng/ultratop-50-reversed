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

def validate_chart(chart, today=None, max_age=16):
    """Validate both parsed pages and stored snapshots before they can be used."""
    if not isinstance(chart, dict) or chart.get('source') != SOURCE:
        raise ValueError('Onbekende hitlijstbron')
    chart_date = datetime.strptime(chart.get('date', ''), '%Y-%m-%d').date()
    today = today or datetime.now(ZoneInfo('Europe/Brussels')).date()
    if not 0 <= (today - chart_date).days <= max_age:
        raise ValueError('De bronhitlijst is verouderd of ligt in de toekomst')
    data = chart.get('data', [])
    if not isinstance(data, list) or len(data) != 50:
        raise ValueError('Geen volledige rangschikking van 1 tot 50')
    for row in data:
        if not isinstance(row, dict) or type(row.get('this_week')) is not int:
            raise ValueError('Ongeldige hitlijstpositie')
        if not isinstance(row.get('song'), str) or not row['song'].strip():
            raise ValueError('Titel ontbreekt')
        artists = row.get('artists')
        if not isinstance(artists, list) or not artists or any(not isinstance(a, str) or not a.strip() for a in artists):
            raise ValueError('Artiestcredit ontbreekt')
        if type(row.get('peak_position')) is not int or not 1 <= row['peak_position'] <= 50:
            raise ValueError('Ongeldige piekpositie')
        if type(row.get('weeks_on_chart')) is not int or row['weeks_on_chart'] < 1:
            raise ValueError('Ongeldig aantal weken')
        if row.get('last_week') is not None and (type(row['last_week']) is not int or not 1 <= row['last_week'] <= 50):
            raise ValueError('Ongeldige vorige positie')
    if sorted(row['this_week'] for row in data) != list(range(1, 51)):
        raise ValueError('Geen volledige rangschikking van 1 tot 50')
    return {**chart, 'data': sorted(data, key=lambda row: row['this_week'], reverse=True)}

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
    return validate_chart({'date':chart_date.isoformat(),'source':SOURCE,'data':data}, today=today)

def load_chart(today=None):
    failure = None
    for attempt in range(3):
        try:
            response=requests.get(SOURCE,headers={'User-Agent':'Mozilla/5.0','Accept-Language':'nl-BE,nl;q=0.9,en;q=0.8'},timeout=40)
            response.raise_for_status()
            chart=parse_chart(response.text, today=today)
            (ROOT/'chart_source.html').write_text(response.text,encoding='utf-8')
            (ROOT/'chart_snapshot.json').write_text(json.dumps(chart,ensure_ascii=False,indent=2),encoding='utf-8')
            return chart
        except (requests.RequestException,ValueError) as exc:
            failure = exc
            if attempt < 2:
                time.sleep(3)
    # The source can temporarily return a challenge/error page with HTTP 200.
    # Use only a complete, validated snapshot from this chart week; never fixtures
    # or last week's chart when a new weekly update is due.
    snapshot = ROOT/'chart_snapshot.json'
    if snapshot.exists():
        try:
            chart = validate_chart(json.loads(snapshot.read_text(encoding='utf-8')), today=today, max_age=6)
        except (OSError, ValueError, TypeError) as exc:
            raise ValueError('Live bron niet bruikbaar en geen geldige hitlijst van deze week beschikbaar') from exc
        print('Live bron tijdelijk niet bruikbaar; gebruik gevalideerde Ultratop van', chart['date'], flush=True)
        return chart
    raise failure
