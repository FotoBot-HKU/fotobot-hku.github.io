"""Render the local blog.md into a self-contained GitHub Pages website."""

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


class MediaRenderer(HTMLParser):
    """Keep raw HTML embeds while replacing unavailable original MP4 links."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.parts: list[str] = []
        self.video_source: str | None = None

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
                attrs["aria-label"] = label
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
        if tag == "video" and self.video_source:
            path = ROOT / unquote(self.video_source)
            size = path.stat().st_size / (1024 * 1024)
            self.parts.append(
                f'<p class="video-file"><a href="{escape(self.video_source)}">'
                f"Open video file <span>({size:.1f} MiB)</span></a></p>"
            )
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
    def __init__(self) -> None:
        super().__init__()
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
            if not path.is_relative_to(ROOT) or not path.is_file():
                raise ValueError(f"Missing or out-of-repository resource: {value}")
            if path.stat().st_size > 100 * 1024 * 1024:
                raise ValueError(f"Resource exceeds GitHub's 100 MiB limit: {value}")


def build(source: Path) -> None:
    original = source.read_text(encoding="utf-8-sig")
    metadata: dict[str, str] = {}

    def extract_metadata(match: re.Match) -> str:
        metadata[match.group(1).lower()] = match.group(2).strip()
        return ""

    prose = re.sub(
        r"^\*\*(Author|Date|Team|Institute):\*\*[ \t]*(.+)$",
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
            token.attrSet("id", slug)
        # One page-level h1 lives in the template; retain section hierarchy.
        if token.type in {"heading_open", "heading_close"} and token.tag == "h1":
            token.tag = "h2"

    media = MediaRenderer()
    media.feed(markdown.renderer.render(tokens, markdown.options, {}))
    media.close()
    details = "".join(
        f'<div><dt>{label}</dt><dd>{escape(metadata[key])}</dd></div>'
        for key, label in (("team", "Team"), ("institute", "Institutions"))
        if metadata.get(key)
    )
    byline = " · ".join(
        escape(metadata[key]) for key in ("author", "date") if metadata.get(key)
    )
    contact_link = (
        f'<a href="mailto:{escape(email, quote=True)}">Contact</a>' if email else ""
    )
    contact_button = (
        f'<a class="button contact-button" href="mailto:{escape(email, quote=True)}">'
        "Get in touch</a>" if email else ""
    )
    template = Template((ROOT / "templates" / "page.html").read_text(encoding="utf-8"))
    page = template.substitute(
        content="".join(media.parts),
        byline=byline,
        details=details,
        contact_link=contact_link,
        contact_button=contact_button,
    )
    validator = LinkValidator()
    validator.feed(page)
    validator.validate()
    expected_videos = len(re.findall(r"<video\b", original, flags=re.IGNORECASE))
    if validator.video_count != expected_videos:
        raise ValueError("The generated video count does not match blog.md")
    for path in ROOT.rglob("*.webm"):
        if path.stat().st_size > 100 * 1024 * 1024:
            raise ValueError(f"Video exceeds GitHub's 100 MiB limit: {path.name}")

    # Keep the published repository independent from the surrounding workspace.
    if source.resolve() != (ROOT / "blog.md").resolve():
        (ROOT / "blog.md").write_text(original, encoding="utf-8")
    (ROOT / "index.html").write_text(page, encoding="utf-8", newline="\n")
    print(f"Built index.html from {source.name}; validated {validator.video_count} videos and all local links.")


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
