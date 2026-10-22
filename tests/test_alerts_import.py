import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('alerts_import', Path(__file__).resolve().parents[1] / 'alerts_to_js.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class AlertsImportTests(unittest.TestCase):
    def test_import_deduplicates_and_only_exports_public_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            row = '2026-10-21,일본,https://youtu.be/abcdefghijk,체험,1.2만,200,문의메일,비공개 원문\n'
            (root / '2026-10-21.csv').write_text('날짜,나라,링크,제목,구독자,조회수,메일출처,포인트\n' + row + row, encoding='utf-8-sig')
            out = root / 'alerts.js'
            with patch.object(mod, 'OUT', str(out)), patch.object(mod.sys, 'argv', ['import', '--dir', folder]):
                mod.main()
            text = out.read_text(encoding='utf-8')
            items = json.loads(text.removeprefix('window.ALERTS=').strip().removesuffix(';'))
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]['subs'], 12000)
            self.assertEqual(items[0]['published'], '')
            self.assertNotIn('비공개 원문', text)
            self.assertNotIn('문의메일', text)

    def test_missing_or_invalid_input_preserves_previous_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            out = root / 'alerts.js'
            out.write_text('previous', encoding='utf-8')
            with patch.object(mod, 'OUT', str(out)), patch.object(mod.sys, 'argv', ['import', '--dir', folder]):
                mod.main()
                self.assertEqual(out.read_text(), 'previous')
                (root / 'bad.csv').write_text('unexpected\nvalue', encoding='utf-8')
                with self.assertRaises(ValueError):
                    mod.main()
                self.assertEqual(out.read_text(), 'previous')

    def test_countries_and_unknown_preserve_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            csv = root / '2026-10-22.csv'
            csv.write_text('나라,영상id\n한국,aaaaaaaaaaa\n일본,bbbbbbbbbbb\n대만,ccccccccccc\nTaiwan,ddddddddddd\n', encoding='utf-8')
            out = root / 'out.js'
            with patch.object(mod, 'OUT', str(out)), patch.object(mod.sys, 'argv', ['import', '--dir', folder]):
                mod.main()
                text = out.read_text(encoding='utf-8')
                items = json.loads(text.split('=', 1)[1].rstrip(';\n'))
                self.assertEqual([x['country'] for x in items], ['한국', '일본', '대만', '대만'])
                self.assertEqual([x['alert_country'] for x in items], ['한국', '일본', '대만', '대만'])
                csv.write_text('나라,영상id\nunknown,eeeeeeeeeee\n', encoding='utf-8')
                with self.assertRaises(ValueError):
                    mod.main()
                self.assertEqual(out.read_text(encoding='utf-8'), text)

    def test_numbers(self):
        self.assertEqual(mod.num('1.5K'), 1500)
        self.assertEqual(mod.num('0'), 0)
        self.assertIsNone(mod.num('unknown'))


if __name__ == '__main__':
    unittest.main()
