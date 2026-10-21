"""Regression checks for shared metadata generation and HTML-safe JSON."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("refresh_geo", ROOT / "scripts/refresh_geo.py")
GEO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GEO)


def sample_page(extra=""):
    return ('<!DOCTYPE html><html><head>\n'
            '<meta property="og:title" content="A &quot;quoted&quot; title">\n'
            '<meta property="og:description" content="A description">\n'
            + extra + '<script type="application/ld+json">\n'
            + json.dumps({"@context": "https://schema.org", "@type": "Person", "name": "Author"})
            + '\n</script>\n</head><body><p>Original body &amp; FAQ.</p></body></html>')


class MetadataTests(unittest.TestCase):
    def test_head_rewrite_preserves_body(self):
        original = sample_page()
        page = GEO.Page(original)
        result = page.render(page.nodes(), GEO.DEFAULT_IMAGE)
        self.assertEqual(original.split("</head>", 1)[1], result.split("</head>", 1)[1])
        parsed = GEO.Page(result)
        self.assertEqual(parsed.meta("twitter:title"), 'A "quoted" title')
        self.assertEqual(parsed.meta("og:image"), parsed.meta("twitter:image"))
        self.assertEqual(len(parsed.icons), 1)

    def test_render_is_idempotent(self):
        page = GEO.Page(sample_page())
        first = page.render(page.nodes(), GEO.DEFAULT_IMAGE)
        second = GEO.Page(first).render(page.nodes(), GEO.DEFAULT_IMAGE)
        self.assertEqual(first, second)

    def test_existing_social_fields_are_replaced_once(self):
        page = GEO.Page(sample_page('<meta name="twitter:card" content="summary">\n'
                                   '<meta property="og:image" content="https://example.com/old.png">\n'))
        result = page.render(page.nodes(), GEO.DEFAULT_IMAGE)
        self.assertEqual(result.count('name="twitter:card"'), 1)
        self.assertEqual(GEO.Page(result).meta("twitter:card"), "summary_large_image")
        self.assertNotIn("example.com/old.png", result)

    def test_duplicate_metadata_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Duplicate metadata"):
            GEO.Page(sample_page('<meta property="og:title" content="Duplicate">'))

    def test_script_delimiters_are_escaped(self):
        page = GEO.Page(sample_page())
        nodes = [{"@type": "Person", "name": '</script><img src="bad">'}]
        result = page.render(nodes, GEO.DEFAULT_IMAGE)
        self.assertNotIn('<img src="bad">', result)
        self.assertEqual(GEO.Page(result).nodes(), nodes)

    def test_breadcrumb_label_uses_element_spans(self):
        original = sample_page().replace("<body>", '<body><nav class="breadcrumb"><span class="sep">/</span><span>Cl</span></nav>')
        page = GEO.Page(original)
        refreshed = page.render(page.nodes(), GEO.DEFAULT_IMAGE, "Code & tools")
        self.assertIn("<span>Code &amp; tools</span>", refreshed)
        self.assertIn('<span class="sep">/</span>', refreshed)
        self.assertEqual(GEO.Page(refreshed).render(page.nodes(), GEO.DEFAULT_IMAGE, "Code & tools"), refreshed)

    def test_repository_generation_preserves_content_and_dates(self):
        updates = GEO.refreshed_pages(ROOT)
        for path, original, refreshed in updates:
            with self.subTest(path=str(path.relative_to(ROOT))):
                def body_without_label(text):
                    page = GEO.Page(text)
                    if page.breadcrumb_label:
                        start, end = page.breadcrumb_label
                        text = text[:start] + text[end:]
                    return text.split("</head>", 1)[1]

                self.assertEqual(body_without_label(original), body_without_label(refreshed))
                old = GEO.Page(original).nodes()
                new = GEO.Page(refreshed).nodes()
                for kind in ("Article", "FAQPage"):
                    before = [node for node in old if node.get("@type") == kind]
                    after = [node for node in new if node.get("@type") == kind]
                    if kind == "FAQPage":
                        self.assertEqual(before, after)
                    elif before:
                        for key in ("datePublished", "dateModified", "headline", "mainEntityOfPage"):
                            self.assertEqual(before[0][key], after[0][key])
        for _, _, refreshed in updates:
            page = GEO.Page(refreshed)
            image = page.meta("og:image")
            self.assertEqual(page.render(page.nodes(), image), refreshed)

    def test_check_does_not_write(self):
        paths = [path for path, _, _ in GEO.refreshed_pages(ROOT)]
        before = {path: path.stat().st_mtime_ns for path in paths}
        result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/refresh_geo.py"), "--check"],
                                capture_output=True, text=True, timeout=15)
        self.assertIn(result.returncode, (0, 1), result.stderr)
        self.assertEqual(before, {path: path.stat().st_mtime_ns for path in paths})


if __name__ == "__main__":
    unittest.main(verbosity=2)
