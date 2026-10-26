import hashlib
import json
from pathlib import Path
import unittest
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

from test_site import Page, ROOT, ORIGIN, local_path

QR = 'wecom-contact-764be1abb583.jpg'
QR_SHA = '764be1abb583342c876aef0641a0c81af890b3531e2946c7d2bf7078acd0661a'


class ConversionEntryTests(unittest.TestCase):
    def test_home_has_direct_learning_and_enterprise_routes(self):
        page = Page(ROOT / 'index.html')
        links = [attrs.get('href') for tag, attrs in page.elements if tag == 'a']
        self.assertIn('topics/#fde-start', links)
        self.assertIn('https://willeai.cn/services/#ai-start', links)
        self.assertIn('小天说FDE · 维天OS', (ROOT / 'index.html').read_text())

    def test_learning_entry_answers_the_first_steps_and_keeps_resources_optional(self):
        text = (ROOT / 'topics/index.html').read_text()
        page = Page(ROOT / 'topics/index.html')
        ids = {attrs.get('id') for _, attrs in page.elements}
        self.assertTrue({'fde-start', 'enterprise-start'} <= ids)
        for phrase in ('角色', '小任务', '异常样例', '不需要先领取', '入企诊断'):
            self.assertIn(phrase, text)

    def test_all_sitemap_contact_surfaces_use_owner_wecom_not_bot_auth(self):
        urls = [node.text for node in ET.parse(ROOT / 'sitemap.xml').getroot().findall('{*}url/{*}loc')]
        for url in urls:
            with self.subTest(url=url):
                page = Page(local_path(url))
                codes = [attrs for tag, attrs in page.elements if tag == 'img' and QR in attrs.get('src', '')]
                self.assertEqual(len(codes), 1)
                self.assertIn('本人', codes[0]['alt'])
                self.assertEqual((codes[0].get('width'), codes[0].get('height')), ('311', '304'))
                self.assertFalse(any('wechat-workflow-claim-' in attrs.get('src', '') for tag, attrs in page.elements if tag == 'img'))
                self.assertFalse(any('/ai/qc/' in attrs.get('src', '') for tag, attrs in page.elements if tag == 'img'))

    def test_contact_runtime_asset_has_original_bytes_and_provenance(self):
        path = ROOT / 'assets/weitian' / QR
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), QR_SHA)
        manifest = json.loads((ROOT / 'assets/weitian/asset-manifest.json').read_text())
        assets = next(value for value in manifest.values() if isinstance(value, list))
        matches = [item for item in assets if item['runtime'] == QR]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['sha256'], QR_SHA)
        self.assertEqual(matches[0]['transform'], 'none')

    def test_both_routes_are_in_machine_readable_navigation(self):
        text = (ROOT / 'llms.txt').read_text()
        self.assertIn('https://willeai.com/learn/', text)
        self.assertIn('https://willeai.cn/services/#ai-start', text)
        self.assertIn('不是内部提醒机器人', text)


if __name__ == '__main__':
    unittest.main()
