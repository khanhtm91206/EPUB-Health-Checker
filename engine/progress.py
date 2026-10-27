"""
engine/progress.py

Progress tracking for EPUB Health Checker.

Responsibilities
----------------
- Track total scan jobs.
- Track completed jobs.
- Track successful and failed jobs.
- Calculate progress percentage.
- Estimate remaining work.
- Provide progress snapshots for CLI and GUI.

This module does NOT:
- Scan EPUB files.
- Run checkers.
- Generate reports.
- Print to the console.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from time import monotonic


@dataclass(slots=True, frozen=True)
class ProgressSnapshot:
    """
    Immutable snapshot of the current scanning progress.

    This object is useful for passing progress information from the
    Runner to the GUI or CLI without exposing the internal mutable
    state of ProgressTracker.
    """

    total: int
    completed: int
    passed: int
    failed: int

    started_at: datetime | None
    elapsed_seconds: float

    percent: float
    remaining: int

    items_per_second: float
    estimated_remaining_seconds: float | None

    @property
    def finished(self) -> bool:
        """Return True when all jobs have been completed."""
        return self.completed >= self.total

    @property
    def has_started(self) -> bool:
        """Return True when progress tracking has started."""
        return self.started_at is not None


class ProgressTracker:
    """
    Tracks progress for a batch of EPUB scan jobs.

    Example
    -------
    tracker = ProgressTracker(total=3000)

    tracker.start()

    tracker.complete(passed=True)

    snapshot = tracker.snapshot()

    The Runner can then pass `snapshot` to a GUI callback or CLI
    progress display.
    """

    def __init__(self, total: int = 0) -> None:
        """
        Create a progress tracker.

        Parameters
        ----------
        total:
            Total number of jobs expected.
        """

        if not isinstance(total, int):
            raise TypeError(
                "total must be an integer."
            )

        if total < 0:
            raise ValueError(
                "total cannot be negative."
            )

        self._total = total
        self._completed = 0
        self._passed = 0
        self._failed = 0

        self._started_at: datetime | None = None
        self._monotonic_start: float | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def total(self) -> int:
        """Return total number of jobs."""
        return self._total

    @property
    def completed(self) -> int:
        """Return number of completed jobs."""
        return self._completed

    @property
    def passed(self) -> int:
        """Return number of successful jobs."""
        return self._passed

    @property
    def failed(self) -> int:
        """Return number of failed jobs."""
        return self._failed

    @property
    def remaining(self) -> int:
        """Return number of jobs remaining."""
        return max(
            self._total - self._completed,
            0,
        )

    @property
    def percent(self) -> float:
        """
        Return progress percentage from 0 to 100.

        Returns 0 when there are no jobs.
        """

        if self._total == 0:
            return 0.0

        return (
            self._completed / self._total
        ) * 100.0

    @property
    def fraction(self) -> float:
        """
        Return progress as a value from 0.0 to 1.0.
        """

        return self.percent / 100.0

    @property
    def started(self) -> bool:
        """Return True when tracking has started."""
        return self._started_at is not None

    @property
    def finished(self) -> bool:
        """Return True when all jobs have completed."""
        return self._completed >= self._total

    @property
    def elapsed_seconds(self) -> float:
        """
        Return elapsed tracking time.

        Uses monotonic time so the calculation is not affected by
        changes to the system clock.
        """

        if self._monotonic_start is None:
            return 0.0

        return max(
            monotonic() - self._monotonic_start,
            0.0,
        )

    @property
    def items_per_second(self) -> float:
        """
        Return average processing speed.

        Returns 0 when no work has been completed yet.
        """

        elapsed = self.elapsed_seconds

        if elapsed <= 0:
            return 0.0

        if self._completed <= 0:
            return 0.0

        return self._completed / elapsed

    @property
    def estimated_remaining_seconds(self) -> float | None:
        """
        Estimate the remaining processing time.

        Returns None when there is not enough information to make
        an estimate.
        """

        speed = self.items_per_second

        if speed <= 0:
            return None

        return self.remaining / speed

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """
        Start progress tracking.

        Calling start() again resets the timer but does not reset
        completed counts.
        """

        self._started_at = datetime.now()
        self._monotonic_start = monotonic()

    def reset(
        self,
        total: int | None = None,
    ) -> None:
        """
        Reset all progress state.

        Parameters
        ----------
        total:
            Optional new total job count.

            If omitted, the existing total is kept.
        """

        if total is not None:
            if not isinstance(total, int):
                raise TypeError(
                    "total must be an integer."
                )

            if total < 0:
                raise ValueError(
                    "total cannot be negative."
                )

            self._total = total

        self._completed = 0
        self._passed = 0
        self._failed = 0

        self._started_at = None
        self._monotonic_start = None

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_total(
        self,
        total: int,
    ) -> None:
        """
        Change the total job count.

        This should normally be called before processing starts.

        Raises
        ------
        ValueError
            If total is smaller than the number already completed.
        """

        if not isinstance(total, int):
            raise TypeError(
                "total must be an integer."
            )

        if total < 0:
            raise ValueError(
                "total cannot be negative."
            )

        if total < self._completed:
            raise ValueError(
                "total cannot be smaller than "
                "the number of completed jobs."
            )

        self._total = total

    # ------------------------------------------------------------------
    # Updating progress
    # ------------------------------------------------------------------

    def complete(
        self,
        passed: bool | None = None,
    ) -> None:
        """
        Mark one job as completed.

        Parameters
        ----------
        passed:
            True
                Job passed.

            False
                Job failed.

            None
                Job completed but its final status is unknown.

        Raises
        ------
        RuntimeError
            If more jobs are completed than the configured total.
        """

        if self._completed >= self._total:
            raise RuntimeError(
                "Cannot complete more jobs than the configured total."
            )

        self._completed += 1

        if passed is True:
            self._passed += 1

        elif passed is False:
            self._failed += 1

    def mark_passed(self) -> None:
        """
        Mark one job as completed successfully.
        """

        self.complete(passed=True)

    def mark_failed(self) -> None:
        """
        Mark one job as completed with failure.
        """

        self.complete(passed=False)

    def mark_completed(self) -> None:
        """
        Mark one job as completed without specifying its status.
        """

        self.complete(passed=None)

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> ProgressSnapshot:
        """
        Create an immutable snapshot of the current progress.
        """

        return ProgressSnapshot(
            total=self._total,
            completed=self._completed,
            passed=self._passed,
            failed=self._failed,
            started_at=self._started_at,
            elapsed_seconds=self.elapsed_seconds,
            percent=self.percent,
            remaining=self.remaining,
            items_per_second=self.items_per_second,
            estimated_remaining_seconds=(
                self.estimated_remaining_seconds
            ),
        )

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def format_percent(
        self,
        decimals: int = 1,
    ) -> str:
        """
        Return progress percentage as formatted text.

        Example
        -------
        "42.5%"
        """

        if decimals < 0:
            raise ValueError(
                "decimals cannot be negative."
            )

        return f"{self.percent:.{decimals}f}%"

    def format_speed(
        self,
        decimals: int = 2,
    ) -> str:
        """
        Return processing speed as formatted text.

        Example
        -------
        "12.35 EPUB/s"
        """

        if decimals < 0:
            raise ValueError(
                "decimals cannot be negative."
            )

        return (
            f"{self.items_per_second:.{decimals}f} EPUB/s"
        )

    def format_eta(self) -> str:
        """
        Return estimated remaining time as human-readable text.

        Examples
        --------
        "Calculating..."

        "45s"

        "3m 12s"

        "1h 4m 8s"
        """

        seconds = self.estimated_remaining_seconds

        if seconds is None:
            return "Calculating..."

        return self._format_duration(seconds)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def as_dict(self) -> dict:
        """
        Convert current progress into a JSON-friendly dictionary.
        """

        snapshot = self.snapshot()

        return {
            "total": snapshot.total,
            "completed": snapshot.completed,
            "passed": snapshot.passed,
            "failed": snapshot.failed,
            "remaining": snapshot.remaining,
            "percent": snapshot.percent,
            "elapsed_seconds": snapshot.elapsed_seconds,
            "items_per_second": snapshot.items_per_second,
            "estimated_remaining_seconds": (
                snapshot.estimated_remaining_seconds
            ),
            "started_at": (
                snapshot.started_at.isoformat()
                if snapshot.started_at
                else None
            ),
            "finished": snapshot.finished,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_duration(
        seconds: float,
    ) -> str:
        """
        Convert seconds into human-readable duration text.
        """

        total_seconds = max(
            int(round(seconds)),
            0,
        )

        hours, remainder = divmod(
            total_seconds,
            3600,
        )

        minutes, seconds = divmod(
            remainder,
            60,
        )

        if hours > 0:
            return (
                f"{hours}h "
                f"{minutes}m "
                f"{seconds}s"
            )

        if minutes > 0:
            return (
                f"{minutes}m "
                f"{seconds}s"
            )

        return f"{seconds}s"

    def __str__(self) -> str:
        """
        Return a concise progress representation.
        """

        return (
            f"{self._completed}/{self._total} "
            f"({self.percent:.1f}%)"
        )