import csv
import re
from pathlib import Path
from collections import Counter
root=Path(__file__).resolve().parent
def rows(name):
    return list(csv.DictReader((root/name).open(encoding='utf-8-sig',newline='')))
tracks=rows('ultratop_50_details.csv')
artists=rows('ultratop_50_artists.csv')
members=rows('ultratop_band_members.csv')
profiles=rows('ultratop_artist_profiles.csv')
h=(root/'index.html').read_text(encoding='utf-8')
assert [int(r['Ultratop-positie']) for r in tracks]==list(range(50,0,-1))
assert len(re.findall('<article class=',h))==50
assert len({r['Artiest'] for r in artists})==len(profiles)==63
assert all(r['Afbeelding'].startswith('https://') for r in profiles)
assert len({r['Artiest'] for r in members})==9
assert len(members)==25 and all(r['Lid'] and r['Functie/instrument'] not in ('Niet vermeld','Niet bevestigd','eponymous','task','') for r in members)
assert all(r['Type']=='Person' for r in profiles if r['Artiest'] in ('Judith','Used','MAKSIM'))
assert 'Ultratop 50 Vlaanderen' in h and '#50 → #1' in h
assert 'Billboard' not in h and 'Hot 100' not in h
assert 'Kleurenlegende' in h and 'Ongewijzigd' in h
assert 'data-rank="50"' in h and 'data-rank="1"' in h and 'data-rank="51"' not in h
print('PASS: 50 reversed songs; 63 sourced portraits; 25 members in 9 groups; Ultratop branding and rank filters')
