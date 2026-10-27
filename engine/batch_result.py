"""
engine/batch_result.py

Result containers for EPUB Health Checker.

Responsibilities
----------------
- Store the result of checking one EPUB.
- Store the results of a complete batch scan.
- Provide summary statistics.
- Provide convenient access to passed/failed results.
- Keep result aggregation separate from Runner, GUI, CLI and Reporters.

This module does NOT:
- Run checkers.
- Scan files.
- Generate reports.
- Print to the console.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator

from models import CheckResult, Severity


@dataclass(slots=True)
class BookResult:
    """
    Stores all checker results for one EPUB file.

    Parameters
    ----------
    path:
        Absolute path of the EPUB file.

    results:
        Results returned by the individual checkers.

    started_at:
        Time at which checking this EPUB started.

    finished_at:
        Time at which checking this EPUB finished.

    Attributes
    ----------
    path : Path
        EPUB file that was checked.

    results : list[CheckResult]
        Individual checker results.

    started_at : datetime | None
        Start timestamp.

    finished_at : datetime | None
        End timestamp.
    """

    path: Path
    results: list[CheckResult] = field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    # ------------------------------------------------------------------
    # Basic information
    # ------------------------------------------------------------------

    @property
    def filename(self) -> str:
        """Return the EPUB filename."""
        return self.path.name

    @property
    def stem(self) -> str:
        """Return the EPUB filename without its extension."""
        return self.path.stem

    @property
    def checker_count(self) -> int:
        """Return the number of checker results."""
        return len(self.results)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @staticmethod
    def _blocking_failure(result: CheckResult) -> bool:
        """A finding blocks overall PASS only if it is a real failure.

        WARNING findings are non-blocking even when success=False.
        INFO findings with success=False remain blocking so that older
        checkers which omit an appropriate severity are not silently ignored.
        """
        severity = BookResult._severity_name(result)
        if severity in ("ERROR", "CRITICAL"):
            return True
        if severity == "WARNING":
            return False
        return not BookResult._result_passed(result)

    @property
    def passed(self) -> bool:
        """True when checks ran and no blocking failure was recorded."""
        return bool(self.results) and not any(
            self._blocking_failure(result) for result in self.results
        )

    @property
    def failed(self) -> bool:
        """True when at least one blocking failure was recorded."""
        return any(self._blocking_failure(result) for result in self.results)

    @property
    def status(self) -> str:
        """PASS, FAIL or NO_RESULT; non-blocking warnings allow PASS."""
        if not self.results:
            return "NO_RESULT"
        return "FAIL" if self.failed else "PASS"

    # ------------------------------------------------------------------
    # Health assessment (independent of legacy PASS/FAIL)
    # ------------------------------------------------------------------

    @staticmethod
    def _severity_name(result: CheckResult) -> str:
        severity = getattr(result, "severity", Severity.INFO)
        value = getattr(severity, "value", severity)
        return str(value).upper()

    @property
    def health_status(self) -> str:
        """Conservative assessment based on recorded checker results.

        This is NOT proof that a reading app can open/render the book.
        CORRUPTED is reserved for explicit ZIP/container unreadability,
        rather than a failed metadata, accessibility or format check.
        """
        if not self.results:
            return "NOT_CHECKED"

        failures = [r for r in self.results if not self._result_passed(r)]
        if not failures:
            if any(self._severity_name(r) == "WARNING" for r in self.results):
                return "WARNING"
            return "HEALTHY"

        for r in failures:
            checker = self._result_name(r).casefold()
            message = str(getattr(r, "message", "")).casefold()
            if checker in ("integrity", "structure", "zip") and any(
                phrase in message for phrase in (
                    "not a zip file", "bad zip file", "badzipfile",
                    "invalid zip", "corrupt zip", "corrupted zip",
                    "cannot open zip", "failed to open zip",
                    "failed to load epub", "cannot load epub",
                )
            ):
                return "CORRUPTED"

        if any(self._severity_name(r) in ("ERROR", "CRITICAL") for r in failures):
            return "ERROR"
        return "WARNING"

    # ------------------------------------------------------------------
    # Reading readiness (independent from standards/quality health)
    # ------------------------------------------------------------------

    # Readability is an evidence-based estimate, not a real reader test.
    # Keep the existing three states for GUI/export compatibility.
    _CONTENT_FATAL = (
        "no reading order (spine)",
        "no spine document passed",
        "no xhtml/html spine documents could be checked",
        "cannot load epub reading structure",
    )
    _CONTENT_CHAPTER_PROBLEM = (
        "spine entry #",
        "reading-order document is missing",
        "cannot read spine document",
        "reading-order document is empty",
        "spine xhtml cannot be parsed",
        "spine xhtml root element is not html",
        "spine xhtml has no body element",
    )

    @property
    def readability_status(self) -> str:
        """Estimate readability using Integrity AND ReadableContent.

        UNREADABLE: a critical archive/package failure, context-load failure,
        or evidence that no usable reading-order document exists.
        READABLE: both checks ran, and no core content failure was reported.
        UNKNOWN: insufficient evidence or problems in some chapters only.
        """
        integrity = [
            r for r in self.results
            if self._result_name(r).casefold() == "integrity"
        ]
        content = [
            r for r in self.results
            if self._result_name(r).casefold() == "readablecontent"
        ]

        if any(
            not self._result_passed(r)
            and self._severity_name(r) == "CRITICAL"
            for r in integrity
        ):
            return "UNREADABLE"

        for r in self.results:
            if self._result_name(r).casefold() != "runner":
                continue
            message = str(getattr(r, "message", "")).casefold()
            if not self._result_passed(r) and any(
                term in message for term in (
                    "failed to load epub", "cannot load epub",
                    "failed to open epub",
                )
            ):
                return "UNREADABLE"

        if not integrity or not content:
            return "UNKNOWN"

        if any(
            not self._result_passed(r)
            and any(term in str(getattr(r, "message", "")).casefold()
                    for term in self._CONTENT_FATAL)
            for r in content
        ):
            return "UNREADABLE"

        # A single missing/broken chapter should not make the *entire*
        # book UNREADABLE. UNKNOWN flags partial reading risk.
        if any(
            not self._result_passed(r)
            and (
                self._severity_name(r) in ("ERROR", "CRITICAL")
                or any(term in str(getattr(r, "message", "")).casefold()
                       for term in self._CONTENT_CHAPTER_PROBLEM)
            )
            for r in content
        ):
            return "UNKNOWN"

        # Warnings for blank bodies, missing images or unsupported
        # spine media types remain in Health, not a hard unreadable claim.
        return "READABLE"

    @property
    def readability_reason(self) -> str:
        """Explain the classification without overstating certainty."""
        state = self.readability_status
        if state == "READABLE":
            return (
                "Integrity and basic spine-content checks passed; "
                "real EPUB reader compatibility has not been tested."
            )

        integrity = [
            r for r in self.results
            if self._result_name(r).casefold() == "integrity"
        ]
        content = [
            r for r in self.results
            if self._result_name(r).casefold() == "readablecontent"
        ]
        for r in integrity:
            if not self._result_passed(r) and self._severity_name(r) == "CRITICAL":
                return str(getattr(r, "message", "")) or "Critical EPUB integrity failure"

        for r in self.results:
            if self._result_name(r).casefold() == "runner":
                message = str(getattr(r, "message", ""))
                if not self._result_passed(r) and any(
                    term in message.casefold()
                    for term in ("failed to load epub", "cannot load epub", "failed to open epub")
                ):
                    return message

        if not integrity:
            return "Integrity preflight has not been recorded."
        if not content:
            return "ReadableContent checker has not been recorded."

        for r in content:
            message = str(getattr(r, "message", ""))
            if not self._result_passed(r) and any(
                term in message.casefold() for term in self._CONTENT_FATAL
            ):
                return message

        if state == "UNKNOWN":
            issues = [
                str(getattr(r, "message", ""))
                for r in content
                if not self._result_passed(r)
                and self._severity_name(r) in ("ERROR", "CRITICAL")
            ]
            if issues:
                return (
                    f"One or more spine documents have content errors "
                    f"({len(issues)} finding(s)); some chapters may still be readable. "
                    f"First: {issues[0]}"
                )
            return "Insufficient evidence to establish basic readability."

        return "Basic reading structure cannot be verified."

    @property
    def health_counts(self) -> dict[str, int]:
        """Counts of failed findings by severity; INFO is not an error."""
        counts = {"CRITICAL": 0, "ERROR": 0, "WARNING": 0, "INFO": 0}
        for result in self.results:
            if not self._result_passed(result):
                severity = self._severity_name(result)
                counts[severity if severity in counts else "INFO"] += 1
        return counts

    # ------------------------------------------------------------------
    # Result statistics
    # ------------------------------------------------------------------

    @property
    def passed_count(self) -> int:
        """Return the number of passed checker results."""
        return sum(
            1
            for result in self.results
            if self._result_passed(result)
        )

    @property
    def failed_count(self) -> int:
        """Return the number of failed checker results."""
        return sum(
            1
            for result in self.results
            if not self._result_passed(result)
        )

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------

    @property
    def duration_seconds(self) -> float | None:
        """
        Return checking duration in seconds.

        Returns None when either timestamp is unavailable.
        """

        if self.started_at is None:
            return None

        if self.finished_at is None:
            return None

        return (
            self.finished_at - self.started_at
        ).total_seconds()

    # ------------------------------------------------------------------
    # Result manipulation
    # ------------------------------------------------------------------

    def add_result(
        self,
        result: CheckResult,
    ) -> None:
        """
        Add one checker result.

        Parameters
        ----------
        result:
            Result produced by a checker.
        """

        self.results.append(result)

    def extend(
        self,
        results: Iterable[CheckResult],
    ) -> None:
        """
        Add multiple checker results.
        """

        self.results.extend(results)

    def get_result(
        self,
        checker_name: str,
    ) -> CheckResult | None:
        """
        Find a checker result by checker name.

        Returns None if the checker was not executed.
        """

        normalized_name = checker_name.casefold()

        for result in self.results:
            if self._result_name(result).casefold() == normalized_name:
                return result

        return None

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def as_dict(self) -> dict:
        """
        Convert this BookResult to a JSON-friendly dictionary.
        """

        return {
            "path": str(self.path),
            "filename": self.filename,
            "status": self.status,
            "health_status": self.health_status,
            "readability_status": self.readability_status,
            "readability_reason": self.readability_reason,
            "health_counts": self.health_counts,
            "checker_count": self.checker_count,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "started_at": (
                self.started_at.isoformat()
                if self.started_at
                else None
            ),
            "finished_at": (
                self.finished_at.isoformat()
                if self.finished_at
                else None
            ),
            "duration_seconds": self.duration_seconds,
            "results": [
                self._result_to_dict(result)
                for result in self.results
            ],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _result_name(
        result: CheckResult,
    ) -> str:
        """
        Safely retrieve a checker name.

        The current CheckResult model may expose its checker name
        under different attribute names depending on the existing
        project implementation.
        """

        if hasattr(result, "checker_name"):
            return str(result.checker_name)

        if hasattr(result, "name"):
            return str(result.name)

        if hasattr(result, "checker"):
            return str(result.checker)

        return result.__class__.__name__

    @staticmethod
    def _result_passed(
        result: CheckResult,
    ) -> bool:
        """
        Determine whether a CheckResult represents a successful check.

        This helper deliberately supports the existing CheckResult
        model instead of forcing changes to models.py.
        """

        if hasattr(result, "passed"):
            return bool(result.passed)

        if hasattr(result, "success"):
            return bool(result.success)

        if hasattr(result, "is_passed"):
            value = result.is_passed

            if callable(value):
                return bool(value())

            return bool(value)

        if hasattr(result, "status"):
            status = str(result.status).upper()

            if status in {
                "PASS",
                "PASSED",
                "SUCCESS",
                "OK",
            }:
                return True

            if status in {
                "FAIL",
                "FAILED",
                "ERROR",
            }:
                return False

        return False

    @staticmethod
    def _result_to_dict(
        result: CheckResult,
    ) -> dict:
        """
        Convert an individual CheckResult into a dictionary.

        If the model already provides as_dict(), use it.
        Otherwise collect its public attributes.
        """

        if hasattr(result, "as_dict"):
            return result.as_dict()

        if hasattr(result, "to_dict"):
            return result.to_dict()

        if hasattr(result, "__dict__"):
            return {
                key: value
                for key, value in result.__dict__.items()
                if not key.startswith("_")
            }

        return {
            "value": str(result),
        }

    def __iter__(self) -> Iterator[CheckResult]:
        """Iterate through checker results."""
        return iter(self.results)

    def __len__(self) -> int:
        """Return number of checker results."""
        return len(self.results)

    def __str__(self) -> str:
        return f"{self.filename}: {self.status}"


@dataclass(slots=True)
class BatchResult:
    """
    Stores results from a complete EPUB scanning operation.

    A BatchResult represents one complete user operation.

    Example
    -------
    The user selects a directory containing 3,000 EPUB files.

    One BatchResult contains:

        3,000 BookResult objects

    It can then be consumed by:

        Runner
            ↓
        Reporter
            ↓
        GUI / CLI / JSON / HTML
    """

    source: Path
    results: list[BookResult] = field(default_factory=list)

    started_at: datetime | None = None
    finished_at: datetime | None = None

    # ------------------------------------------------------------------
    # Basic information
    # ------------------------------------------------------------------

    @property
    def total(self) -> int:
        """Return the total number of EPUB files processed."""
        return len(self.results)

    @property
    def completed(self) -> int:
        """
        Return the number of EPUB files that have at least one result.
        """

        return sum(
            1
            for result in self.results
            if result.results
        )

    @property
    def remaining(self) -> int:
        """Return the number of EPUB files not yet completed."""
        return max(self.total - self.completed, 0)

    # ------------------------------------------------------------------
    # Overall status
    # ------------------------------------------------------------------

    @property
    def passed(self) -> int:
        """Return the number of EPUB files that passed."""
        return sum(
            1
            for result in self.results
            if result.passed
        )

    @property
    def failed(self) -> int:
        """Return the number of EPUB files that failed."""
        return sum(
            1
            for result in self.results
            if result.failed
        )

    @property
    def no_result(self) -> int:
        """Return the number of EPUB files without checker results."""
        return sum(
            1
            for result in self.results
            if not result.results
        )

    # ------------------------------------------------------------------
    # Checker statistics
    # ------------------------------------------------------------------

    @property
    def total_checker_results(self) -> int:
        """
        Return the total number of checker executions.
        """

        return sum(
            result.checker_count
            for result in self.results
        )

    @property
    def total_checker_passed(self) -> int:
        """Return total number of passed checker executions."""
        return sum(
            result.passed_count
            for result in self.results
        )

    @property
    def total_checker_failed(self) -> int:
        """Return total number of failed checker executions."""
        return sum(
            result.failed_count
            for result in self.results
        )

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    @property
    def progress(self) -> float:
        """
        Return completion percentage as a value from 0.0 to 1.0.

        Examples
        --------
        0.0
            Nothing completed.

        0.5
            50% completed.

        1.0
            Everything completed.
        """

        if self.total == 0:
            return 0.0

        return self.completed / self.total

    @property
    def progress_percent(self) -> float:
        """
        Return completion percentage from 0 to 100.
        """

        return self.progress * 100.0

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------

    @property
    def duration_seconds(self) -> float | None:
        """
        Return total batch duration in seconds.
        """

        if self.started_at is None:
            return None

        if self.finished_at is None:
            return None

        return (
            self.finished_at - self.started_at
        ).total_seconds()

    # ------------------------------------------------------------------
    # Result access
    # ------------------------------------------------------------------

    def add_result(
        self,
        result: BookResult,
    ) -> None:
        """
        Add one EPUB result to the batch.
        """

        self.results.append(result)

    def extend(
        self,
        results: Iterable[BookResult],
    ) -> None:
        """
        Add multiple EPUB results.
        """

        self.results.extend(results)

    def get_result(
        self,
        path: str | Path,
    ) -> BookResult | None:
        """
        Find a result by EPUB path.
        """

        target = Path(path).resolve()

        for result in self.results:
            if result.path.resolve() == target:
                return result

        return None

    def failed_results(self) -> list[BookResult]:
        """
        Return all EPUBs with at least one failed checker.
        """

        return [
            result
            for result in self.results
            if result.failed
        ]

    def passed_results(self) -> list[BookResult]:
        """
        Return all EPUBs where every executed checker passed.
        """

        return [
            result
            for result in self.results
            if result.passed
        ]

    def incomplete_results(self) -> list[BookResult]:
        """
        Return EPUBs that have no checker results.
        """

        return [
            result
            for result in self.results
            if not result.results
        ]

    @property
    def health_summary(self) -> dict[str, int]:
        """Aggregate health statuses across processed EPUBs."""
        summary = {name: 0 for name in (
            "HEALTHY", "WARNING", "ERROR", "CORRUPTED", "NOT_CHECKED"
        )}
        for book in self.results:
            summary[book.health_status] += 1
        return summary

    @property
    def readability_summary(self) -> dict[str, int]:
        """Aggregate basic EPUB reading-readiness classifications."""
        summary = {"READABLE": 0, "UNREADABLE": 0, "UNKNOWN": 0}
        for book in self.results:
            summary[book.readability_status] += 1
        return summary

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def as_dict(self) -> dict:
        """
        Convert the entire batch result to a JSON-friendly dictionary.
        """

        return {
            "source": str(self.source),
            "health_summary": self.health_summary,
            "readability_summary": self.readability_summary,
            "total": self.total,
            "completed": self.completed,
            "remaining": self.remaining,
            "passed": self.passed,
            "failed": self.failed,
            "no_result": self.no_result,
            "progress": self.progress,
            "progress_percent": self.progress_percent,
            "total_checker_results": self.total_checker_results,
            "total_checker_passed": self.total_checker_passed,
            "total_checker_failed": self.total_checker_failed,
            "started_at": (
                self.started_at.isoformat()
                if self.started_at
                else None
            ),
            "finished_at": (
                self.finished_at.isoformat()
                if self.finished_at
                else None
            ),
            "duration_seconds": self.duration_seconds,
            "results": [
                result.as_dict()
                for result in self.results
            ],
        }

    # ------------------------------------------------------------------
    # Collection behaviour
    # ------------------------------------------------------------------

    def __iter__(self) -> Iterator[BookResult]:
        """Iterate through EPUB results."""
        return iter(self.results)

    def __len__(self) -> int:
        """Return number of EPUB results."""
        return len(self.results)

    def __getitem__(self, index: int) -> BookResult:
        """Allow batch[index] access."""
        return self.results[index]

    def __str__(self) -> str:
        return (
            f"BatchResult("
            f"total={self.total}, "
            f"passed={self.passed}, "
            f"failed={self.failed}"
            f")"
        )


