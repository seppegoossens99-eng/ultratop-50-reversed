"""Enrich Ultratop CSV from MusicBrainz. Unknown/ambiguous fields stay blank."""
import csv
import re
import time
import unicodedata
from pathlib import Path
import requests
try:
    import pycountry
except ImportError:
    pycountry = None
from artist_identities import VERIFIED_ARTIST_IDS as IDENTITY_OVERRIDES

CHART_URL = "https://raw.githubusercontent.com/mhollingshead/billboard-hot-100/main/recent.json"
MB = "https://musicbrainz.org/ws/2"
OUTPUT = Path("ultratop_50_details.csv")
ARTISTS_OUTPUT = Path("ultratop_50_artists.csv")
ARTIST_FIELDS = ["Ultratop-positie", "Nummer", "Artiest", "Land", "Staat/regio", "Stad", "Bron herkomst"]
FIELDS = ["Ultratop-positie", "Artiest", "Nummer", "Vorige week", "Weken in Ultratop 50", "Hoogste positie", "Land", "Staat/regio", "Stad",
          "Eerste officiële releasedatum", "Bron herkomst", "Bron releasedatum"]
HEADERS = {"User-Agent": "UltratopReverseMetadata/1.0 (https://github.com/seppegoossens99-eng/ultratop-50-reversed)"}
session = requests.Session()
session.headers.update(HEADERS)
last_call = 0.0

def norm(value):
    value = unicodedata.normalize("NFKD", value.casefold())
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in value if not unicodedata.combining(c))).strip()

# Artist names containing separators must not be split into separate people.
PROTECTED_ARTISTS = (
    "King Gizzard & The Lizard Wizard",
    "Earth, Wind & Fire",
    "Tyler, the Creator",
)
COLLAB_SEPARATOR = r"\s+(?:featuring|feat\.?|ft\.?|with|x)\s+|\s*&\s*|\s*,\s*"

def split_artists(value):
    """Split collaborations, keeping established group names intact."""
    masked = value
    placeholders = {}
    for i, name in enumerate(PROTECTED_ARTISTS):
        token = f"PROTECTEDARTIST{i}TOKEN"
        pattern = re.compile(re.escape(name), re.I)
        if pattern.search(masked):
            placeholders[token] = pattern.search(masked).group()
            masked = pattern.sub(lambda match: token, masked)
    parts = re.split(COLLAB_SEPARATOR, masked, flags=re.I)
    result = []
    for part in parts:
        part = part.strip()
        for token, name in placeholders.items():
            part = part.replace(token, name)
        if part and part not in result:
            result.append(part)
    return result

def main_artist(value):
    parts = split_artists(value)
    return parts[0] if parts else value.strip()

def mb_get(entity, params):
    global last_call
    wait = 1.15 - (time.monotonic() - last_call)
    if wait > 0:
        time.sleep(wait)
    try:
        last_call = time.monotonic()
        response = session.get(f"{MB}/{entity}", params={**params, "fmt": "json"}, timeout=18)
        if response.status_code in (429, 503):
            time.sleep(4)
            last_call = time.monotonic()
            response = session.get(f"{MB}/{entity}", params={**params, "fmt": "json"}, timeout=18)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        print(f"MusicBrainz unavailable for {entity}: {exc}", flush=True)
        return {}

VERIFIED_ARTIST_IDS = {
    "Ashe": "36086094-c2a4-49b9-8572-0fbf12fc3409",
    "JADE": "f4108df8-cf1f-4279-a840-599b2a291127",
    "Jamie Miller": "081e71fb-4291-4a0c-a0f7-52b6c9ea8b31",
    "Justice": "860b2707-6153-4e3a-aa57-74d2b42c55b5",
    "Robert Smith": "7d1a1624-784b-4f89-8ff9-b9b493cd059d",
    "Rockwell": "57ea7aef-42d6-4c16-a4a7-88b4ba8283a4",
}
artist_cache = {}
VERIFIED_ARTIST_IDS.update(IDENTITY_OVERRIDES)
recording_cache = {}
area_cache = {}

def country_name(code):
    if code == "US":
        return "Verenigde Staten"
    if not code:
        return ""
    if pycountry is None:
        return {"GB":"Verenigd Koninkrijk","NL":"Nederland","BE":"België","FR":"Frankrijk","DE":"Duitsland","SE":"Zweden","NO":"Noorwegen","AU":"Australië","IE":"Ierland","LT":"Litouwen","RO":"Roemenië","BR":"Brazilië"}.get(code,code)
    match = pycountry.countries.get(alpha_2=code)
    return match.name if match else code

def us_state(area_id):
    """Follow MusicBrainz area hierarchy; never infer state from city name."""
    if not area_id:
        return ""
    if area_id in area_cache:
        return area_cache[area_id]
    visited = set()
    pending = [(area_id, 0)]
    result = ""
    while pending:
        identifier, depth = pending.pop(0)
        if identifier in visited or depth > 3:
            continue
        visited.add(identifier)
        area = mb_get(f"area/{identifier}", {"inc": "area-rels"})
        if area.get("type") == "Subdivision":
            # Subdivisions include counties: only accept a state directly
            # below the United States (verified in the next pass).
            relations = area.get("relations", [])
            parents = [r.get("area", {}) for r in relations
                       if r.get("type") == "part of" and r.get("direction") == "backward"]
            if any(p.get("name") == "United States" for p in parents):
                result = area.get("name", "")
                break
        for rel in area.get("relations", []):
            if rel.get("type") == "part of" and rel.get("direction") == "backward":
                parent = rel.get("area", {})
                if parent.get("id") and parent.get("name") != "United States":
                    pending.append((parent["id"], depth + 1))
    area_cache[area_id] = result
    return result


# Verified origins for artists whose MusicBrainz country field is missing.
# Source links are retained in the artist CSV for review.
VERIFIED_ORIGINS = {
    "Alyssa Grace": ("Verenigde Staten", "California", "", "https://www.allmusic.com/artist/alyssa-grace-mn0005023955"),
    "Blake Whiten": ("Verenigde Staten", "South Carolina", "Six Mile", "https://press.warnerrecords.com/sites/g/files/g2000014901/files/2026-01/Blake%20Whiten%202025%20Bio.pdf"),
    "Thekidszn": ("Verenigde Staten", "New York", "", "https://www.missinglinkmusic.com/Topic/378/New-Signing-Thekidszn"),
    "comehelpglo": ("Verenigde Staten", "Ohio", "Ashland", "https://www.famousbirthdays.com/people/comehelpglo.html"),
    "Dolly Babe": ("Verenigde Staten", "Texas", "", "https://www.power1061.com/lsp/artist/bio/dolly-babe/"),
    # Soundtrack vocal ensemble, not a band with a geographic hometown.
    "The Citizens of Halloween": ("", "", "", "https://music.apple.com/us/artist/the-citizens-of-halloween/1656038206"),
}

def artist_details(name):
    if name in VERIFIED_ORIGINS:
        return VERIFIED_ORIGINS[name]
    if name == "John Morgan":
        return ("Verenigde Staten", "North Carolina", "", "https://www.opry.com/artists/john-morgan")
    key = norm(name)
    expected_source = 'https://musicbrainz.org/artist/' + VERIFIED_ARTIST_IDS[name] if name in VERIFIED_ARTIST_IDS else ''
    if key in artist_cache and (not expected_source or artist_cache[key][3] == expected_source):
        return artist_cache[key]
    result = ("", "", "", "")
    verified_id = VERIFIED_ARTIST_IDS.get(name)
    if verified_id:
        record = mb_get(f"artist/{verified_id}", {"inc": "url-rels"})
        candidates = [record] if record.get("id") == verified_id else []
    else:
        data = mb_get("artist", {"query": f'artist:"{name}"', "limit": 8})
        candidates = [a for a in data.get("artists", []) if norm(a.get("name", "")) == key
                      and int(a.get("score", 0)) >= 90]
    # Multiple identically named artists: do not guess.
    if len(candidates) == 1:
        artist = candidates[0]
        code = artist.get("country", "")
        begin = artist.get("begin-area") or {}
        area = artist.get("area") or {}
        city = begin.get("name", "") if begin.get("type") == "City" else ""
        region = ""
        if code == "US":
            region = us_state(begin.get("id") or area.get("id"))
        country = country_name(code)
        result = (country, region, city, f"https://musicbrainz.org/artist/{artist['id']}")
    artist_cache[key] = result
    return result

def earliest_recording_date(title, artist):
    # Individually checked against the original soundtrack and single releases.
    # Keep the exact source beside the date for later auditing.
    if norm(title) == "this is halloween" and norm(artist) == "the citizens of halloween":
        return ("1993-10-12", "https://musicbrainz.org/release/f3a762e5-cfc0-30a1-a0bf-001f6ab5f6fa")
    if norm(title).startswith("dai dai") and "shakira" in norm(artist) and "burna boy" in norm(artist):
        return ("2026-05-14", "https://music.apple.com/us/song/6778672603")
    if norm(title) == "kid myself" and norm(artist) == "john morgan":
        return ("2025-03-21", "https://themusicuniverse.com/john-morgan-shares-kid-myself/")
    key = (norm(title), norm(artist))
    if key in recording_cache:
        return recording_cache[key]
    result = ("", "")
    data = mb_get("recording", {"query": f'recording:"{title}" AND artist:"{artist}"', "limit": 25})
    dates = []
    for rec in data.get("recordings", []):
        if norm(rec.get("title", "")) != norm(title):
            continue
        credited = rec.get("artist-credit", [])
        names = [norm(a.get("artist", {}).get("name", "")) for a in credited if isinstance(a, dict)]
        if norm(artist) not in names:
            continue
        date = rec.get("first-release-date", "")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            dates.append((date, rec["id"]))
    # This is the earliest known MusicBrainz recording date, not proof of the
    # first-ever official release. Keep source so it can be manually verified.
    if dates:
        date, rec_id = min(dates)
        result = (date, f"https://musicbrainz.org/recording/{rec_id}")
    recording_cache[key] = result
    return result
