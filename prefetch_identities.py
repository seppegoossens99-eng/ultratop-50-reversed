"""Fetch explicit disambiguated artist IDs before looking up chart metadata."""
import json
from datetime import date
from pathlib import Path
from artist_identities import VERIFIED_ARTIST_IDS
from collect_band_members import get_artist
import requests
import time

ROOT=Path(__file__).resolve().parent
def main():
    path=ROOT/'band_members_cache.json'
    cache=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    resolved_path=ROOT/'resolved_identities.json'
    resolved=json.loads(resolved_path.read_text(encoding='utf-8')) if resolved_path.exists() else {}
    if 'Judith' not in resolved:
        time.sleep(1.2)
        r=requests.get('https://musicbrainz.org/ws/2/release/a9d4c675-5889-4698-8ab3-43de6677d857',params={'inc':'artist-credits','fmt':'json'},headers={'User-Agent':'UltratopReverseMetadata/1.0'},timeout=20)
        r.raise_for_status()
        release=r.json()
        credits=[c['artist'] for c in release.get('artist-credit',[]) if isinstance(c,dict) and 'artist' in c]
        if release.get('title','').casefold()!='you did not sign up for this' or len(credits)!=1 or credits[0]['name'].casefold()!='judith':
            raise ValueError('Judith release identity could not be verified')
        resolved['Judith']=credits[0]['id']
        resolved_path.write_text(json.dumps(resolved),encoding='utf-8')
    VERIFIED_ARTIST_IDS.update(resolved)
    for name,identifier in VERIFIED_ARTIST_IDS.items():
        if cache.get(identifier,{}).get('data'):
            continue
        data=get_artist(identifier)
        if data.get('id')==identifier:
            cache[identifier]={'checked':date.today().isoformat(),'url_relations_fetched':True,'data':data}
            print('Verified identity:',name,flush=True)
    path.write_text(json.dumps(cache,ensure_ascii=False,separators=(',',':')),encoding='utf-8')

if __name__=='__main__':
    main()
