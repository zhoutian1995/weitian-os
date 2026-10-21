"""Refresh GEO metadata and breadcrumb labels without changing article prose."""

import argparse
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://willeai.com/"
PERSON_ID = ORIGIN + "#person"
DEFAULT_IMAGE = ORIGIN + "assets/weitian/wille-portrait.jpg"
ARTICLE_IMAGE = ORIGIN + "topics/assets/images/fde-flow.png"

SHORT_NAMES = {
    "fde-what-is": "FDE 是什么",
    "fde-seven-capabilities": "FDE 的七种能力",
    "fde-dual-loop": "FDE 双循环",
    "fde-first-battle": "企业 AI 第一仗",
    "fde-daily-work": "FDE 每天在忙什么",
    "one-person-fde-myth": "一人 FDE 伪命题",
    "fde-vs-consultant": "AI FDE 与传统顾问",
    "fde-frontline-degradation": "FDE 的四种退化",
    "fde-karpathy-output-spec": "Karpathy 输出规范",
    "fde-price-boundary": "FDE 凭什么贵",
    "fde-not-outsourcing": "FDE 不是外包",
    "fde-verify-ai-done": "AI 说做完了",
    "ai-as-employee": "把 AI 当成员工",
    "technology-value-shift": "技术贬值之后",
    "ai-era-not-stuck-in-role": "AI 时代别困在岗位里",
    "fde-what-to-learn": "程序员转 FDE 学什么",
    "layoff-resignation-story": "被裁三次裸辞",
    "tokens-cheap-future": "Tokens 像自来水",
    "agent-running-dumber": "AI Agent 越跑越笨",
    "ai-coding-subtraction": "AI 编程做减法",
    "agent-gets-own-computer": "AI 领电脑上岗",
    "model-brain-skill-toolbox": "模型与工具箱",
    "agent-layer-model": "企业 Agent 分层",
    "agent-era-enterprise-it": "Agent 时代的企业信息化",
    "codex-not-baidu": "别把 Codex 当百度",
    "claude-code-source-notes": "读 Claude Code 源码",
    "picoclaw-arm-port": "PicoClaw ARM 移植",
    "remote-agent-rescue": "远程救场 Agent",
    "growth-compass-launch": "成长指南针上线",
    "parkinghub-tool": "借车位小工具",
    "cyber-hub-experiment": "双轨制网站实验",
    "gpt-live-english-method": "GPT-Live 练英语",
    "manufacturing-fde-field": "FDE 主战场在工厂",
    "manufacturing-fde-cost": "制造业 FDE 成本",
}


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.text = text
        self.lines = [0]
        for line in text.splitlines(keepends=True):
            self.lines.append(self.lines[-1] + len(line))
        self.metadata = {}
        self.scripts = []
        self.icons = []
        self.head_end = None
        self.in_head = False
        self.script_start = None
        self.in_breadcrumb = False
        self.label_start = None
        self.breadcrumb_label = None
        self.feed(text)
        self.close()
        if self.head_end is None or len(self.scripts) != 1:
            raise ValueError("Expected one head and one JSON-LD script")

    def source_offset(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "head":
            self.in_head = True
        if tag == "nav" and "breadcrumb" in attrs.get("class", "").split():
            self.in_breadcrumb = True
        if self.in_breadcrumb and tag == "span" and not attrs.get("class"):
            self.label_start = self.source_offset() + len(self.get_starttag_text())
        if not self.in_head:
            return
        start = self.source_offset()
        end = start + len(self.get_starttag_text())
        if tag == "meta":
            key = attrs.get("property", attrs.get("name"))
            if key:
                if key in self.metadata:
                    raise ValueError("Duplicate metadata: " + key)
                self.metadata[key] = (start, end, attrs.get("content", ""))
        if tag == "link" and attrs.get("rel") == "icon":
            self.icons.append(attrs)
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.script_start = (start, end)

    def handle_endtag(self, tag):
        if tag == "span" and self.label_start is not None:
            self.breadcrumb_label = (self.label_start, self.source_offset())
            self.label_start = None
        if tag == "nav":
            self.in_breadcrumb = False
        if tag == "head":
            self.head_end = self.source_offset()
            self.in_head = False
        if tag == "script" and self.script_start is not None:
            start, content_start = self.script_start
            content_end = self.source_offset()
            end = self.text.index(">", content_end) + 1
            self.scripts.append((start, end, json.loads(self.text[content_start:content_end])))
            self.script_start = None

    def meta(self, key):
        return self.metadata.get(key, (0, 0, ""))[2]

    def nodes(self):
        document = self.scripts[0][2]
        return document.get("@graph", [document])

    def render(self, nodes, image, breadcrumb_label=None):
        document = {"@context": "https://schema.org", "@graph": nodes}
        payload = json.dumps(document, ensure_ascii=False, indent=2).replace("<", "\\u003c")
        start, end, _ = self.scripts[0]
        changes = [(start, end, '<script type="application/ld+json">\n' + payload + '\n</script>')]
        additions = []
        metadata = {
            "og:image": image,
            "twitter:card": "summary_large_image",
            "twitter:title": self.meta("og:title"),
            "twitter:description": self.meta("og:description"),
            "twitter:image": image,
        }
        for key, value in metadata.items():
            if not value:
                raise ValueError("Missing metadata source: " + key)
            attr = "property" if key.startswith("og:") else "name"
            markup = f'<meta {attr}="{key}" content="{html.escape(value, quote=True)}">'
            if key in self.metadata:
                start, end, _ = self.metadata[key]
                changes.append((start, end, markup))
            else:
                additions.append(markup)
        if not self.icons:
            additions.append('<link rel="icon" type="image/png" href="/favicon.png">')
        if additions:
            changes.append((self.head_end, self.head_end, "\n".join(additions) + "\n"))
        if breadcrumb_label is not None:
            if self.breadcrumb_label is None:
                raise ValueError("Missing visible breadcrumb label")
            start, end = self.breadcrumb_label
            changes.append((start, end, html.escape(breadcrumb_label)))
        text = self.text
        for start, end, replacement in sorted(changes, reverse=True):
            text = text[:start] + replacement + text[end:]
        return text


def one(nodes, kind):
    matches = [node for node in nodes if node.get("@type") == kind]
    if len(matches) != 1:
        raise ValueError(f"Expected one {kind}, found {len(matches)}")
    return matches[0]


def refreshed_pages(root):
    home = Page((root / "index.html").read_text(encoding="utf-8"))
    person = dict(one(home.nodes(), "Person"))
    person.pop("@context", None)
    person["@id"] = PERSON_ID
    website = {
        "@type": "WebSite", "@id": ORIGIN + "#website",
        "name": home.meta("og:site_name"), "url": ORIGIN,
        "inLanguage": "zh-CN", "publisher": {"@id": PERSON_ID},
    }
    urls = [node.text for node in ET.parse(root / "sitemap.xml").getroot().findall("{*}url/{*}loc")]
    updates = []
    for url in urls:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc != "willeai.com":
            raise ValueError("Unexpected sitemap URL: " + url)
        path = (root / unquote(parsed.path).lstrip("/")).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Sitemap path escapes root: " + url)
        if path.is_dir():
            path /= "index.html"
        original = path.read_text(encoding="utf-8")
        page = Page(original)
        nodes = page.nodes()
        articles = [node for node in nodes if node.get("@type") == "Article"]
        image = page.meta("og:image") or DEFAULT_IMAGE
        if articles and image == DEFAULT_IMAGE:
            image = ARTICLE_IMAGE
        label = None
        if url == ORIGIN:
            nodes = [person, website, *[node for node in nodes if node.get("@type") not in ("Person", "WebSite")]]
        elif articles:
            article = dict(one(nodes, "Article"))
            label = SHORT_NAMES.get(path.stem, article["headline"])
            article.update({"author": {"@id": PERSON_ID}, "publisher": {"@id": PERSON_ID},
                            "image": image, "description": page.meta("description")})
            breadcrumb = {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "首页", "item": ORIGIN},
                    {"@type": "ListItem", "position": 2, "name": "全部文章", "item": ORIGIN + "topics/"},
                    {"@type": "ListItem", "position": 3, "name": article["headline"], "item": url},
                ],
            }
            nodes = [person, article, breadcrumb, *[node for node in nodes if node.get("@type") not in ("Person", "Article", "BreadcrumbList")]]
        else:
            collection = dict(one(nodes, "CollectionPage"))
            collection.pop("@context", None)
            collection["publisher"] = {"@id": PERSON_ID}
            nodes = [person, collection, *[node for node in nodes if node.get("@type") not in ("Person", "CollectionPage")]]
        updates.append((path, original, page.render(nodes, image, label)))
    return updates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check generated metadata without writing")
    args = parser.parse_args()
    updates = refreshed_pages(ROOT)
    changed = [(path, old, new) for path, old, new in updates if old != new]
    if args.check:
        for path, _, _ in changed:
            print("Stale GEO metadata: " + str(path.relative_to(ROOT)))
        return int(bool(changed))
    for path, original, _ in changed:
        if path.read_text(encoding="utf-8") != original:
            raise RuntimeError("File changed during generation: " + str(path))
    for path, _, text in changed:
        path.write_text(text, encoding="utf-8")
    print(f"Refreshed {len(changed)} of {len(updates)} sitemap pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
