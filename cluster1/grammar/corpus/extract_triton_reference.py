"""Fetch and pin the official `triton.language` API reference.

The generated JSON is the permanent reference snapshot used by offline CI. This
script intentionally fails if the docs page cannot be fetched or if any listed
function page cannot be parsed.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


DEFAULT_URL = "https://triton-lang.org/main/python-api/triton.language.html"
DEFAULT_OUTPUT = Path("cluster1/grammar/corpus/triton_language_reference_vmain_2026_05_16.json")
EXTRACTION_VERSION = "2026-05-16.1"
NON_FUNCTION_PUBLIC_ENTRIES = {"tensor", "tensor_descriptor"}
FUNCTION_LIKE_CLASSES = {"range", "static_range"}
PRIVATE_REFERENCE_PARAMETERS = {"_semantic", "_generator"}


@dataclass(frozen=True)
class IndexEntry:
    name: str
    href: str
    section: str
    summary: str


class TritonLanguageIndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_main = False
        self.section_depth = 0
        self.pending_section_id: str | None = None
        self.current_section = ""
        self.in_heading = False
        self.heading_parts: list[str] = []
        self.capture_link: dict[str, str] | None = None
        self.link_parts: list[str] = []
        self.entries: list[IndexEntry] = []
        self._seen: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key: value or "" for key, value in attrs}
        if tag == "section" and attrs_dict.get("id") == "triton-language":
            self.in_main = True
            self.section_depth = 1
            return
        if not self.in_main:
            return
        if tag == "section":
            self.section_depth += 1
            self.pending_section_id = attrs_dict.get("id")
        elif tag == "h2":
            self.in_heading = True
            self.heading_parts = []
        elif tag == "a":
            href = attrs_dict.get("href", "")
            title = attrs_dict.get("title", "")
            if "generated/triton.language." in href and "#triton.language." in href:
                name = title.removeprefix("triton.language.")
                if name and name not in self._seen:
                    self.capture_link = {"name": name, "href": href}
                    self.link_parts = []

    def handle_endtag(self, tag: str) -> None:
        if not self.in_main:
            return
        if tag == "h2" and self.in_heading:
            heading = _normalize_text("".join(self.heading_parts))
            if heading:
                self.current_section = heading
            self.in_heading = False
            self.heading_parts = []
        elif tag == "a" and self.capture_link is not None:
            name = self.capture_link["name"]
            href = self.capture_link["href"].split("#", 1)[0]
            if name not in self._seen:
                self.entries.append(
                    IndexEntry(
                        name=name,
                        href=href,
                        section=self.current_section,
                        summary="",
                    )
                )
                self._seen.add(name)
            self.capture_link = None
            self.link_parts = []
        elif tag == "section":
            self.section_depth -= 1
            if self.section_depth <= 0:
                self.in_main = False

    def handle_data(self, data: str) -> None:
        if self.in_heading:
            self.heading_parts.append(data)
        if self.capture_link is not None:
            self.link_parts.append(data)


class SignatureParser(HTMLParser):
    def __init__(self, qualified_name: str) -> None:
        super().__init__()
        self.qualified_name = qualified_name
        self.capture_depth = 0
        self.parts: list[str] = []
        self.found = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key: value or "" for key, value in attrs}
        if tag == "dt" and attrs_dict.get("id") == self.qualified_name:
            self.capture_depth = 1
            self.found = True
            return
        if self.capture_depth:
            self.capture_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self.capture_depth:
            self.capture_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.capture_depth:
            self.parts.append(data)

    @property
    def signature(self) -> str:
        return _normalize_signature("".join(self.parts))


def fetch_reference(url: str, timestamp: str | None = None) -> dict[str, Any]:
    fetched_at = timestamp or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    index_html = _fetch_text(url)
    entries = _parse_index(index_html)
    if not entries:
        raise RuntimeError(f"no triton.language entries found in {url}")

    functions: list[dict[str, Any]] = []
    excluded_entries: list[dict[str, Any]] = []
    for entry in entries:
        page_url = urllib.parse.urljoin(url, entry.href)
        page_html = _fetch_text(page_url)
        signature = _parse_signature(page_html, f"triton.language.{entry.name}")
        kind, clean_signature = _classify_signature(signature)
        params = _parse_parameters(clean_signature)
        record = {
            "name": f"tl.{entry.name}",
            "reference_name": f"triton.language.{entry.name}",
            "kind": kind,
            "signature": clean_signature,
            "parameters": params,
            "parameter_names": [param["name"] for param in params],
            "kwargs": [
                param["name"]
                for param in params
                if param["name"] not in PRIVATE_REFERENCE_PARAMETERS
                and param["name"] != "self"
                and param["kind"] != "var_positional"
                and param["has_default"]
            ],
            "section": entry.section,
            "source_url": page_url,
        }
        if entry.name in NON_FUNCTION_PUBLIC_ENTRIES:
            excluded_entries.append(
                {
                    **record,
                    "exclusion_reason": "Public programming-model class, not a tl.* function call in the grammar allow-list.",
                }
            )
        elif kind == "class" and entry.name not in FUNCTION_LIKE_CLASSES:
            excluded_entries.append(
                {
                    **record,
                    "exclusion_reason": "Public class, not a function-like Triton language call.",
                }
            )
        else:
            functions.append(record)

    version = _infer_docs_version(url)
    return {
        "source_url": url,
        "docs_version": version,
        "source_title": _extract_title(index_html),
        "extraction_version": EXTRACTION_VERSION,
        "extraction_timestamp_utc": fetched_at,
        "function_count": len(functions),
        "functions": functions,
        "excluded_public_entries": excluded_entries,
    }


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "TritonGen-reference-extractor/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - official docs URL supplied by caller.
            status = getattr(response, "status", 200)
            if status != 200:
                raise RuntimeError(f"unexpected HTTP status {status} for {url}")
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"failed to fetch {url}: {exc}") from exc


def _parse_index(html: str) -> list[IndexEntry]:
    parser = TritonLanguageIndexParser()
    parser.feed(html)
    return parser.entries


def _parse_signature(html: str, qualified_name: str) -> str:
    parser = SignatureParser(qualified_name)
    parser.feed(html)
    if not parser.found or not parser.signature:
        raise RuntimeError(f"could not parse signature for {qualified_name}")
    return parser.signature


def _classify_signature(signature: str) -> tuple[str, str]:
    if signature.startswith("class "):
        return "class", signature.removeprefix("class ")
    return "function", signature


def _parse_parameters(signature: str) -> list[dict[str, Any]]:
    inside = _signature_inside_parentheses(signature)
    if inside == "":
        return []
    params: list[dict[str, Any]] = []
    for raw in _split_signature_args(inside):
        cleaned = raw.strip()
        if not cleaned:
            continue
        name_part = cleaned.split("=", 1)[0].split(":", 1)[0].strip()
        kind = "positional_or_keyword"
        if name_part.startswith("**"):
            kind = "var_keyword"
            name_part = name_part[2:]
        elif name_part.startswith("*"):
            kind = "var_positional"
            name_part = name_part[1:]
        params.append(
            {
                "name": name_part.strip(),
                "raw": cleaned,
                "kind": kind,
                "has_default": "=" in cleaned,
                "is_private": name_part.strip().startswith("_"),
            }
        )
    return params


def _signature_inside_parentheses(signature: str) -> str:
    start = signature.find("(")
    end = signature.rfind(")")
    if start < 0 or end < start:
        raise RuntimeError(f"signature has no parseable parameter list: {signature}")
    return signature[start + 1 : end]


def _split_signature_args(text: str) -> list[str]:
    args: list[str] = []
    start = 0
    depth = 0
    quote = ""
    escaped = False
    for index, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = ""
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            args.append(text[start:index])
            start = index + 1
    args.append(text[start:])
    return args


def _normalize_signature(text: str) -> str:
    text = unescape(text).replace("\xa0", " ").replace("", "")
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace(" ,", ",").replace("( ", "(").replace(" )", ")")
    text = text.replace(" =", "=").replace("= ", "=")
    text = text.replace(" -> ", " -> ")
    return text


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(text)).strip().replace("", "").strip()


def _extract_title(html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html, flags=re.DOTALL)
    if not match:
        return ""
    return _normalize_text(match.group(1))


def _infer_docs_version(url: str) -> str:
    path_parts = [part for part in urllib.parse.urlparse(url).path.split("/") if part]
    if "main" in path_parts:
        return "main"
    for part in path_parts:
        if re.fullmatch(r"v?\d+(?:\.\d+)*", part):
            return part
    return "unknown"


def _write_json(data: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--extraction-timestamp-utc",
        help="Optional pinned UTC timestamp for reproducible snapshot regeneration.",
    )
    args = parser.parse_args(argv)

    data = fetch_reference(args.url, timestamp=args.extraction_timestamp_utc)
    _write_json(data, args.output)
    print(f"wrote {args.output} ({len(data['functions'])} public tl.* call entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
