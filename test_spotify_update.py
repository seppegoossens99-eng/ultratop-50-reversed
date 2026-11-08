import contextlib
import io
import os
import re
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import update_spotify as update

CREDIT = 'HUGEL and Imael Angel and Ultra Naté'
TITLE = "Movin' To The Sun"


def spotify_artists(*names):
    return [{'name': name} for name in names]


class SpotifyMatchingTests(unittest.TestCase):
    def test_documented_credit_variant_accepts_this_release_only(self):
        self.assertTrue(update.artist_ok(CREDIT, spotify_artists('HUGEL', 'Ultra Naté'), TITLE))
        self.assertTrue(update.title_ok(TITLE, TITLE))
        self.assertFalse(update.artist_ok(CREDIT, spotify_artists('HUGEL', 'Ultra Naté'), 'Unrelated song'))
        self.assertFalse(update.artist_ok(CREDIT, spotify_artists('HUGEL'), TITLE))
        self.assertFalse(update.artist_ok(CREDIT, spotify_artists('Ultra Naté'), TITLE))
        self.assertFalse(update.artist_ok(CREDIT, spotify_artists('HUGEL', 'Unrelated artist'), TITLE))
        self.assertFalse(update.artist_ok('HUGEL and Someone Else and Ultra Naté', spotify_artists('HUGEL', 'Ultra Naté'), TITLE))
        self.assertFalse(update.title_ok(TITLE, 'Angel Face'))

    def test_other_collaborations_still_require_all_credited_artists(self):
        self.assertTrue(update.artist_ok('Justice and Tame Impala and SZA', spotify_artists('Justice', 'Tame Impala', 'SZA'), 'Song'))
        self.assertFalse(update.artist_ok('Justice and Tame Impala and SZA', spotify_artists('Justice', 'SZA'), 'Song'))
        self.assertTrue(update.artist_ok('Suzan & Freek', spotify_artists('Suzan & Freek'), 'Song'))

    def run_update(self, missing=False, duplicate=False, length=50):
        tracks = [(pos, TITLE if pos == 14 else f'Song {pos}', CREDIT if pos == 14 else f'Artist {pos}') for pos in range(50, 50-length, -1)]
        client = Mock()
        client.current_user.return_value = {'id': 'test-user'}
        client.playlist.return_value = {'id': 'test-playlist', 'owner': {'id': 'test-user'}}
        def search(q, **kwargs):
            title = re.search(r'(?:track:)?"([^"]+)"', q)
            title = title.group(1) if title else next((t for _, t, _ in tracks if t in q), '')
            row = next((row for row in tracks if row[1] == title), None)
            if row is None or (missing and row[0] == 14): return {'tracks': {'items': []}}
            pos, title, artist = row
            names = ['HUGEL', 'Ultra Naté'] if pos == 14 else [artist]
            return {'tracks': {'items': [{'id': str(pos), 'uri': 'spotify:track:' + ('same' if duplicate else str(pos)), 'name': title, 'artists': spotify_artists(*names)}]}}
        client.search.side_effect = search
        env = {'SPOTIFY_CLIENT_ID': 'test-client', 'SPOTIFY_CLIENT_SECRET': 'test-secret', 'SPOTIFY_REFRESH_TOKEN': 'test-refresh', 'SPOTIFY_PLAYLIST_ID': 'test-playlist'}
        auth = Mock(); auth.refresh_access_token.return_value = {'access_token': 'test-access'}
        with patch.dict(os.environ, env), patch.object(update, 'chart', return_value=tracks), patch.object(update, 'SpotifyOAuth', return_value=auth), patch.object(update.spotipy, 'Spotify', return_value=client), patch.object(update.requests, 'put') as put, contextlib.redirect_stdout(io.StringIO()):
            if missing or duplicate or length != 50:
                with self.assertRaisesRegex(RuntimeError, 'playlist blijft ongewijzigd'): update.main()
                put.assert_not_called()
            else:
                update.main()
                put.assert_called_once()
                self.assertEqual(put.call_args.args[0], 'https://api.spotify.com/v1/playlists/test-playlist/items')
                self.assertEqual(put.call_args.kwargs['json']['uris'], [f'spotify:track:{pos}' for pos in range(50, 0, -1)])

    def test_all_50_tracks_including_credit_variant_replace_playlist_in_reverse_order(self): self.run_update()
    def test_missing_match_never_replaces_existing_playlist(self): self.run_update(missing=True)
    def test_duplicate_tracks_never_replace_existing_playlist(self): self.run_update(duplicate=True)
    def test_incomplete_chart_never_replaces_existing_playlist(self): self.run_update(length=49)


if __name__ == '__main__': unittest.main()
