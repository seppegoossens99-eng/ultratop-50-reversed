"""Cache documented release-group years and provisional song dates by verified artist ID."""
import csv
import json
import time
from datetime import date,timedelta
from pathlib import Path
import requests
from metadata_sources import norm

ROOT=Path(__file__).resolve().parent
def read(name):
    with (ROOT/name).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))
def write(name,rows):
    with (ROOT/name).open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)

def main():
    cache_path=ROOT/'catalog_cache.json'
    cache=json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
    if not cache_path.exists():
        cache_path.write_text('{}',encoding='utf-8')
    credits=read('ultratop_50_artists.csv')
    extras=read('ultratop_artist_extra.csv')
    by_name={r['Artiest']:r for r in extras}
    tracks=read('ultratop_50_details.csv')
    identities={r['Artiest']:r['Bron herkomst'].rsplit('/',1)[-1] for r in credits if r['Bron herkomst'].startswith('https://musicbrainz.org/artist/')}
    cutoff=(date.today()-timedelta(days=30)).isoformat()
    for name,identifier in identities.items():
        row=by_name.get(name,{})
        if row.get('Debuutalbum'):
            continue
        entry=cache.get(identifier,{})
        if entry.get('checked','')<cutoff:
            groups=[]
            try:
                offset=0
                while True:
                    time.sleep(1.2)
                    response=requests.get('https://musicbrainz.org/ws/2/release-group',params={'artist':identifier,'limit':100,'offset':offset,'fmt':'json'},headers={'User-Agent':'UltratopReverseMetadata/1.0'},timeout=12)
                    response.raise_for_status()
                    page=response.json()
                    groups.extend(page.get('release-groups',[]))
                    offset+=100
                    if offset>=page.get('release-group-count',0):
                        break
                entry={'checked':date.today().isoformat(),'groups':groups}
                cache[identifier]=entry
            except (requests.RequestException,ValueError) as exc:
                print('Catalog unavailable:',name,exc,flush=True)
        groups=entry.get('groups',[])
        candidates=[g for g in groups if len(g.get('first-release-date',''))>=4 and g.get('primary-type') in ('Album','EP','Single') and not set(g.get('secondary-types',[])) & {'Compilation','DJ-mix','Remix','Live'}]
        if candidates:
            first=min(candidates,key=lambda g:g['first-release-date'])
            row['Debuutalbum']=first['first-release-date'][:4]
            row['Bron debuutalbum']='https://musicbrainz.org/release-group/'+first['id']
            print('Documented release year:',name,row['Debuutalbum'],flush=True)
        for track in tracks:
            if track['Bron releasedatum']:
                continue
            matching=[g for g in candidates if norm(g.get('title',''))==norm(track['Nummer']) and len(g.get('first-release-date',''))==10 and norm(name) in norm(track['Artiest'])]
            if matching:
                first=min(matching,key=lambda g:g['first-release-date'])
                track['Eerste officiële releasedatum']=first['first-release-date']
                track['Bron releasedatum']='https://musicbrainz.org/release-group/'+first['id']
        cache_path.write_text(json.dumps(cache,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
        write('ultratop_artist_extra.csv',extras)
        write('ultratop_50_details.csv',tracks)

if __name__=='__main__':
    main()
