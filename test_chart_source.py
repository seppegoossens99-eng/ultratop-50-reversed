import copy
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import chart_source

TODAY = date(2026, 11, 8)
ROOT = Path(__file__).resolve().parent


class ChartSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.addCleanup(patch.stopall)
        patch.object(chart_source, 'ROOT', self.root).start()
        patch.object(chart_source.time, 'sleep').start()
        self.get = patch.object(chart_source.requests, 'get').start()
        self.get.return_value = SimpleNamespace(text='<html>Temporary error page</html>', raise_for_status=lambda: None)
        self.snapshot = json.loads((ROOT / 'chart_snapshot.json').read_text(encoding='utf-8'))
        # Anchor these tests independently of the moving production chart date.
        self.snapshot['date'] = '2026-11-07'

    def save_snapshot(self, data=None):
        (self.root / 'chart_snapshot.json').write_text(json.dumps(data or self.snapshot), encoding='utf-8')

    def test_http_200_without_table_uses_only_valid_current_week_snapshot(self):
        self.save_snapshot()
        raw = self.root / 'chart_source.html'
        raw.write_text('last valid page')
        result = chart_source.load_chart(today=TODAY)
        self.assertEqual(result['date'], '2026-11-07')
        self.assertEqual([row['this_week'] for row in result['data']], list(range(50, 0, -1)))
        self.assertEqual(self.get.call_count, 3)
        self.assertEqual(raw.read_text(), 'last valid page')
        self.assertEqual(json.loads((self.root / 'chart_snapshot.json').read_text()), self.snapshot)

    def test_old_future_incomplete_or_corrupt_snapshots_are_rejected(self):
        invalid = []
        for value in ('2026-10-31', '2026-11-09'):
            data = copy.deepcopy(self.snapshot); data['date'] = value; invalid.append(data)
        data = copy.deepcopy(self.snapshot); data['data'].pop(); invalid.append(data)
        data = copy.deepcopy(self.snapshot); data['data'][0]['this_week'] = data['data'][1]['this_week']; invalid.append(data)
        data = copy.deepcopy(self.snapshot); data['data'][0]['artists'] = []; invalid.append(data)
        data = copy.deepcopy(self.snapshot); data['data'][0]['peak_position'] = 0; invalid.append(data)
        data = copy.deepcopy(self.snapshot); data['source'] = 'https://unrelated.example'; invalid.append(data)
        for data in invalid:
            with self.subTest(data=data['date']):
                self.save_snapshot(data)
                with self.assertRaisesRegex(ValueError, 'geen geldige hitlijst'):
                    chart_source.load_chart(today=TODAY)
        (self.root / 'chart_snapshot.json').write_text('{broken')
        with self.assertRaises(ValueError): chart_source.load_chart(today=TODAY)

    def test_network_failure_uses_valid_snapshot(self):
        self.save_snapshot()
        self.get.side_effect = chart_source.requests.ConnectionError('temporary failure')
        self.assertEqual(len(chart_source.load_chart(today=TODAY)['data']), 50)

    def test_no_snapshot_and_invalid_source_fails_without_writing_a_chart(self):
        with self.assertRaisesRegex(ValueError, 'Geen Ultratop-tabel'):
            chart_source.load_chart(today=TODAY)
        self.assertFalse((self.root / 'chart_snapshot.json').exists())

    def test_valid_live_chart_refreshes_snapshot_and_takes_precedence(self):
        self.snapshot['date'] = '2026-11-01'
        self.save_snapshot()
        document = (ROOT / 'chart_fixture.html').read_text(encoding='utf-8')
        self.get.return_value.text = document
        result = chart_source.load_chart(today=TODAY)
        self.assertEqual(result['date'], '2026-11-07')
        self.assertEqual(self.get.call_count, 1)
        self.assertEqual(json.loads((self.root / 'chart_snapshot.json').read_text()), result)


if __name__ == '__main__': unittest.main()
