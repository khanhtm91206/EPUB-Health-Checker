"""Verify that the EPUB reading order points to usable XHTML content.

This is a structural readability preflight, NOT a real e-reader emulator.
Can run independently with check_path(), or through check(ctx) in Runner.
"""
from __future__ import annotations

import posixpath
import re
from html.entities import name2codepoint
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

from checks.base_checker import BaseChecker
from core.epub_context import EPUBContext


def _recover_html_named_entities(data: bytes):
    """Replace known HTML named entities with XML numeric references.

    Only used as a diagnostic fallback after XML parsing fails on an
    undefined entity. Unknown names and malformed XML remain errors.
    Original EPUB bytes are never modified.
    """
    replaced = set()

    def substitute(match):
        name = match.group(1).decode("ascii")
        codepoint = name2codepoint.get(name)
        if codepoint is None:
            return match.group(0)
        replaced.add(name)
        return f"&#{codepoint};".encode("ascii")

    repaired = re.sub(rb"&([A-Za-z][A-Za-z0-9]+);", substitute, data)
    return repaired, replaced


class ReadableContentChecker(BaseChecker):
    name = "ReadableContent"

    def check_path(self, path: str | Path):
        ctx = EPUBContext(Path(path))
        try:
            ctx.load()
            return self.check(ctx)
        except Exception as exc:
            return [self.critical(
                f"Cannot load EPUB reading structure: {type(exc).__name__}: {exc}",
                str(path),
            )]
        finally:
            ctx.close()

    def check(self, ctx, fast: bool = False):
        """Fast mode checks all spine references, but parses only 5 spread-out chapters.

        A successful fast scan is a sample-based assessment, not proof that
        every chapter can be opened. Full mode preserves existing behavior.
        """
        results = []
        spine = getattr(ctx, "spine", None) or []
        manifest = getattr(ctx, "manifest", None) or {}
        if not spine:
            return [self.critical("No reading order (spine) was found", "spine")]

        sample_indices = set()
        if fast:
            # First, last, and evenly distributed chapters; no duplicate reads.
            n = len(spine)
            sample_indices = {round(i * (n - 1) / (min(5, n) - 1))
                              for i in range(min(5, n))} if n > 1 else {0}
        checked = 0
        readable = 0
        for index, idref in enumerate(spine, 1):
            if not idref or idref not in manifest:
                results.append(self.critical(
                    f"Spine entry #{index} references missing manifest ID: {idref!r}",
                    str(getattr(ctx, "opf_path", "") or ""),
                    f"spine[{index}]",
                ))
                continue

            item = manifest[idref]
            path = item.get("path", "")
            media = item.get("media-type", "")
            if not path:
                results.append(self.critical(
                    f"Spine entry #{index} has no content path",
                    str(getattr(ctx, "opf_path", "") or ""),
                    idref,
                ))
                continue
            if not ctx.exists(path):
                results.append(self.critical(
                    "Reading-order document is missing from EPUB",
                    path,
                    f"spine[{index}]",
                ))
                continue

            if media not in ("application/xhtml+xml", "text/html"):
                # EPUB fixed-layout and fallback chains can have other media
                # types; don't label them corrupt without resolving fallbacks.
                results.append(self.warning(
                    f"Spine media type {media!r} is not checked as XHTML",
                    path,
                    f"spine[{index}]",
                ))
                continue

            if fast and (index - 1) not in sample_indices:
                # Existence is checked above for EVERY spine entry.
                continue

            checked += 1
            try:
                data = ctx.read_bytes(path)
            except Exception as exc:
                results.append(self.critical(
                    f"Cannot read spine document: {type(exc).__name__}: {exc}",
                    path,
                    f"spine[{index}]",
                ))
                continue

            if not data.strip():
                results.append(self.error(
                    "Reading-order document is empty",
                    path,
                    f"spine[{index}]",
                ))
                continue

            if media == "text/html":
                # XML parsing is not appropriate for HTML5, so only verify
                # that content exists and can be decoded.
                try:
                    data.decode("utf-8-sig")
                except UnicodeDecodeError:
                    results.append(self.warning(
                        "HTML document is not UTF-8; reader compatibility uncertain",
                        path,
                        f"spine[{index}]",
                    ))
                readable += 1
                continue

            try:
                root = ET.fromstring(data)
            except ET.ParseError as exc:
                if "undefined entity" not in str(exc).lower():
                    results.append(self.error(
                        f"Spine XHTML cannot be parsed as XML: {exc}",
                        path,
                        f"spine[{index}]",
                    ))
                    continue

                # Some EPUB readers tolerate HTML named entities such as
                # &nbsp; even though undeclared entities are invalid XML.
                # Reparse a temporary in-memory copy; never change the book.
                recovered, names = _recover_html_named_entities(data)
                if not names:
                    results.append(self.error(
                        f"Spine XHTML cannot be parsed as XML: {exc}",
                        path,
                        f"spine[{index}]",
                    ))
                    continue
                try:
                    root = ET.fromstring(recovered)
                except ET.ParseError as recovery_exc:
                    results.append(self.error(
                        f"Spine XHTML cannot be parsed as XML: {recovery_exc}",
                        path,
                        f"spine[{index}]",
                    ))
                    continue
                results.append(self.warning(
                    "XHTML uses undeclared HTML named entities "
                    f"({', '.join(sorted(names))}); recoverable for basic "
                    "content checks, but strict EPUB readers may reject it",
                    path,
                    f"spine[{index}]",
                ))

            if root.tag.rsplit("}", 1)[-1].lower() != "html":
                results.append(self.error(
                    "Spine XHTML root element is not html",
                    path,
                    f"spine[{index}]",
                ))
                continue

            body = next(
                (el for el in root.iter()
                 if el.tag.rsplit("}", 1)[-1].lower() == "body"),
                None,
            )
            if body is None:
                results.append(self.error(
                    "Spine XHTML has no body element",
                    path,
                    f"spine[{index}]",
                ))
                continue

            # Image-only chapters are valid (covers, comics, fixed layout).
            has_text = any((t or "").strip() for t in body.itertext())
            has_media = any(
                el.tag.rsplit("}", 1)[-1].lower() in {
                    "img", "image", "svg", "video", "audio", "object",
                    "canvas", "math",
                }
                for el in body.iter()
            )
            if not has_text and not has_media:
                results.append(self.warning(
                    "Spine XHTML body appears blank",
                    path,
                    f"spine[{index}]",
                ))
            readable += 1

            # Check directly referenced local images in the reading content.
            for element in body.iter():
                tag = element.tag.rsplit("}", 1)[-1].lower()
                if tag not in {"img", "image"}:
                    continue
                src = element.get("src") or element.get(
                    "{http://www.w3.org/1999/xlink}href"
                ) or element.get("href")
                if not src:
                    continue
                parts = urlsplit(src)
                if parts.scheme or parts.netloc or not parts.path:
                    continue
                target = posixpath.normpath(posixpath.join(
                    posixpath.dirname(path), unquote(parts.path)
                ))
                if target.startswith("../") or target == "..":
                    results.append(self.error(
                        "Image reference escapes EPUB package",
                        path,
                        src,
                    ))
                elif not ctx.exists(target):
                    results.append(self.warning(
                        "Image referenced by reading content is missing",
                        path,
                        src,
                    ))

        if checked == 0:
            results.append(self.critical(
                "No XHTML/HTML spine documents could be checked",
                str(getattr(ctx, "opf_path", "") or ""),
            ))
        elif readable == 0:
            results.append(self.critical(
                "No spine document passed the basic content checks",
                str(getattr(ctx, "opf_path", "") or ""),
            ))

        if fast:
            results.append(self.warning(
                f"FAST SAMPLE ONLY: parsed {checked} of {len(spine)} spine entries; "
                "all spine paths checked for existence. Unexamined chapters "
                "may still be malformed or unreadable."
            ))
        if not results:
            results.append(self.ok())
        return results

