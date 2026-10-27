"""
core/printer.py

Console output for EPUB Health Checker.

Supports both:
    - legacy Report
    - Engine BookResult
    - Engine BatchResult

The printer is presentation-only:
    it does not run checkers
    it does not scan EPUB files
    it does not modify results
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from models import CheckResult, Severity


class ConsolePrinter:
    """
    Formats checker results for console output.

    The class intentionally keeps the existing simple API while
    adding support for the new Engine result objects.
    """

    # ---------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------

    def print_report(self, report: Any) -> None:
        """
        Print a complete report.

        `report` may be:

            Report
            BookResult
            BatchResult
        """

        if self._is_batch_result(report):
            self.print_batch(report)
            return

        if self._is_book_result(report):
            self.print_book(report)
            return

        self._print_legacy_report(report)

    def print_book(self, book_result: Any) -> None:
        """
        Print the result of one EPUB.
        """

        path = getattr(
            book_result,
            "path",
            None,
        )

        results = getattr(
            book_result,
            "results",
            [],
        )

        status = getattr(
            book_result,
            "status",
            None,
        )

        print()
        print("=" * 70)
        print(
            f"EPUB: {path}"
        )
        print("=" * 70)

        self._print_results(
            results
        )

        print()
        print(
            self._format_status_line(
                status=status,
                results=results,
            )
        )

        duration = getattr(
            book_result,
            "duration_seconds",
            None,
        )

        if duration is not None:
            print(
                f"Duration: {duration:.2f}s"
            )

        print("=" * 70)

    def print_batch(self, batch_result: Any) -> None:
        """
        Print a complete batch result.

        Designed for large EPUB collections, so the output is kept
        compact: individual EPUB details are printed only when useful,
        followed by a complete summary.
        """

        source = getattr(
            batch_result,
            "source",
            None,
        )

        results = list(
            getattr(
                batch_result,
                "results",
                [],
            )
        )

        print()
        print("=" * 70)
        print("EPUB HEALTH CHECKER")
        print("=" * 70)

        if source is not None:
            print(
                f"Source: {source}"
            )

        print(
            f"Total EPUBs: {len(results)}"
        )

        print()

        for index, result in enumerate(
            results,
            start=1,
        ):
            self._print_batch_item(
                index,
                result,
            )

        print()
        self._print_batch_summary(
            batch_result
        )

    def print_progress(
        self,
        snapshot: Any,
    ) -> None:
        """
        Print one progress snapshot.

        Intended for CLI callbacks.

        Example:

            125/3000 | 4.2% | 8.31 EPUB/s | ETA 5m 46s
        """

        total = getattr(
            snapshot,
            "total",
            0,
        )

        completed = getattr(
            snapshot,
            "completed",
            0,
        )

        percent = getattr(
            snapshot,
            "percent",
            0.0,
        )

        speed = getattr(
            snapshot,
            "items_per_second",
            0.0,
        )

        eta = getattr(
            snapshot,
            "estimated_remaining_seconds",
            None,
        )

        eta_text = self._format_duration(
            eta
        )

        print(
            f"\r"
            f"{completed}/{total} "
            f"| {percent:.1f}% "
            f"| {speed:.2f} EPUB/s "
            f"| ETA {eta_text}",
            end="",
            flush=True,
        )

        if completed >= total:
            print()

    # ---------------------------------------------------------------
    # Legacy Report support
    # ---------------------------------------------------------------

    def _print_legacy_report(
        self,
        report: Any,
    ) -> None:
        """
        Print the original Report object.

        This keeps the old main.py flow working.
        """

        results = []

        try:
            results = report.all()

        except AttributeError:
            results = getattr(
                report,
                "results",
                [],
            )

        epub_path = getattr(
            report,
            "epub_path",
            None,
        )

        print()
        print("=" * 70)

        if epub_path:
            print(
                f"EPUB: {epub_path}"
            )
        else:
            print("EPUB HEALTH CHECK")

        print("=" * 70)

        self._print_results(
            results
        )

        print()

        passed = sum(
            1
            for result in results
            if self._is_success(result)
        )

        failed = len(results) - passed

        print(
            f"Passed: {passed} | "
            f"Failed: {failed}"
        )

        print("=" * 70)

    # ---------------------------------------------------------------
    # Result printing
    # ---------------------------------------------------------------

    def _print_results(
        self,
        results: Iterable[CheckResult],
    ) -> None:
        """
        Print individual checker results.
        """

        results = list(results)

        if not results:
            print(
                "No checker results."
            )
            return

        for result in results:
            self._print_result(
                result
            )

    def _print_result(
        self,
        result: CheckResult,
    ) -> None:
        """
        Print one CheckResult.
        """

        checker = getattr(
            result,
            "checker",
            "Unknown",
        )

        success = self._is_success(
            result
        )

        severity = getattr(
            result,
            "severity",
            Severity.INFO,
        )

        message = getattr(
            result,
            "message",
            "",
        )

        file = getattr(
            result,
            "file",
            "",
        )

        location = getattr(
            result,
            "location",
            "",
        )

        status = (
            "PASS"
            if success
            else "FAIL"
        )

        severity_text = self._severity_text(
            severity
        )

        print(
            f"[{status}] "
            f"{checker}"
            f" [{severity_text}]"
        )

        if message:
            print(
                f"    {message}"
            )

        if file:
            print(
                f"    File: {file}"
            )

        if location:
            print(
                f"    Location: {location}"
            )

    # ---------------------------------------------------------------
    # Batch printing
    # ---------------------------------------------------------------

    def _print_batch_item(
        self,
        index: int,
        book_result: Any,
    ) -> None:
        """
        Print one compact batch entry.
        """

        path = getattr(
            book_result,
            "path",
            None,
        )

        status = getattr(
            book_result,
            "status",
            None,
        )

        results = getattr(
            book_result,
            "results",
            [],
        )

        failed_count = sum(
            1
            for result in results
            if not self._is_success(result)
        )

        status_text = (
            status
            if status is not None
            else self._calculate_status(results)
        )

        if failed_count > 0:
            print(
                f"[{index:>5}] "
                f"[FAIL] "
                f"{path} "
                f"({failed_count} issue(s))"
            )
        else:
            print(
                f"[{index:>5}] "
                f"[{status_text}] "
                f"{path}"
            )

    def _print_batch_summary(
        self,
        batch_result: Any,
    ) -> None:
        """
        Print batch summary statistics.
        """

        total = getattr(
            batch_result,
            "total",
            0,
        )

        passed = getattr(
            batch_result,
            "passed",
            0,
        )

        failed = getattr(
            batch_result,
            "failed",
            0,
        )

        no_result = getattr(
            batch_result,
            "no_result",
            0,
        )

        checker_total = getattr(
            batch_result,
            "total_checker_results",
            0,
        )

        checker_passed = getattr(
            batch_result,
            "total_checker_passed",
            0,
        )

        checker_failed = getattr(
            batch_result,
            "total_checker_failed",
            0,
        )

        duration = getattr(
            batch_result,
            "duration_seconds",
            None,
        )

        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)

        print(
            f"EPUBs checked : {total}"
        )

        print(
            f"EPUBs passed  : {passed}"
        )

        print(
            f"EPUBs failed  : {failed}"
        )

        if no_result:
            print(
                f"No result    : {no_result}"
            )

        print()

        print(
            f"Checker runs  : {checker_total}"
        )

        print(
            f"Checker pass  : {checker_passed}"
        )

        print(
            f"Checker fail  : {checker_failed}"
        )

        if duration is not None:
            print()

            print(
                f"Duration      : "
                f"{duration:.2f}s"
            )

        print("=" * 70)

    # ---------------------------------------------------------------
    # Status helpers
    # ---------------------------------------------------------------

    @staticmethod
    def _is_success(
        result: CheckResult,
    ) -> bool:
        """
        Determine whether a CheckResult passed.
        """

        return bool(
            getattr(
                result,
                "success",
                False,
            )
        )

    @staticmethod
    def _severity_text(
        severity: Severity,
    ) -> str:
        """
        Convert Severity into display text.
        """

        if isinstance(
            severity,
            Severity,
        ):
            return severity.value.upper()

        return str(
            severity
        ).upper()

    @staticmethod
    def _calculate_status(
        results: Iterable[CheckResult],
    ) -> str:
        """
        Calculate overall status from checker results.
        """

        results = list(results)

        if not results:
            return "NO_RESULT"

        if all(
            ConsolePrinter._is_success(
                result
            )
            for result in results
        ):
            return "PASS"

        return "FAIL"

    @staticmethod
    def _format_status_line(
        status: str | None,
        results: Iterable[CheckResult],
    ) -> str:
        """
        Format an overall status line.
        """

        if status is None:
            status = ConsolePrinter._calculate_status(
                results
            )

        results = list(results)

        passed = sum(
            1
            for result in results
            if ConsolePrinter._is_success(result)
        )

        failed = len(results) - passed

        return (
            f"Status: {status} | "
            f"Passed: {passed} | "
            f"Failed: {failed}"
        )

    # ---------------------------------------------------------------
    # Type detection
    # ---------------------------------------------------------------

    @staticmethod
    def _is_batch_result(
        value: Any,
    ) -> bool:
        """
        Detect Engine BatchResult without importing it.

        Avoiding a hard dependency here keeps Printer usable by the
        legacy system.
        """

        return (
            hasattr(value, "results")
            and hasattr(value, "source")
            and hasattr(value, "progress")
            and hasattr(value, "total")
        )

    @staticmethod
    def _is_book_result(
        value: Any,
    ) -> bool:
        """
        Detect Engine BookResult without importing it.
        """

        return (
            hasattr(value, "path")
            and hasattr(value, "results")
            and hasattr(value, "status")
            and not hasattr(value, "source")
        )

    # ---------------------------------------------------------------
    # Formatting utilities
    # ---------------------------------------------------------------

    @staticmethod
    def _format_duration(
        seconds: float | None,
    ) -> str:
        """
        Convert seconds into human-readable text.
        """

        if seconds is None:
            return "Calculating..."

        seconds = max(
            int(round(seconds)),
            0,
        )

        hours, remainder = divmod(
            seconds,
            3600,
        )

        minutes, seconds = divmod(
            remainder,
            60,
        )

        if hours:
            return (
                f"{hours}h "
                f"{minutes}m "
                f"{seconds}s"
            )

        if minutes:
            return (
                f"{minutes}m "
                f"{seconds}s"
            )

        return f"{seconds}s"


# ----------------------------------------------------------------------
# Convenience function
# ----------------------------------------------------------------------

def print_report(
    report: Any,
) -> None:
    """
    Convenience wrapper.

    Allows:

        print_report(report)

    instead of:

        ConsolePrinter().print_report(report)
    """

    printer = ConsolePrinter()

    printer.print_report(
        report
    )