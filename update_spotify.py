import os
import re
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup
import spotipy
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from spotipy.oauth2 import SpotifyOAuth

SOURCE = "https://acharts.co/belgium_singles_top_50"
PLAYLIST_NAME = "Ultratop 50 België – Reversed"
TZ = ZoneInfo("Europe/Brussels")

def chart():
    table = None
    for attempt in range(1, 5):
        try:
            response = requests.get(
                SOURCE,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "nl-BE,nl;q=0.9,en;q=0.8",
                },
                timeout=45,
            )
            print(f"aCharts poging {attempt}/4: HTTP {response.status_code}, {len(response.content)} bytes, URL {response.url}", flush=True)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            table = soup.select_one("#ChartTable")
            if table is not None:
                break
            page_title = soup.title.get_text(" ", strip=True) if soup.title else "(geen titel)"
            print(f"ChartTable ontbreekt. Paginatitel: {page_title!r}; begin tekst: {soup.get_text(' ', strip=True)[:250]!r}", flush=True)
        except requests.RequestException as exc:
            print(f"aCharts verzoek mislukt: {exc}", flush=True)
        if attempt < 4:
            time.sleep(attempt * 5)
    if table is None:
        raise RuntimeError("Na vier pogingen geen geldige ChartTable van aCharts; playlist blijft ongewijzigd")
    tracks = []
    for row in table.select('tr[itemprop="itemListElement"]'):
        pos = row.select_one('[itemprop="position"]')
        title = row.select_one('.cPrinciple [itemprop="name"]')
        artist = row.select_one('.cPrinciple [itemprop="byArtist"] [itemprop="name"]')
        if not all((pos, title, artist)):
            raise RuntimeError("Onvolledige hitlijstregel")
        tracks.append((int(pos.get_text(strip=True)), title.get_text(" ", strip=True), artist.get_text(" ", strip=True)))
    if len(tracks) != 50 or sorted(x[0] for x in tracks) != list(range(1, 51)):
        raise RuntimeError(f"Geen complete Top 50: {len(tracks)} regels")
    text = soup.get_text(" ", strip=True)
    match = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+20\d{2}\b", text)
    if not match:
        raise RuntimeError("Chartdatum niet gevonden: niet publiceren")
    date = datetime.strptime(match.group(), "%B %d, %Y").date()
    age = (datetime.now(TZ).date() - date).days
    if not 0 <= age <= 16:
        raise RuntimeError(f"Chartdatum {date} is niet recent genoeg (leeftijd {age} dagen)")
    print(f"Ultratop chart date: {date}, {len(tracks)} nummers")
    return list(reversed(tracks))

def main():
    tracks = chart()
    auth = SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri="http://127.0.0.1:8888/callback",
        scope="playlist-modify-private playlist-modify-public",
    )
    token = auth.refresh_access_token(os.environ["SPOTIFY_REFRESH_TOKEN"])["access_token"]
    sp = spotipy.Spotify(auth=token, requests_timeout=20, retries=0, status_retries=0, backoff_factor=0)
    # Spotipy creates an HTTP adapter that retries 429 by default even when retries=0.
    # Replace it so Retry-After values of many hours never block GitHub Actions.
    sp._session.mount("https://", HTTPAdapter(max_retries=Retry(total=0, status=0, respect_retry_after_header=False)))
    user_id = sp.current_user()["id"]
    uris = []
    used = set()
    unresolved = []
    import unicodedata

    def norm(s):
        s = unicodedata.normalize("NFKD", s.casefold())
        return re.sub(r"[^a-z0-9]+", "", "".join(ch for ch in s if not unicodedata.combining(ch)))

    def clean_artist(s):
        return re.sub(r"\s*\((?:fr|be|nl|uk|us|de|au|ca)\)\s*$", "", s, flags=re.I).strip()

    def artist_parts(s):
        s = clean_artist(s)
        return [clean_artist(p).strip() for p in re.split(r"\s+(?:x|and|feat\.?|ft\.?)\s+", s, flags=re.I) if p.strip()]

    def artist_ok(chart_artist, spotify_artists):
        expected = [norm(x) for x in artist_parts(chart_artist)]
        actual = [norm(a["name"]) for a in spotify_artists]
        if norm(chart_artist) == "bausa" and "thebausa" in actual:
            return True  # Chart credits Bausa; Spotify credits The Bausa for Magnetic.
        return bool(expected) and all(x in actual for x in expected)

    def title_ok(chart_title, spotify_title):
        expected = norm(chart_title)
        actual = norm(spotify_title)
        if actual == expected:
            return True
        # Only permit an explicit parenthetical suffix on the Spotify version.
        # E.g. "I'm Good - From The Movie GOAT" or "Talk To You (ft. 54 Ultra)".
        prefix = re.split(r"\s+(?:-|–)\s+|\s*\(", spotify_title, maxsplit=1)[0]
        return norm(prefix) == expected

    for pos, title, artist in tracks:
        print(f"Zoeken Ultratop #{pos}: {artist} - {title}", flush=True)
        artist_clean = clean_artist(artist)
        parts = artist_parts(artist)
        queries = [
            f'track:"{title}" artist:"{artist_clean}"',
            f'"{title}" "{artist_clean}"',
            f'{title} {artist_clean}',
            f'"{title}" "{parts[0]}"',
            f'{title} {parts[0]}',
        ]
        candidates = {}
        matches = []
        for query in dict.fromkeys(queries):
            for item in sp.search(q=query, type="track", limit=10)["tracks"]["items"]:
                candidates[item["id"]] = item
            matches = [
                item for item in candidates.values()
                if title_ok(title, item["name"]) and artist_ok(artist, item["artists"])
            ]
            if matches:
                break
        if not matches:
            print(f"ONZEKER: {pos}: {artist} - {title}", flush=True)
            for item in list(candidates.values())[:8]:
                print("  Spotify kandidaat:", item["name"], "-", ", ".join(a["name"] for a in item["artists"]), flush=True)
            unresolved.append((pos, artist, title))
            continue
        available = [item for item in matches if item["uri"] not in used]
        if not available:
            unresolved.append((pos, artist, title))
            print(f"DUBBEL: {pos}: {artist} - {title}", flush=True)
            continue
        target = next((item for item in available if item.get("is_playable", True)), available[0])
        uri = target["uri"]
        used.add(uri)
        uris.append(uri)
        print(f"{51-pos:02d}. {artist} - {title} -> {target['name']} / {', '.join(a['name'] for a in target['artists'])}", flush=True)
    if unresolved:
        print(f"\\nNIET GEKOPPELD: {len(unresolved)} van 50", flush=True)
        for pos, artist, title in unresolved:
            print(f"  Ultratop #{pos}: {artist} - {title}", flush=True)
        raise RuntimeError("Niet alle 50 tracks betrouwbaar gevonden; playlist blijft ongewijzigd")
    playlist_id = os.environ.get("SPOTIFY_PLAYLIST_ID", "").strip() or "59kSfLkSzSUryhnPMHeF99"
    if playlist_id:
        playlist = sp.playlist(playlist_id, fields="id,name,owner(id)")
        if playlist["owner"]["id"] != user_id:
            raise RuntimeError("Doelplaylist is niet van dit Spotify-account")
    else:
        playlist = sp.user_playlist_create(user=user_id, name=PLAYLIST_NAME, public=False,
            description="Officiële Belgische Ultratop 50 in omgekeerde volgorde (50 naar 1). Wekelijks bijgewerkt.")
        playlist_id = playlist["id"]
        print("NIEUWE PLAYLIST:", playlist["external_urls"]["spotify"])
        print("BELANGRIJK: voeg SPOTIFY_PLAYLIST_ID toe als GitHub Secret voor volgende updates:", playlist_id)
    sp.playlist_replace_items(playlist_id, uris)
    print(f"SUCCES: {len(uris)} nummers geplaatst, 50 naar 1. Playlist ID: {playlist_id}")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FOUT: {exc}", file=sys.stderr)
        raise
