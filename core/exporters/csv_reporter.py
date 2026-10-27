from __future__ import annotations

import csv
import io
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from models import CheckResult
from core.report import Report
from engine.batch_result import BookResult, BatchResult


class CSVReporter:
    """Export EPUB checking results to CSV."""

    COLUMNS = (
        "epub_path",
        "epub_name",
        "book_status",
        "health_status",
        "readability_status",
        "readability_reason",
        "health_critical_count",
        "health_error_count",
        "health_warning_count",
        "checker",
        "success",
        "severity",
        "message",
        "file",
        "location",
    )

    def __init__(
        self,
        delimiter: str = ",",
        encoding: str = "utf-8-sig",
    ) -> None:
        self.delimiter = delimiter
        self.encoding = encoding

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def serialize(self, value: Any) -> list[dict]:
        """Convert supported objects into CSV rows."""

        if isinstance(value, BatchResult):
            rows = []

            for book in value.results:
                rows.extend(self._book_rows(book))

            return rows

        if isinstance(value, BookResult):
            return self._book_rows(value)

        if isinstance(value, Report):
            return self._report_rows(value)

        if isinstance(value, CheckResult):
            return [
                self._result_row(
                    value,
                    epub_path="",
                    book_status="",
                )
            ]

        if isinstance(value, (list, tuple)):
            rows = []

            for item in value:
                rows.extend(self.serialize(item))

            return rows

        raise TypeError(
            f"Unsupported CSV export type: "
            f"{type(value).__name__}"
        )

    def to_csv(self, value: Any) -> str:
        """Convert results into a CSV string."""

        rows = self.serialize(value)

        buffer = io.StringIO(newline="")

        writer = csv.DictWriter(
            buffer,
            fieldnames=self.COLUMNS,
            delimiter=self.delimiter,
            lineterminator="\n",
        )

        writer.writeheader()
        writer.writerows(rows)

        return buffer.getvalue()

    def save(
        self,
        value: Any,
        output: str | Path,
    ) -> Path:
        """Write results to a CSV file."""

        output_path = Path(output)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            self.to_csv(value),
            encoding=self.encoding,
            newline="",
        )

        return output_path

    def export(
        self,
        value: Any,
        output: str | Path,
    ) -> Path:
        """Alias for save()."""

        return self.save(value, output)

    def save_report(
        self,
        report: Report,
        output: str | Path,
    ) -> Path:
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
    # Conversion helpers
    # --------------------------------------------------

    def _book_rows(
        self,
        book: BookResult,
    ) -> list[dict]:

        epub_path = str(book.path)
        status = book.status
        extra = {
            "health_status": book.health_status,
            "readability_status": book.readability_status,
            "readability_reason": book.readability_reason,
            "health_critical_count": book.health_counts.get("CRITICAL", 0),
            "health_error_count": book.health_counts.get("ERROR", 0),
            "health_warning_count": book.health_counts.get("WARNING", 0),
        }

        if not book.results:
            return [
                self._empty_row(
                    epub_path,
                    status,
                    **extra,
                )
            ]

        return [
            self._result_row(
                result,
                epub_path=epub_path,
                book_status=status,
                **extra,
            )
            for result in book.results
        ]

    def _report_rows(
        self,
        report: Report,
    ) -> list[dict]:

        epub_path = (
            str(report.epub_path)
            if report.epub_path is not None
            else ""
        )

        if not report.results:
            return [
                self._empty_row(
                    epub_path,
                    report.status,
                )
            ]

        return [
            self._result_row(
                result,
                epub_path=epub_path,
                book_status=report.status,
            )
            for result in report.results
        ]

    def _result_row(
        self,
        result: CheckResult,
        epub_path: str,
        book_status: str,
        *,
        health_status: str = "",
        readability_status: str = "",
        readability_reason: str = "",
        health_critical_count: int | str = "",
        health_error_count: int | str = "",
        health_warning_count: int | str = "",
    ) -> dict:

        severity = result.severity

        if isinstance(severity, Enum):
            severity = severity.value

        return {
            "epub_path": epub_path,
            "epub_name": (
                Path(epub_path).name
                if epub_path
                else ""
            ),
            "book_status": book_status,
            "health_status": health_status,
            "readability_status": readability_status,
            "readability_reason": readability_reason,
            "health_critical_count": health_critical_count,
            "health_error_count": health_error_count,
            "health_warning_count": health_warning_count,
            "checker": result.checker,
            "success": result.success,
            "severity": severity,
            "message": result.message,
            "file": result.file,
            "location": result.location,
        }

    def _empty_row(
        self,
        epub_path: str,
        status: str,
        *,
        health_status: str = "",
        readability_status: str = "",
        readability_reason: str = "",
        health_critical_count: int | str = "",
        health_error_count: int | str = "",
        health_warning_count: int | str = "",
    ) -> dict:

        return {
            "epub_path": epub_path,
            "epub_name": (
                Path(epub_path).name
                if epub_path
                else ""
            ),
            "book_status": status,
            "health_status": health_status,
            "readability_status": readability_status,
            "readability_reason": readability_reason,
            "health_critical_count": health_critical_count,
            "health_error_count": health_error_count,
            "health_warning_count": health_warning_count,
            "checker": "",
            "success": "",
            "severity": "",
            "message": "No checker results",
            "file": "",
            "location": "",
        }


# --------------------------------------------------
# Convenience functions
# --------------------------------------------------

def to_csv(
    value: Any,
    delimiter: str = ",",
) -> str:

    return CSVReporter(
        delimiter=delimiter,
    ).to_csv(value)


def save_csv(
    value: Any,
    output: str | Path,
    delimiter: str = ",",
) -> Path:

    return CSVReporter(
        delimiter=delimiter,
    ).save(value, output)
