import os
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup
import spotipy
from spotipy.oauth2 import SpotifyOAuth

SOURCE = "https://acharts.co/belgium_singles_top_50"
PLAYLIST_NAME = "Ultratop 50 België – Reversed"
TZ = ZoneInfo("Europe/Brussels")

def chart():
    response = requests.get(SOURCE, headers={"User-Agent": "Mozilla/5.0"}, timeout=45)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    table = soup.select_one("#ChartTable")
    if table is None:
        raise RuntimeError("ChartTable ontbreekt")
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
    sp = spotipy.Spotify(auth=token, requests_timeout=30, retries=3)
    user_id = sp.current_user()["id"]
    uris = []
    used = set()
    for pos, title, artist in tracks:
        query = f'track:"{title}" artist:"{artist}"'
        results = sp.search(q=query, type="track", limit=10)["tracks"]["items"]
        if not results:
            print(f"NIET GEVONDEN: {pos}: {artist} - {title}")
            raise RuntimeError("Niet alle 50 tracks gevonden; playlist blijft ongewijzigd")
        target = None
        norm = lambda s: re.sub(r"[^a-z0-9]+", "", s.casefold())
        for item in results:
            if norm(item["name"]) == norm(title) and any(norm(a["name"]) == norm(artist) for a in item["artists"]):
                target = item
                break
        if target is None:
            print(f"ONZEKER: {pos}: {artist} - {title}")
            raise RuntimeError("Geen exacte Spotify-match; playlist blijft ongewijzigd")
        uri = target["uri"]
        if uri in used:
            raise RuntimeError(f"Dubbel Spotify-ID bij positie {pos}")
        used.add(uri)
        uris.append(uri)
        print(f"{51-pos:02d}. {artist} - {title}")
    playlist_id = os.environ.get("SPOTIFY_PLAYLIST_ID", "").strip()
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
