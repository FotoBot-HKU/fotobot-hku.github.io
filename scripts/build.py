"""Render English and Chinese Markdown into a static GitHub Pages website."""

from __future__ import annotations

import argparse
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
from string import Template
from urllib.parse import quote, unquote, urlsplit

from markdown_it import MarkdownIt


ROOT = Path(__file__).resolve().parents[1]
POSTERS = {
    "大维版demo.webm": ("fotobot.jpg", "FotoBot photography prototype"),
    "pixbot-demo-tech--ruixing.webm": ("vlog.jpg", "Robotic vlog recording"),
    "LEAP nature_cities_final.webm": ("leap.jpg", "LEAP pipeline and results"),
    "5_one_day_deployment.webm": ("deployment.jpg", "One day deployment"),
}
CHINESE_VIDEO_LABELS = {
    "大维版demo.webm": "FotoBot 摄影机器人原型",
    "pixbot-demo-tech--ruixing.webm": "机器人 vlog 拍摄",
    "LEAP nature_cities_final.webm": "LEAP 系统流程与成果概览",
    "5_one_day_deployment.webm": "深圳人才公园一日实地部署",
}
PAGE_TEXT = {
    "en": {
        "page_title": "FotoBot-HKU | Robots as creative partners",
        "description": "The FotoBot series explores robots as creative partners through autonomous photography, videography, and personalised creative assistance.",
        "social_description": "Robotic photography and videography guided by personal intentions and aesthetic preferences.",
        "canonical": "https://fotobot-hku.github.io/",
        "og_locale": "en_US",
        "skip_label": "Skip to content",
        "nav_label": "Main navigation",
        "about_label": "About",
        "work_label": "Our work",
        "contact_label": "Contact",
        "eyebrow": "Robotic photography & videography",
        "subtitle": "Robots as creative partners",
        "explore_label": "Explore our work",
        "contact_button_label": "Get in touch",
        "team_label": "Team",
        "institutions_label": "Institutions",
        "language_href": "zh.html",
        "language_target": "zh-CN",
        "language_label": "中文",
        "language_switch_label": "Switch to Chinese / 切换到中文",
        "footer_prefix": "Page structure adapted from the",
        "footer_using": ", using",
        "footer_end": ".",
    },
    "zh-CN": {
        "page_title": "FotoBot-HKU | 让机器人成为创作伙伴",
        "description": "FotoBot 系列探索通过自主摄影、视频拍摄和个性化创作辅助，让机器人成为人们的创作伙伴。",
        "social_description": "理解个人意图与审美偏好的机器人摄影及视频拍摄。",
        "canonical": "https://fotobot-hku.github.io/zh.html",
        "og_locale": "zh_CN",
        "skip_label": "跳转到正文",
        "nav_label": "主导航",
        "about_label": "关于项目",
        "work_label": "研究成果",
        "contact_label": "联系我们",
        "eyebrow": "机器人摄影与视频拍摄",
        "subtitle": "让机器人成为创作伙伴",
        "explore_label": "探索研究成果",
        "contact_button_label": "联系我们",
        "team_label": "团队",
        "institutions_label": "机构",
        "language_href": "index.html",
        "language_target": "en",
        "language_label": "English",
        "language_switch_label": "切换到英文 / Switch to English",
        "footer_prefix": "页面结构改编自",
        "footer_using": "，使用",
        "footer_end": "。",
    },
}


class MediaRenderer(HTMLParser):
    """Keep raw HTML embeds while replacing unavailable original MP4 links."""

    def __init__(self, language: str = "en") -> None:
        super().__init__(convert_charrefs=False)
        self.parts: list[str] = []
        self.video_source: str | None = None
        self.language = language

    def handle_starttag(self, tag: str, attributes: list) -> None:
        attrs = dict(attributes)
        if tag == "video":
            self.video_source = quote(unquote(attrs["src"]), safe="/:")
            attrs["src"] = self.video_source
            attrs["controls"] = None
            attrs["playsinline"] = None
            attrs["preload"] = "metadata"
            attrs.pop("width", None)
            filename = Path(unquote(self.video_source)).name
            if filename in POSTERS:
                poster, label = POSTERS[filename]
                attrs["poster"] = f"static/images/{poster}"
                attrs["aria-label"] = (
                    CHINESE_VIDEO_LABELS[filename] if self.language == "zh-CN" else label
                )
        if tag == "a" and self.video_source and attrs.get("href", "").endswith(".mp4"):
            attrs["href"] = self.video_source
        rendered = "".join(
            f" {key}" if value is None else f' {key}="{escape(value, quote=True)}"'
            for key, value in attrs.items()
        )
        self.parts.append(f"<{tag}{rendered}>")

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        self.parts.append(f"</{tag}>")
        if tag == "video":
            self.video_source = None

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.parts.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        self.parts.append(f"<!--{data}-->")


class LinkValidator(HTMLParser):
    def __init__(self, generated_files: tuple[str, ...] = ()) -> None:
        super().__init__()
        self.generated_files = {(ROOT / name).resolve() for name in generated_files}
        self.links: list[str] = []
        self.ids: set[str] = set()
        self.video_count = 0

    def handle_starttag(self, tag: str, attributes: list) -> None:
        attrs = dict(attributes)
        if "id" in attrs:
            if attrs["id"] in self.ids:
                raise ValueError(f"Duplicate HTML id: {attrs['id']}")
            self.ids.add(attrs["id"])
        if tag == "video":
            self.video_count += 1
        # Canonical links describe the remote site, not a local asset.
        if tag == "link" and attrs.get("rel") == "canonical":
            return
        for name in ("src", "href", "poster"):
            if attrs.get(name):
                self.links.append(attrs[name])

    def validate(self) -> None:
        for value in self.links:
            url = urlsplit(value)
            if url.scheme or url.netloc:
                continue
            if not url.path:
                if url.fragment and unquote(url.fragment) not in self.ids:
                    raise ValueError(f"Missing section anchor: {value}")
                continue
            path = (ROOT / unquote(url.path)).resolve()
            if path in self.generated_files:
                continue
            if not path.is_relative_to(ROOT) or not path.is_file():
                raise ValueError(f"Missing or out-of-repository resource: {value}")
            if path.stat().st_size > 100 * 1024 * 1024:
                raise ValueError(f"Resource exceeds GitHub's 100 MiB limit: {value}")


def render_page(source: Path, language: str) -> str:
    original = source.read_text(encoding="utf-8-sig")
    text = PAGE_TEXT[language]
    metadata: dict[str, str] = {}

    def extract_metadata(match: re.Match) -> str:
        key = match.group(1).lower()
        metadata["institute" if key == "institutions" else key] = match.group(2).strip()
        return ""

    prose = re.sub(
        r"^\*\*(Author|Date|Team|Institute|Institutions):\*\*[ \t]*(.+)$",
        extract_metadata,
        original,
        flags=re.MULTILINE,
    )
    email_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", prose)
    email = email_match.group() if email_match else ""
    if email:
        prose = prose.replace(f"({email})", f"([{email}](mailto:{email}))")

    # Raw video blocks need paragraph boundaries even when the editor source
    # places them directly after a developer credit or a numbered caption.
    prose = re.sub(r"(?m)^[ \t]*(<video\b)", r"\n\1", prose)
    prose = re.sub(r"(</video>)[ \t]*", r"\1\n", prose)

    markdown = MarkdownIt("commonmark", {"html": True})
    tokens = markdown.parse(prose)
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            inline = tokens[index + 1]
            label = re.sub(r"<[^>]+>", "", inline.content).strip()
            slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
            # Explicit anchors in translated headings keep navigation stable.
            # Chinese-only headings may have no ASCII slug at all.
            if slug and (language == "en" or not re.search(r"<a\b[^>]*\bid=", inline.content)):
                token.attrSet("id", slug)
        # One page-level h1 lives in the template; retain section hierarchy.
        if token.type in {"heading_open", "heading_close"} and token.tag == "h1":
            token.tag = "h2"

    media = MediaRenderer(language)
    media.feed(markdown.renderer.render(tokens, markdown.options, {}))
    media.close()
    details = "".join(
        f'<div><dt>{label}</dt><dd>{markdown.renderInline(metadata[key]) if key == "team" else escape(metadata[key])}</dd></div>'
        for key, label in (
            ("team", text["team_label"]), ("institute", text["institutions_label"])
        )
        if metadata.get(key)
    )
    byline = " · ".join(
        markdown.renderInline(metadata[key]) if key == "author" else escape(metadata[key])
        for key in ("author", "date") if metadata.get(key)
    )
    contact_link = (
        f'<a href="mailto:{escape(email, quote=True)}">{text["contact_label"]}</a>'
        if email else ""
    )
    contact_button = (
        f'<a class="button contact-button" href="mailto:{escape(email, quote=True)}">'
        f'{text["contact_button_label"]}</a>' if email else ""
    )
    footer_credit = (
        f'{text["footer_prefix"]} '
        '<a href="https://github.com/eliahuhorwitz/Academic-project-page-template">'
        'Academic Project Page Template</a> '
        '(<a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>)'
        f'{text["footer_using"]} <a href="https://bulma.io/">Bulma</a>'
        f'{text["footer_end"]}'
    )
    template = Template((ROOT / "templates" / "page.html").read_text(encoding="utf-8"))
    page = template.substitute(
        **{key: escape(value, quote=True) for key, value in text.items()},
        lang=language,
        content="".join(media.parts),
        byline=byline,
        details=details,
        contact_link=contact_link,
        contact_button=contact_button,
        footer_credit=footer_credit,
    )
    validator = LinkValidator(("index.html", "zh.html"))
    validator.feed(page)
    validator.validate()
    expected_videos = len(re.findall(r"<video\b", original, flags=re.IGNORECASE))
    if validator.video_count != expected_videos:
        raise ValueError(f"The generated video count does not match {source.name}")
    return page


def build(source: Path) -> None:
    pages = {
        "index.html": render_page(source, "en"),
        "zh.html": render_page(ROOT / "blog.zh-CN.md", "zh-CN"),
    }
    for path in ROOT.rglob("*.webm"):
        if path.stat().st_size > 100 * 1024 * 1024:
            raise ValueError(f"Video exceeds GitHub's 100 MiB limit: {path.name}")

    # Keep the published repository independent from the surrounding workspace.
    if source.resolve() != (ROOT / "blog.md").resolve():
        (ROOT / "blog.md").write_text(source.read_text(encoding="utf-8-sig"), encoding="utf-8")
    for filename, page in pages.items():
        (ROOT / filename).write_text(page, encoding="utf-8", newline="\n")
    print("Built index.html and zh.html; validated video counts and all local links in both languages.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", type=Path, default=ROOT / "blog.md",
        help="Markdown source to import; defaults to this repository's blog.md",
    )
    arguments = parser.parse_args()
    try:
        build(arguments.source.resolve())
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Build failed: {error}\n")
