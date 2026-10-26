import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import unittest
from urllib.parse import unquote, urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class OriginalLearningPageTests(unittest.TestCase):
    def test_page_is_original_and_uses_no_os_layout_assets(self):
        text = (ROOT / 'learn/index.html').read_text()
        for required in ('小天说FDE', 'AI / FDE 学习与实践', '程序员', '学生 / 初学者', '业务背景', '不默认包含免费完整诊断'):
            self.assertIn(required, text)
        for forbidden in ('win95', 'esther', 'desktop.js', 'topics.css', '<form', '/Volumes/', '/Users/'):
            self.assertNotIn(forbidden, text)
        self.assertIn('willeai.cn/services/', text)
        self.assertIn('ai-fde-diagnosis', text)
        self.assertNotIn('ai-fde-diagnosi"', text)

    def test_styles_and_scripts_exist_and_keyboard_controls_are_native(self):
        text = (ROOT / 'learn/index.html').read_text()
        class Elements(HTMLParser):
            def __init__(self): super().__init__(); self.items=[]
            def handle_starttag(self, tag, attrs): self.items.append((tag, dict(attrs)))
        page = Elements(); page.feed(text)
        modes = [attrs for tag, attrs in page.items if tag == 'input']
        self.assertEqual(len(modes), 3)
        self.assertTrue(all(item['type'] == 'radio' and item['name'] == 'track' for item in modes))
        for tag, attrs in page.items:
            value = attrs.get('src') if tag in ('script', 'img') else attrs.get('href') if tag == 'link' else None
            if value and not urlsplit(value).netloc:
                relative = unquote(urlsplit(urljoin('https://willeai.com/learn/', value)).path)
                self.assertTrue((ROOT / relative.lstrip('/')).is_file(), value)
        self.assertTrue((ROOT / 'learn/实践.css').stat().st_size > 2000)

    def test_practice_tracks_update_real_content_without_external_requests(self):
        result = subprocess.run(['node', str(ROOT / 'tests/learning.test.cjs')], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__': unittest.main()
