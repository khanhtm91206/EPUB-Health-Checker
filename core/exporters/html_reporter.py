
"""
core/exporters/html_reporter.py

Interactive HTML report exporter for EPUB Health Checker.

Supported:
- CheckResult
- Report
- BookResult
- BatchResult
- Lists of supported objects

No external dependencies.
"""

from __future__ import annotations

import html
import json
from collections import Counter
from enum import Enum
from pathlib import Path
from typing import Any

from models import CheckResult
from core.report import Report
from engine.batch_result import BookResult, BatchResult


class HTMLReporter:

    def __init__(self, title: str = "EPUB Health Report"):
        self.title = title

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def serialize(self, value: Any) -> dict:
        """Normalize scan results for HTML rendering."""

        if isinstance(value, BatchResult):
            books = [
                self._book_data(book)
                for book in value.results
            ]
            source = str(value.source)

        elif isinstance(value, BookResult):
            books = [self._book_data(value)]
            source = str(value.path)

        elif isinstance(value, Report):
            books = [self._report_data(value)]
            source = (
                str(value.epub_path)
                if value.epub_path is not None
                else ""
            )

        elif isinstance(value, CheckResult):
            books = [{
                "path": "",
                "name": "Individual result",
                "status": (
                    "PASS" if value.success else "FAIL"
                ),
                "results": [self._result_data(value)],
            }]
            source = ""

        elif isinstance(value, (list, tuple)):
            books = []
            for item in value:
                books.extend(self.serialize(item)["books"])
            source = ""

        else:
            raise TypeError(
                "Unsupported HTML export type: "
                f"{type(value).__name__}"
            )

        counts = Counter(
            book["status"] for book in books
        )

        severities = Counter(
            result["severity"]
            for book in books
            for result in book["results"]
        )

        return {
            "source": source,
            "summary": {
                "total": len(books),
                "passed": counts["PASS"],
                "failed": counts["FAIL"],
                "no_result": counts["NO_RESULT"],
                "warnings": severities["WARNING"],
                "errors": severities["ERROR"],
                "critical": severities["CRITICAL"],
            },
            "books": books,
        }

    def to_html(self, value: Any) -> str:
        """Generate a standalone HTML document."""

        data = self.serialize(value)
        summary = data["summary"]

        title = html.escape(self.title)
        source = html.escape(data["source"])

        # Escape embedded JSON so EPUB metadata or checker
        # messages cannot break out of the script element.
        payload = json.dumps(
            data["books"],
            ensure_ascii=False,
        ).replace("<", "\\u003c").replace(
            ">", "\\u003e"
        ).replace("&", "\\u0026")

        template = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root {
    color-scheme: light;
    --bg: #f3f6fb;
    --surface: #ffffff;
    --text: #172033;
    --muted: #65748b;
    --line: #dce3ed;
    --blue: #2563eb;
    --green: #15803d;
    --red: #dc2626;
    --orange: #b45309;
    --purple: #7c3aed;
}
* { box-sizing: border-box; }
body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: system-ui, -apple-system, "Segoe UI",
                 Arial, sans-serif;
}
.container {
    max-width: 1400px;
    margin: auto;
    padding: 28px 20px 60px;
}
h1 { margin: 0 0 8px; font-size: 28px; }
.subtitle {
    color: var(--muted);
    overflow-wrap: anywhere;
    margin-bottom: 26px;
}
.stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
}
.stat {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 18px;
}
.stat .number {
    font-size: 28px;
    font-weight: 750;
}
.stat .label {
    color: var(--muted);
    margin-top: 4px;
    font-size: 13px;
}
.controls {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    background: var(--surface);
    border: 1px solid var(--line);
    padding: 16px;
    border-radius: 12px;
    margin-bottom: 14px;
}
input, select {
    font: inherit;
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 10px 12px;
    background: white;
    color: var(--text);
}
input { flex: 2; min-width: 220px; }
select { flex: 1; min-width: 150px; }
#visibleCount {
    margin: 12px 2px;
    color: var(--muted);
}
.book {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 12px;
    margin: 12px 0;
    overflow: hidden;
}
.book-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 15px 18px;
    cursor: pointer;
    list-style: none;
}
.book-header::-webkit-details-marker { display: none; }
.book-header::before {
    content: "▸";
    color: var(--muted);
}
.book[open] .book-header::before { content: "▾"; }
.book-name {
    font-weight: 650;
    overflow-wrap: anywhere;
    flex: 1;
}
.book-path {
    font-size: 12px;
    color: var(--muted);
    overflow-wrap: anywhere;
    padding: 0 18px 14px;
}
.badge {
    border-radius: 20px;
    padding: 5px 10px;
    font-size: 11px;
    font-weight: 750;
    white-space: nowrap;
}
.PASS, .INFO {
    background: #dcfce7;
    color: var(--green);
}
.FAIL, .ERROR {
    background: #fee2e2;
    color: var(--red);
}
.WARNING {
    background: #fef3c7;
    color: var(--orange);
}
.CRITICAL {
    background: #ede9fe;
    color: var(--purple);
}
.NO_RESULT {
    background: #e2e8f0;
    color: #475569;
}
.result-list {
    border-top: 1px solid var(--line);
    padding: 12px 18px 18px;
}
.result {
    border-bottom: 1px solid var(--line);
    padding: 12px 0;
}
.result:last-child { border-bottom: 0; }
.result-top {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
}
.result-message {
    margin: 8px 0;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}
.result-meta {
    color: var(--muted);
    font-size: 12px;
    overflow-wrap: anywhere;
}
.empty {
    padding: 32px;
    text-align: center;
    color: var(--muted);
}
@media (max-width: 600px) {
    .container { padding: 16px 12px; }
    h1 { font-size: 23px; }
}
</style>
</head>
<body>
<main class="container">
<h1>__TITLE__</h1>
<div class="subtitle">Source: __SOURCE__</div>

<section class="stats">
    <div class="stat">
        <div class="number">__TOTAL__</div>
        <div class="label">Total EPUBs</div>
    </div>
    <div class="stat">
        <div class="number">__PASSED__</div>
        <div class="label">Passed</div>
    </div>
    <div class="stat">
        <div class="number">__FAILED__</div>
        <div class="label">Failed</div>
    </div>
    <div class="stat">
        <div class="number">__NO_RESULT__</div>
        <div class="label">No result</div>
    </div>
    <div class="stat">
        <div class="number">__WARNINGS__</div>
        <div class="label">Warnings</div>
    </div>
    <div class="stat">
        <div class="number">__ERRORS__</div>
        <div class="label">Errors</div>
    </div>
    <div class="stat">
        <div class="number">__CRITICAL__</div>
        <div class="label">Critical</div>
    </div>
</section>

<section class="controls">
    <input id="search" placeholder="Search EPUB, checker, error..."
           aria-label="Search results">
    <select id="statusFilter" aria-label="Book status">
        <option value="ALL">All book statuses</option>
        <option value="PASS">PASS</option>
        <option value="FAIL">FAIL</option>
        <option value="NO_RESULT">NO_RESULT</option>
    </select>
    <select id="severityFilter" aria-label="Severity">
        <option value="ALL">All severities</option>
        <option value="INFO">INFO</option>
        <option value="WARNING">WARNING</option>
        <option value="ERROR">ERROR</option>
        <option value="CRITICAL">CRITICAL</option>
    </select>
</section>

<div id="visibleCount"></div>
<section id="bookList"></section>

<script id="report-data" type="application/json">__DATA__</script>
<script>
"use strict";

const books = JSON.parse(
    document.getElementById("report-data").textContent
);

const searchInput = document.getElementById("search");
const statusFilter = document.getElementById("statusFilter");
const severityFilter = document.getElementById("severityFilter");
const list = document.getElementById("bookList");
const visibleCount = document.getElementById("visibleCount");

const PAGE_SIZE = 100;
let visibleLimit = PAGE_SIZE;

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
}

function matchingResults(book, query, severity) {
    const bookMatches = (
        book.name + " " + book.path
    ).toLowerCase().includes(query);

    return book.results.filter(result => {
        if (severity !== "ALL" &&
            result.severity !== severity) {
            return false;
        }

        const text = [
            result.checker,
            result.message,
            result.file,
            result.location,
            result.severity
        ].join(" ").toLowerCase();

        return bookMatches || text.includes(query);
    });
}

function createBook(book, results) {
    const details = el("details", "book");
    const header = el("summary", "book-header");
    header.appendChild(el("span", "book-name", book.name));
    header.appendChild(el("span", "badge " + book.status,
                          book.status));
    header.appendChild(el("span", "", results.length + " results"));
    details.appendChild(header);
    details.appendChild(el("div", "book-path", book.path));

    const body = el("div", "result-list");

    if (results.length === 0) {
        body.appendChild(el("div", "empty",
                            "No checker results"));
    }

    for (const result of results) {
        const item = el("div", "result");
        const top = el("div", "result-top");
        top.appendChild(el("strong", "", result.checker));
        top.appendChild(
            el("span", "badge " + result.severity,
               result.severity)
        );
        item.appendChild(top);

        if (result.message) {
            item.appendChild(
                el("div", "result-message", result.message)
            );
        }

        const meta = [result.file, result.location]
            .filter(Boolean).join(" | ");

        if (meta) {
            item.appendChild(el("div", "result-meta", meta));
        }

        body.appendChild(item);
    }

    details.appendChild(body);
    return details;
}

function getMatches() {
    const query = searchInput.value.trim().toLowerCase();
    const status = statusFilter.value;
    const severity = severityFilter.value;

    const matches = [];

    for (const book of books) {
        if (status !== "ALL" && book.status !== status) {
            continue;
        }

        const results = matchingResults(book, query, severity);
        const bookMatches = (
            book.name + " " + book.path
        ).toLowerCase().includes(query);

        if (severity !== "ALL" && results.length === 0) {
            continue;
        }

        if (query && !bookMatches && results.length === 0) {
            continue;
        }

        matches.push({book, results});
    }

    return matches;
}

function render() {
    const matches = getMatches();
    const fragment = document.createDocumentFragment();

    for (const item of matches.slice(0, visibleLimit)) {
        fragment.appendChild(
            createBook(item.book, item.results)
        );
    }

    list.replaceChildren(fragment);

    visibleCount.textContent =
        "Showing " + Math.min(visibleLimit, matches.length) +
        " of " + matches.length + " matching EPUBs";

    if (matches.length === 0) {
        list.appendChild(
            el("div", "empty", "No matching results")
        );
    }

    if (matches.length > visibleLimit) {
        const button = el("button", "", "Load more EPUBs");
        button.style.padding = "12px 20px";
        button.style.cursor = "pointer";
        button.addEventListener("click", () => {
            visibleLimit += PAGE_SIZE;
            render();
        });
        list.appendChild(button);
    }
}

function resetAndRender() {
    visibleLimit = PAGE_SIZE;
    render();
}

searchInput.addEventListener("input", resetAndRender);
statusFilter.addEventListener("change", resetAndRender);
severityFilter.addEventListener("change", resetAndRender);

render();
</script>
</main>
</body>
</html>"""

        replacements = {
            "__TITLE__": title,
            "__SOURCE__": source,
            "__TOTAL__": summary["total"],
            "__PASSED__": summary["passed"],
            "__FAILED__": summary["failed"],
            "__NO_RESULT__": summary["no_result"],
            "__WARNINGS__": summary["warnings"],
            "__ERRORS__": summary["errors"],
            "__CRITICAL__": summary["critical"],
            "__DATA__": payload,
        }

        for key, replacement in replacements.items():
            template = template.replace(key, str(replacement))

        return template

    def save(
        self,
        value: Any,
        output: str | Path,
    ) -> Path:
        """Save a standalone HTML report."""

        output_path = Path(output)
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            self.to_html(value),
            encoding="utf-8",
        )

        return output_path

    def export(self, value: Any, output: str | Path) -> Path:
        return self.save(value, output)

    def save_report(self, report: Report, output: str | Path) -> Path:
        return self.save(report, output)

    def save_book_result(
        self,
        book: BookResult,
        output: str | Path,
    ) -> Path:
        return self.save(book, output)

    def save_batch_result(
        self,
        batch: BatchResult,
        output: str | Path,
    ) -> Path:
        return self.save(batch, output)

    # --------------------------------------------------
    # Internal conversion
    # --------------------------------------------------

    @staticmethod
    def _result_data(result: CheckResult) -> dict:
        severity = result.severity

        if isinstance(severity, Enum):
            severity = severity.value

        return {
            "checker": str(result.checker),
            "success": bool(result.success),
            "severity": str(severity),
            "message": str(result.message or ""),
            "file": str(result.file or ""),
            "location": str(result.location or ""),
        }

    def _book_data(self, book: BookResult) -> dict:
        return {
            "path": str(book.path),
            "name": book.path.name,
            "status": book.status,
            "results": [
                self._result_data(result)
                for result in book.results
            ],
        }

    def _report_data(self, report: Report) -> dict:
        path = (
            str(report.epub_path)
            if report.epub_path is not None
            else ""
        )

        return {
            "path": path,
            "name": Path(path).name if path else "Report",
            "status": report.status,
            "results": [
                self._result_data(result)
                for result in report.results
            ],
        }


def to_html(value: Any, title: str = "EPUB Health Report") -> str:
    return HTMLReporter(title=title).to_html(value)


def save_html(
    value: Any,
    output: str | Path,
    title: str = "EPUB Health Report",
) -> Path:
    return HTMLReporter(title=title).save(value, output)
