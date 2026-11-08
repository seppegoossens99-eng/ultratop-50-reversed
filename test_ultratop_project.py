import unittest
from datetime import date
from pathlib import Path
from chart_source import parse_chart
from generate_details import credited_artists, cached_release
from build_mobile_page import render_band_members

class UltratopProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document=(Path(__file__).resolve().parent/'chart_fixture.html').read_text(encoding='utf-8')
    def test_full_chart_is_reversed_and_dated(self):
        chart=parse_chart(self.document,today=date(2026,11,8))
        self.assertEqual(chart['date'],'2026-11-07')
        self.assertEqual([r['this_week'] for r in chart['data']],list(range(50,0,-1)))
    def test_all_collaborators_are_preserved(self):
        chart=parse_chart(self.document,today=date(2026,11,8))
        track=next(r for r in chart['data'] if r['this_week']==39)
        self.assertEqual(track['artists'],['Justice','Tame Impala','SZA'])
    def test_new_and_reentry_keep_week_counts(self):
        tracks={r['this_week']:r for r in parse_chart(self.document,today=date(2026,11,8))['data']}
        self.assertIsNone(tracks[49]['last_week'])
        self.assertEqual(tracks[49]['weeks_on_chart'],1)
        self.assertIsNone(tracks[48]['last_week'])
        self.assertGreater(tracks[48]['weeks_on_chart'],1)
        self.assertEqual(tracks[25]['last_week'],25)
    def test_future_and_stale_sources_are_rejected(self):
        for today in (date(2026,11,1),date(2026,12,1)):
            with self.assertRaises(ValueError):
                parse_chart(self.document,today=today)
    def test_incomplete_chart_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_chart('<h2>November 7, 2026</h2><table id="ChartTable"></table>',today=date(2026,11,8))
    def test_duo_is_not_split_and_alias_is_not_a_namesake(self):
        self.assertEqual(credited_artists(['Suzan & Freek'],{}),['Suzan & Freek'])
        self.assertEqual(credited_artists(['Bausa'],{}),['The Bausa'])
        self.assertEqual(credited_artists(['Topic X Becky G'],{}),['Topic','Becky G'])
        self.assertEqual(credited_artists(['Willy Wi..'],{}),['Willy William'])
        self.assertEqual(credited_artists(['The Used','Judith (Fr)'],{}),['Used','Judith'])
    def test_members_have_name_age_and_instrument(self):
        result=render_band_members([{'Lid':'Member','Leeftijd lid':'28','Functie/instrument':'Gitaar','Status':'Huidig'}])
        for expected in ('Member','28 jaar','Gitaar'):
            self.assertIn(expected,result)
    def test_collaboration_retains_previously_sourced_release_date(self):
        releases={('song','artist a artist b'):('2026-01-02','https://example.com/source')}
        self.assertEqual(cached_release(releases,'Song',['Artist A','Artist B']),('2026-01-02','https://example.com/source'))

if __name__=='__main__':
    unittest.main()
