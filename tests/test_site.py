"""Check the published static site without third-party dependencies."""

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import sys
import unittest
from urllib.parse import unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://willeai.com/"


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.elements = []
        self.head_elements = []
        self.title = ""
        self.groups = []
        self.articles = []
        self.json_ld = []
        self.body_links = []
        self.related_links = []
        self.body_depth = 0
        self.in_breadcrumb = False
        self.in_breadcrumb_label = False
        self.breadcrumb_label = ""
        self.in_head = False
        self.capture = None
        self.buffer = []
        self.feed(path.read_text(encoding="utf-8"))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements.append((tag, attrs))
        if tag == "head":
            self.in_head = True
        if self.in_head:
            self.head_elements.append((tag, attrs))
        classes = attrs.get("class", "").split()
        if tag == "nav" and "breadcrumb" in classes:
            self.in_breadcrumb = True
        if tag == "span" and self.in_breadcrumb and not classes:
            self.in_breadcrumb_label = True
        if tag == "div" and (self.body_depth or "article-body" in classes):
            self.body_depth += 1
        if tag == "a" and self.body_depth:
            self.body_links.append(attrs.get("href", ""))
        if tag == "a" and "related-item" in classes:
            self.related_links.append(attrs.get("href", ""))
        if tag == "title" or (tag == "script" and attrs.get("type") == "application/ld+json"):
            self.capture = tag
            self.buffer = []
        elif tag == "h2" and "section-title" in classes:
            self.capture = "h2"
            self.buffer = []
            self.groups.append({"label": "", "links": []})
        if tag == "a" and "topic-card" in classes:
            self.articles.append(attrs["href"])
            self.groups[-1]["links"].append(attrs["href"])

    def handle_data(self, data):
        if self.in_breadcrumb_label:
            self.breadcrumb_label += data
        if self.capture:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag == "span":
            self.in_breadcrumb_label = False
        if tag == "nav":
            self.in_breadcrumb = False
        if tag == "div" and self.body_depth:
            self.body_depth -= 1
        if tag == "head":
            self.in_head = False
        if tag == self.capture:
            text = "".join(self.buffer)
            if tag == "title":
                self.title = text
            elif tag == "script":
                self.json_ld.append(json.loads(text))
            elif tag == "h2":
                self.groups[-1]["label"] = text
            self.capture = None

    def metadata(self, key):
        return [attrs["content"] for tag, attrs in self.head_elements
                if tag == "meta" and (attrs.get("name") == key or attrs.get("property") == key)]

    def canonicals(self):
        return [attrs["href"] for tag, attrs in self.head_elements
                if tag == "link" and attrs.get("rel") == "canonical"]


def local_path(url):
    path = ROOT / unquote(urlsplit(url).path).lstrip("/")
    return path / "index.html" if path.is_dir() else path


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = Page(ROOT / "topics/index.html")
        cls.article_urls = [urljoin(ORIGIN + "topics/", href) for href in cls.catalog.articles]
        cls.sitemap = [node.text for node in ET.parse(ROOT / "sitemap.xml").getroot()
                       .findall("{*}url/{*}loc")]
        cls.pages = {url: Page(local_path(url)) for url in cls.sitemap}

    def test_catalog_and_sitemap_match(self):
        self.assertEqual(len(self.article_urls), len(set(self.article_urls)))
        self.assertCountEqual(self.sitemap, [ORIGIN, ORIGIN + "topics/", *self.article_urls])

    def test_catalog_counts(self):
        count = len(self.article_urls)
        for label in [self.catalog.title, *self.catalog.metadata("description")]:
            with self.subTest(label=label):
                self.assertEqual(re.findall(r"(\d+)\s*篇", label), [str(count)])
        for group in self.catalog.groups:
            with self.subTest(group=group["label"]):
                self.assertEqual(re.findall(r"(\d+)\s*篇", group["label"]), [str(len(group["links"]))])

    def test_llms_matches_catalog(self):
        text = (ROOT / "llms.txt").read_text(encoding="utf-8")
        articles = re.findall(r"^- \[[^\]]+\]\((https://willeai\.com/topics/[^)]+\.html)\)", text, re.M)
        self.assertCountEqual(articles, self.article_urls)
        self.assertTrue(all(int(value) == len(articles) for value in re.findall(r"(\d+)\s*篇", text)))

    def test_unique_metadata_and_canonical(self):
        for url, page in self.pages.items():
            with self.subTest(url=url):
                self.assertEqual(page.canonicals(), [url])
                for key in ("description", "og:title", "og:description", "og:type", "og:url"):
                    self.assertEqual(len(page.metadata(key)), 1, key)
                    self.assertTrue(page.metadata(key)[0].strip(), key)
                self.assertEqual(page.metadata("og:url"), [url])
                for key in ("og:image", "og:site_name", "twitter:title", "twitter:image"):
                    self.assertLessEqual(len(page.metadata(key)), 1, key)
                allowed = {"charset", "name", "property", "content", "http-equiv"}
                for tag, attrs in page.head_elements:
                    if tag == "meta":
                        self.assertFalse(set(attrs) - allowed, f"Malformed meta attributes at {url}")
                self.assertTrue(page.json_ld)
                nodes = [node for document in page.json_ld
                         for node in document.get("@graph", [document])]
                people = {node["@id"]: node for node in nodes if "@id" in node}
                for node in nodes:
                    if node.get("@type") == "Article":
                        self.assertEqual(node["mainEntityOfPage"], url)
                        author = node["author"]
                        if "@id" in author:
                            author = people[author["@id"]]
                        self.assertEqual(author["name"], "小天说FDE")

    def test_social_metadata(self):
        for url, page in self.pages.items():
            with self.subTest(url=url):
                self.assertEqual(page.metadata("twitter:card"), ["summary_large_image"])
                for key in ("og:image", "twitter:image", "twitter:title", "twitter:description"):
                    self.assertEqual(len(page.metadata(key)), 1, key)
                    self.assertTrue(page.metadata(key)[0].strip(), key)
                self.assertEqual(page.metadata("twitter:image"), page.metadata("og:image"))
                self.assertTrue(local_path(page.metadata("og:image")[0]).is_file())
                self.assertEqual(sum(tag == "link" and attrs.get("rel") == "icon"
                                     for tag, attrs in page.head_elements), 1)

    def test_article_schema_consistency(self):
        for url in self.article_urls:
            with self.subTest(url=url):
                page = self.pages[url]
                nodes = [node for document in page.json_ld
                         for node in document.get("@graph", [document])]
                self.assertCountEqual([node["@type"] for node in nodes],
                                      ["Person", "Article", "BreadcrumbList", "FAQPage"])
                by_type = {node["@type"]: node for node in nodes}
                person = by_type["Person"]
                article = by_type["Article"]
                self.assertEqual(person["@id"], ORIGIN + "#person")
                self.assertEqual(article["author"], {"@id": person["@id"]})
                self.assertEqual(article["publisher"], article["author"])
                self.assertEqual(article["image"], page.metadata("og:image")[0])
                self.assertEqual(article["description"], page.metadata("description")[0])
                crumbs = by_type["BreadcrumbList"]["itemListElement"]
                self.assertEqual([item["position"] for item in crumbs], [1, 2, 3])
                self.assertEqual([item["item"] for item in crumbs], [ORIGIN, ORIGIN + "topics/", url])
                self.assertEqual(crumbs[-1]["name"], article["headline"])

    def test_personal_website_schema_and_headings(self):
        home = self.pages[ORIGIN]
        nodes = [node for document in home.json_ld for node in document.get("@graph", [document])]
        self.assertCountEqual([node["@type"] for node in nodes], ["Person", "WebSite"])
        website = next(node for node in nodes if node["@type"] == "WebSite")
        self.assertEqual(website["url"], ORIGIN)
        self.assertEqual(website["name"], home.metadata("og:site_name")[0])
        self.assertEqual(website["inLanguage"], "zh-CN")
        self.assertEqual(website["publisher"], {"@id": ORIGIN + "#person"})
        self.assertEqual(sum(tag == "h1" for tag, _ in home.elements), 1)

    def test_priority_article_citations_and_links(self):
        stems = ("fde-what-is", "claude-code-source-notes", "agent-running-dumber",
                 "fde-seven-capabilities", "ai-coding-subtraction", "model-brain-skill-toolbox",
                 "remote-agent-rescue", "picoclaw-arm-port")
        for stem in stems:
            url = ORIGIN + "topics/" + stem + ".html"
            page = self.pages[url]
            with self.subTest(url=url):
                sources = {href for href in page.body_links
                           if urlsplit(href).scheme == "https"
                           and urlsplit(href).netloc not in ("willeai.com", "willeai.cn")}
                self.assertGreaterEqual(len(sources), 2)
                related = {href for href in page.related_links if href in self.article_urls}
                self.assertEqual(len(related), 3)
                self.assertNotIn(url, related)

    def test_generated_geo_metadata_is_current(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/refresh_geo.py"), "--check"],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_breadcrumb_labels_are_short(self):
        for url in self.article_urls:
            with self.subTest(url=url):
                label = self.pages[url].breadcrumb_label
                self.assertTrue(label.strip())
                self.assertLessEqual(len(label), 16)
                self.assertNotIn("...", label)

    def test_internal_links_and_assets_exist(self):
        for url, page in self.pages.items():
            for tag, attrs in page.elements:
                for key in ("href", "src"):
                    value = attrs.get(key)
                    if not value or value.startswith("#"):
                        continue
                    target = urljoin(url, value)
                    if urlsplit(target).netloc != "willeai.com":
                        continue
                    with self.subTest(page=url, target=target, tag=tag):
                        self.assertTrue(local_path(target).is_file())

    def test_stylesheet_cache_version(self):
        expected = hashlib.sha256((ROOT / "topics/assets/topics.css").read_bytes()).hexdigest()[:12]
        for url, page in self.pages.items():
            if url == ORIGIN:
                continue
            links = [attrs["href"] for tag, attrs in page.head_elements
                     if tag == "link" and urlsplit(attrs.get("href", "")).path == "assets/topics.css"]
            with self.subTest(url=url):
                self.assertEqual(len(links), 1)
                self.assertEqual(urlsplit(links[0]).query, "v=" + expected)

    def test_current_coding_case(self):
        text = (ROOT / "topics/ai-coding-subtraction.html").read_text(encoding="utf-8")
        self.assertIn("自动上下架", text)
        self.assertNotIn("企业微信销售助理", text)

    def test_home_article_count(self):
        home = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"(\d+) 篇 · 查看全部", home), [str(len(self.article_urls))])

    def test_article_formatting(self):
        for url in self.article_urls:
            with self.subTest(url=url):
                text = local_path(url).read_text(encoding="utf-8")
                self.assertFalse("**" in text, f"Unrendered emphasis: {url}")
                self.assertFalse("<p>---</p>" in text, f"Unrendered separator: {url}")
                self.assertIsNone(re.search(r"<p>\|.*\|</p>", text), "Unrendered table")
                for private_marker in ("/Volumes/", "/Users/", "原稿恢复（"):
                    self.assertFalse(private_marker in text, f"Internal provenance leaked: {url}")
        for name, headers, cells in (("fde-daily-work", 4, 16),
                                      ("fde-seven-capabilities", 4, 28),
                                      ("remote-agent-rescue", 4, 14)):
            with self.subTest(table=name):
                page = self.pages[ORIGIN + "topics/" + name + ".html"]
                self.assertEqual(sum(tag == "th" for tag, _ in page.elements), headers)
                self.assertEqual(sum(tag == "td" for tag, _ in page.elements), cells)


if __name__ == "__main__":
    unittest.main(verbosity=2)
