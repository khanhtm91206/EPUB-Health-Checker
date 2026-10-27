"""
core/report.py

Report model for EPUB Health Checker.

The Report class is the compatibility layer between the original
checker architecture and the newer Engine architecture.

Legacy flow
-----------

    Checker
       |
       v
    Report
       |
       v
    ConsolePrinter


Engine flow
-----------

    Runner
       |
       v
    BookResult / BatchResult
       |
       v
    Report
       |
       +----> ConsolePrinter
       +----> JSON
       +----> HTML
       +----> GUI
       +----> CLI

The class intentionally keeps the original API:

    report = Report()
    report.add(checker.check(context))

    report.passed
    report.failed
    report.warnings
    report.all()
    report.to_dict()
    report.save_json()

so existing main.py does not need to be changed yet.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from models import CheckResult, Severity


class Report:
    """
    Collection of CheckResult objects for one EPUB.

    The Report class is deliberately lightweight.

    It does not:
    - execute checkers
    - open EPUB files
    - scan directories
    - display output
    - decide which checkers should run

    It only stores and summarizes checker results.
    """

    def __init__(
        self,
        epub_path: str | Path | None = None,
    ) -> None:
        """
        Create an empty Report.

        Parameters
        ----------
        epub_path:
            Optional EPUB path associated with this report.
        """

        self.epub_path = (
            Path(epub_path)
            if epub_path is not None
            else None
        )

        self.results: list[CheckResult] = []

    # ------------------------------------------------------------------
    # Adding results
    # ------------------------------------------------------------------

    def add(
        self,
        results: CheckResult | Iterable[CheckResult],
    ) -> None:
        """
        Add one or multiple CheckResult objects.

        The original project used:

            report.add(checker.check(ctx))

        where checker.check() returns a list.

        This method also accepts a single CheckResult, which makes
        the class easier to use from the new Engine.
        """

        if isinstance(results, CheckResult):
            self.results.append(results)
            return

        for result in results:

            if not isinstance(result, CheckResult):
                raise TypeError(
                    "Report can only contain CheckResult objects."
                )

            self.results.append(result)

    def extend(
        self,
        results: Iterable[CheckResult],
    ) -> None:
        """
        Add multiple CheckResult objects.

        This is an alias-style convenience method for Engine code.
        """

        self.add(results)

    # ------------------------------------------------------------------
    # Basic statistics
    # ------------------------------------------------------------------

    @property
    def total(self) -> int:
        """
        Return total number of checker results.
        """

        return len(self.results)

    @property
    def passed(self) -> int:
        """
        Return number of successful checker results.
        """

        return sum(
            1
            for result in self.results
            if result.success
        )

    @property
    def failed(self) -> int:
        """
        Return number of unsuccessful checker results.

        A WARNING is currently considered unsuccessful because the
        existing checker system represents warnings with
        success=False.
        """

        return sum(
            1
            for result in self.results
            if not result.success
        )

    @property
    def warnings(self) -> int:
        """
        Return number of WARNING results.
        """

        return sum(
            1
            for result in self.results
            if result.severity == Severity.WARNING
        )

    @property
    def errors(self) -> int:
        """
        Return number of ERROR results.
        """

        return sum(
            1
            for result in self.results
            if result.severity == Severity.ERROR
        )

    @property
    def critical(self) -> int:
        """
        Return number of CRITICAL results.
        """

        return sum(
            1
            for result in self.results
            if result.severity == Severity.CRITICAL
        )

    @property
    def info(self) -> int:
        """
        Return number of INFO results.
        """

        return sum(
            1
            for result in self.results
            if result.severity == Severity.INFO
        )

    # ------------------------------------------------------------------
    # Overall status
    # ------------------------------------------------------------------

    @property
    def success(self) -> bool:
        """
        Return True when all results passed.

        An empty report is not considered successful.
        """

        if not self.results:
            return False

        return all(
            result.success
            for result in self.results
        )

    @property
    def status(self) -> str:
        """
        Return the overall report status.

        Possible values:

            PASS
            FAIL
            NO_RESULT
        """

        if not self.results:
            return "NO_RESULT"

        if self.success:
            return "PASS"

        return "FAIL"

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def all(self) -> list[CheckResult]:
        """
        Return all checker results.

        The original project uses this method from ConsolePrinter.
        """

        return self.results

    def failed_results(self) -> list[CheckResult]:
        """
        Return all failed results.
        """

        return [
            result
            for result in self.results
            if not result.success
        ]

    def warning_results(self) -> list[CheckResult]:
        """
        Return all warning results.
        """

        return [
            result
            for result in self.results
            if result.severity == Severity.WARNING
        ]

    def error_results(self) -> list[CheckResult]:
        """
        Return all ERROR results.
        """

        return [
            result
            for result in self.results
            if result.severity == Severity.ERROR
        ]

    def critical_results(self) -> list[CheckResult]:
        """
        Return all CRITICAL results.
        """

        return [
            result
            for result in self.results
            if result.severity == Severity.CRITICAL
        ]

    def by_checker(
        self,
        checker_name: str,
    ) -> list[CheckResult]:
        """
        Return all results belonging to one checker.

        Matching is case-insensitive.
        """

        target = checker_name.casefold()

        return [
            result
            for result in self.results
            if result.checker.casefold() == target
        ]

    def has_checker(
        self,
        checker_name: str,
    ) -> bool:
        """
        Return True if a checker has produced at least one result.
        """

        return bool(
            self.by_checker(checker_name)
        )

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """
        Convert the report to a JSON-compatible dictionary.

        The existing JSON structure is preserved while adding useful
        status and severity statistics.
        """

        return {
            "epub": (
                str(self.epub_path)
                if self.epub_path is not None
                else None
            ),

            "status": self.status,

            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "warnings": self.warnings,
                "errors": self.errors,
                "critical": self.critical,
                "info": self.info,
            },

            "results": [
                self._result_to_dict(result)
                for result in self.results
            ],
        }

    @staticmethod
    def _result_to_dict(
        result: CheckResult,
    ) -> dict:
        """
        Convert one CheckResult into a JSON-compatible dictionary.
        """

        return {
            "checker": result.checker,
            "success": result.success,
            "severity": result.severity.value,
            "message": result.message,
            "file": result.file,
            "location": result.location,
        }

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------

    def save_json(
        self,
        output: str | Path,
    ) -> Path:
        """
        Save this report as JSON.

        Parameters
        ----------
        output:
            Destination JSON file.

        Returns
        -------
        Path
            The resolved output path.
        """

        output_path = Path(output)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with output_path.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                self.to_dict(),
                file,
                indent=4,
                ensure_ascii=False,
            )

        return output_path

    def to_json(
        self,
        indent: int = 4,
    ) -> str:
        """
        Return the report as a JSON string.
        """

        return json.dumps(
            self.to_dict(),
            indent=indent,
            ensure_ascii=False,
        )

    # ------------------------------------------------------------------
    # Engine compatibility
    # ------------------------------------------------------------------

    @classmethod
    def from_results(
        cls,
        results: Iterable[CheckResult],
        epub_path: str | Path | None = None,
    ) -> "Report":
        """
        Create a Report directly from checker results.
        """

        report = cls(
            epub_path=epub_path,
        )

        report.add(results)

        return report

    @classmethod
    def from_book_result(
        cls,
        book_result,
    ) -> "Report":
        """
        Create a Report from an Engine BookResult.

        The import is intentionally performed inside the method so
        Report remains usable independently of the Engine package.
        """

        report = cls(
            epub_path=book_result.path,
        )

        report.add(
            book_result.results
        )

        return report

    # ------------------------------------------------------------------
    # Collection behaviour
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        """
        Return number of stored checker results.
        """

        return len(self.results)

    def __iter__(self):
        """
        Iterate through checker results.
        """

        return iter(self.results)

    def __getitem__(
        self,
        index: int,
    ) -> CheckResult:
        """
        Support report[index].
        """

        return self.results[index]

    def __bool__(self) -> bool:
        """
        A Report evaluates to True when it contains at least one result.
        """

        return bool(self.results)

    def __str__(self) -> str:
        """
        Return a concise report summary.
        """

        return (
            f"Report("
            f"status={self.status}, "
            f"total={self.total}, "
            f"passed={self.passed}, "
            f"failed={self.failed}"
            f")"
        )