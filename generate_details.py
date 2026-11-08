"""Generate the complete reverse Ultratop chart and individually credited artists."""
import csv
import json
import re
from pathlib import Path
import metadata_sources as metadata
from chart_source import load_chart

ROOT=Path(__file__).resolve().parent
FIELDS=['Ultratop-positie','Artiest','Nummer','Vorige week','Weken in Ultratop 50','Hoogste positie','Land','Staat/regio','Stad','Eerste officiële releasedatum','Bron herkomst','Bron releasedatum']
ARTIST_FIELDS=['Ultratop-positie','Nummer','Artiest','Land','Staat/regio','Stad','Bron herkomst']
ALIASES={'adela':'ADELA','katseye':'KATSEYE','tate mcrae':'Tate McRae','sombr':'sombr','anotr':'ANOTR','hugel':'HUGEL','dj goja':'DJ Goja','bausa':'The Bausa','juste':'Justė','maksim':'MAKSIM','bart kaell':'Bart Kaëll','rosalia':'ROSALÍA','ultra nate':'Ultra Naté','luisa sonza':'Luísa Sonza'}
PROTECTED={'suzan & freek','lucas & steve','king gizzard & the lizard wizard','earth wind & fire'}
ALIASES['willy wi']='Willy William'
ALIASES['the used']='Used'

def read(path):
    if not path.exists():
        return []
    with path.open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def write(path,fields,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def credited_artists(credits,canonical):
    names=[]
    for credit in credits:
        clean=re.sub(r'\s*\((?:fr|be|nl|uk|us|de|au|ca)\)\s*$','',credit,flags=re.I).strip()
        parts=[clean] if clean.casefold() in PROTECTED else re.split(r'\s+(?:featuring|feat\.?|ft\.?|with|x|and)\s+',clean,flags=re.I)
        for name in parts:
            key=metadata.norm(name)
            name=ALIASES.get(key,canonical.get(key,name))
            if name and name not in names:
                names.append(name)
    return names

def main(chart=None):
    chart=chart or load_chart()
    from artist_identities import VERIFIED_ARTIST_IDS
    metadata.VERIFIED_ARTIST_IDS.update(VERIFIED_ARTIST_IDS)
    previous_date=(ROOT/'ultratop_chart_date.txt').read_text(encoding='utf-8').strip() if (ROOT/'ultratop_chart_date.txt').exists() else ''
    prior=read(ROOT/'ultratop_50_details.csv')+read(ROOT/'seed_details.csv')
    releases={(metadata.norm(r['Nummer']),metadata.norm(r['Artiest'])):(r['Eerste officiële releasedatum'],r['Bron releasedatum']) for r in prior}
    seeds=read(ROOT/'seed_artists.csv')+read(ROOT/'ultratop_50_artists.csv')
    for row in seeds:
        if row.get('Bron herkomst','').startswith('https://musicbrainz.org/artist/'):
            metadata.artist_cache[metadata.norm(row['Artiest'])]=(row['Land'],row['Staat/regio'],row['Stad'],row['Bron herkomst'])
    profiles=read(ROOT/'ultratop_artist_profiles.csv')
    cache_path=ROOT/'band_members_cache.json'
    cache=json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
    for name,identifier in metadata.VERIFIED_ARTIST_IDS.items():
        data=cache.get(identifier,{}).get('data',{})
        if data.get('id')==identifier:
            begin=data.get('begin-area') or {}
            country=data.get('country') or next(iter((data.get('area') or {}).get('iso-3166-1-codes',[])), '')
            metadata.artist_cache[metadata.norm(name)]=(metadata.country_name(country),'',begin.get('name','') if begin.get('type')=='City' else '','https://musicbrainz.org/artist/'+identifier)
    canonical={metadata.norm(r['Artiest']):r['Artiest'] for r in profiles}
    rows=[]
    artists=[]
    for song in chart['data']:
        credits=credited_artists(song.get('artists',[song['artist']]),canonical)
        origins={name:metadata.artist_details(name) for name in credits}
        lead=credits[0]
        country,region,city,source=origins[lead]
        date,date_source=releases.get((metadata.norm(song['song']),metadata.norm(lead)),('',''))
        already_checked = previous_date==chart['date'] and any(r['Nummer']==song['song'] for r in prior)
        if not date_source and not already_checked:
            date,date_source=metadata.earliest_recording_date(song['song'],lead)
        row=dict(zip(FIELDS,[song['this_week'],' & '.join(credits),song['song'],song['last_week'] or '',song['weeks_on_chart'],song['peak_position'],country,region,city,date,source,date_source]))
        rows.append(row)
        for name in credits:
            artists.append(dict(zip(ARTIST_FIELDS,[song['this_week'],song['song'],name,*origins[name]])))
        print('Ultratop',song['this_week'],song['song'],' / '.join(credits),flush=True)
    write(ROOT/'ultratop_50_details.csv',FIELDS,rows)
    write(ROOT/'ultratop_50_artists.csv',ARTIST_FIELDS,artists)
    (ROOT/'ultratop_chart_date.txt').write_text(chart['date']+'\n',encoding='utf-8')
    print('Generated',len(rows),'songs and',len(artists),'artist credits',flush=True)

if __name__=='__main__':
    main()
