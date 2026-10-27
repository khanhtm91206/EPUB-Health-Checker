"""
engine/runner.py

EPUB checking execution engine.

Responsibilities
----------------
- Execute selected EPUB checkers.
- Process one EPUB or a batch of EPUBs.
- Create and manage EPUBContext instances.
- Collect checker results into BookResult and BatchResult.
- Track progress through ProgressTracker.
- Report progress through an optional callback.
- Continue processing other EPUBs when one EPUB fails.

This module does NOT:
- Discover EPUB files.
- Print reports.
- Generate HTML/JSON reports.
- Implement GUI.
- Implement CLI.

The Runner sits between Scanner / CheckerRegistry and the
reporting / presentation layers.

Architecture
------------

    Scanner
       |
       v
    ScanJob
       |
       v
    Runner <---- CheckerRegistry
       |
       +----> EPUBContext
       |
       +----> Checkers
       |
       v
    BookResult
       |
       v
    BatchResult
       |
       +----> Reporter
       +----> GUI
       +----> CLI
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from datetime import datetime
import zipfile
import posixpath
from xml.etree import ElementTree as ET
from pathlib import Path
from threading import Event, Lock
from typing import Any

from checks.base_checker import BaseChecker
from checks.integrity_check import IntegrityChecker
from checks.readable_content_check import ReadableContentChecker
from core.epub_context import EPUBContext
from models import CheckResult, ScanJob, Severity

from engine.batch_result import BatchResult, BookResult
from engine.checker_registry import CheckerRegistry
from engine.progress import ProgressSnapshot, ProgressTracker


# ----------------------------------------------------------------------
# Type aliases
# ----------------------------------------------------------------------

ProgressCallback = Callable[[ProgressSnapshot], None]


class ScanControl:
    """Thread-safe cooperative pause/resume/stop controller for a batch.

    Pause and stop take effect between EPUBs, not during a checker.
    The GUI can call these methods from the Tkinter main thread.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._resume_event = Event()
        self._resume_event.set()
        self._stop_event = Event()

    def pause(self) -> None:
        with self._lock:
            if not self._stop_event.is_set():
                self._resume_event.clear()

    def resume(self) -> None:
        self._resume_event.set()

    def stop(self) -> None:
        self._stop_event.set()
        self._resume_event.set()  # Wake a paused worker so it can exit.

    @property
    def is_paused(self) -> bool:
        return not self._resume_event.is_set() and not self._stop_event.is_set()

    @property
    def is_stopped(self) -> bool:
        return self._stop_event.is_set()

    def wait_until_ready(self) -> bool:
        """Block while paused; return False if stop was requested."""
        while not self._stop_event.is_set():
            if self._resume_event.wait(timeout=0.1):
                return not self._stop_event.is_set()
        return False


class Runner:
    """
    Executes EPUB checkers against ScanJob objects.

    The Runner can process:

    - one EPUB
    - a list of ScanJob objects
    - all registered checkers
    - only selected checkers

    Example
    -------

    registry = CheckerRegistry()

    registry.register(StructureChecker)
    registry.register(HTMLChecker)

    runner = Runner(registry)

    result = runner.run_file(
        scan_job,
        checker_names=["Structure", "HTML"],
    )

    Or for a complete batch:

    result = runner.run_batch(
        jobs,
        checker_names=["Structure", "HTML"],
    )
    """

    RUNNER_CHECKER_NAME = "Runner"

    def __init__(
        self,
        registry: CheckerRegistry,
    ) -> None:
        """
        Create a Runner.

        Parameters
        ----------
        registry:
            CheckerRegistry containing available checker classes.
        """

        if not isinstance(registry, CheckerRegistry):
            raise TypeError(
                "registry must be a CheckerRegistry instance."
            )

        self.registry = registry

    # ------------------------------------------------------------------
    # Public API - single EPUB
    # ------------------------------------------------------------------

    def run_file(
        self,
        job: ScanJob,
        checker_names: Sequence[str] | None = None,
        fast_readability: bool = False,
        zip_integrity: bool = False,
    ) -> BookResult:
        """
        Run selected checkers against one EPUB.

        Parameters
        ----------
        job:
            ScanJob describing the EPUB to process.

        checker_names:
            Names of checkers to execute.

            None
                Execute all registered checkers.

            Example
                ["Structure", "HTML", "CSS"]

        Returns
        -------
        BookResult
            Complete result for this EPUB.

        Notes
        -----
        A failure inside one checker does not normally stop the
        remaining checkers from running.

        A failure while opening/loading the EPUB context is different:
        the EPUB cannot safely be checked, so the Runner records a
        critical result and returns.
        """

        selected_checkers = [] if (fast_readability or zip_integrity) else self._create_checkers(checker_names)
        return self._run_file_with_checkers(job, selected_checkers, fast_readability=fast_readability, zip_integrity=zip_integrity)

    # ------------------------------------------------------------------
    # Public API - batch
    # ------------------------------------------------------------------

    def run_batch(
        self,
        jobs: Iterable[ScanJob],
        checker_names: Sequence[str] | None = None,
        progress_callback: ProgressCallback | None = None,
        control: ScanControl | None = None,
        fast_readability: bool = False,
        zip_integrity: bool = False,
    ) -> BatchResult:
        """
        Run selected checkers against multiple EPUB files.

        Parameters
        ----------
        jobs:
            Iterable of ScanJob objects.

        checker_names:
            Names of checkers to execute.

            None
                Execute all registered checkers.

        progress_callback:
            Optional callback receiving a ProgressSnapshot after
            every completed EPUB.

        control:
            Optional ScanControl for cooperative pause/resume/stop.
            A stopped batch returns only the completed EPUB results.
            The GUI should treat it as partial, not a full scan.

        Returns
        -------
        BatchResult
            Complete result for the batch.

        Important
        ---------
        The jobs iterable is materialized into a list before processing.
        This gives the Runner a stable total count, which is required
        for accurate progress reporting.
        """

        job_list = list(jobs)

        self._validate_jobs(job_list)

        # Validate checker selection before starting the batch.
        #
        # This prevents the situation where EPUB #1 is processed and
        # then an invalid checker name causes the batch to stop.
        selected_checkers = [] if (fast_readability or zip_integrity) else self._create_checkers(
            checker_names
        )

        batch_source = self._determine_batch_source(
            job_list
        )

        batch_result = BatchResult(
            source=batch_source,
            started_at=datetime.now(),
        )

        progress = ProgressTracker(
            total=len(job_list)
        )

        progress.start()

        self._notify_progress(
            progress_callback,
            progress.snapshot(),
        )

        for job in job_list:

            # Cooperative controls only take effect between EPUBs.
            # The current EPUB always finishes before pausing/stopping.
            if control is not None and not control.wait_until_ready():
                break

            book_result = self._run_file_with_checkers(
                job=job,
                checkers=selected_checkers,
                fast_readability=fast_readability,
                zip_integrity=zip_integrity,
            )

            batch_result.add_result(
                book_result
            )

            if book_result.passed:
                progress.mark_passed()

            elif book_result.failed:
                progress.mark_failed()

            else:
                progress.mark_completed()

            self._notify_progress(
                progress_callback,
                progress.snapshot(),
            )

        batch_result.finished_at = datetime.now()

        return batch_result

    # ------------------------------------------------------------------
    # Public API - checker selection
    # ------------------------------------------------------------------

    def available_checkers(self) -> list[str]:
        """
        Return names of all registered checkers.

        This method is intended to be useful for GUI and CLI layers.

        Example
        -------
        [
            "Accessibility",
            "CSS",
            "Font",
            "HTML",
            ...
        ]
        """

        return self.registry.names()

    def create_checkers(
        self,
        checker_names: Sequence[str] | None = None,
    ) -> list[BaseChecker]:
        """
        Public wrapper for creating checker instances.

        Parameters
        ----------
        checker_names:
            Selected checker names.

            None
                Create all registered checkers.

        Returns
        -------
        list[BaseChecker]
            Fresh checker instances.
        """

        return self._create_checkers(
            checker_names
        )

    # ------------------------------------------------------------------
    # Internal execution
    # ------------------------------------------------------------------

    def _run_file_with_checkers(
        self,
        job: ScanJob,
        checkers: Sequence[BaseChecker],
        fast_readability: bool = False,
        zip_integrity: bool = False,
    ) -> BookResult:
        """
        Execute a specific set of checker instances against one EPUB.

        This is separated from run_file() because batch execution
        creates checker instances once and reuses the checker classes
        for every EPUB.

        The actual checker instances are stateless in the current
        project, so this avoids repeatedly constructing the same
        checker objects for a large library.
        """

        self._validate_job(job)

        book_result = BookResult(
            path=job.path,
            started_at=datetime.now(),
        )

        # Integrity runs BEFORE EPUBContext.load(). This is essential:
        # a corrupt ZIP might prevent the context from opening at all.
        integrity = IntegrityChecker()
        try:
            raw = self._fast_integrity(job.path, integrity) if fast_readability else integrity.check_path(job.path)
            integrity_results = self._normalize_checker_results(integrity, raw)
        except Exception as exc:
            integrity_results = [
                self._runner_error(
                    message="Integrity preflight raised an exception",
                    file=str(job.path),
                    location="Integrity",
                    exception=exc,
                )
            ]

        book_result.extend(integrity_results)

        # Dedicated full-archive CRC mode: do not load EPUBContext, parse
        # hundreds of chapters, or run any optional quality checkers.
        # Readability remains UNKNOWN when CRC succeeds (not tested).
        if zip_integrity:
            book_result.finished_at = datetime.now()
            return book_result

        # Do not attempt to parse an EPUB with a critical integrity error.
        # ERROR and WARNING are reported, but other checkers can still run.
        if any(
            not result.success and result.severity == Severity.CRITICAL
            for result in integrity_results
        ):
            book_result.finished_at = datetime.now()
            return book_result

        context: EPUBContext | None = None
        try:
            context = EPUBContext(job.path)
            context.load()
        except Exception as exc:
            book_result.add_result(
                self._runner_error(
                    message="Failed to load EPUB",
                    file=str(job.path),
                    location="",
                    exception=exc,
                )
            )
            self._close_context(context)
            book_result.finished_at = datetime.now()
            return book_result

        try:
            # Readability preflight runs once for every successfully loaded
            # EPUB, independently of the optional quality-checker selection.
            # The checker reports chapter issues without stopping other checks.
            readable_checker = ReadableContentChecker()
            if fast_readability:
                try:
                    raw_readable = readable_checker.check(context, fast=True)
                    readable_results = self._normalize_checker_results(readable_checker, raw_readable)
                except Exception as exc:
                    readable_results = [self._runner_error(
                        message="Fast readability checker raised an exception",
                        file=str(job.path), location="ReadableContent", exception=exc,
                    )]
            else:
                readable_results = self._run_checker(
                    checker=readable_checker,
                    context=context,
                )
            book_result.extend(readable_results)

            for checker in checkers:
                # Both preflight checkers have already run; avoid duplicates
                # if either is registered by the CLI/GUI in the future.
                if isinstance(checker, (IntegrityChecker, ReadableContentChecker)):
                    continue

                results = self._run_checker(
                    checker=checker,
                    context=context,
                )
                book_result.extend(results)
        finally:
            self._close_context(context)

        book_result.finished_at = datetime.now()
        return book_result

    @staticmethod
    def _fast_integrity(path: Path, checker: IntegrityChecker) -> list[CheckResult]:
        """Check ZIP directory and essential EPUB package files without testzip().

        Does NOT decompress all entries or verify all CRCs. The sampled
        ReadableContent check verifies only the chosen chapter payloads.
        """
        try:
            with zipfile.ZipFile(path) as archive:
                names = set(archive.namelist())
                if not names:
                    return [checker.critical("Empty EPUB ZIP", str(path))]
                if "mimetype" not in names:
                    return [checker.critical("Missing mimetype", "mimetype")]
                if archive.read("mimetype") != b"application/epub+zip":
                    return [checker.error("Invalid mimetype", "mimetype")]
                if "META-INF/container.xml" not in names:
                    return [checker.critical("Missing container.xml", "META-INF/container.xml")]
                root = ET.fromstring(archive.read("META-INF/container.xml"))
                paths = [el.get("full-path", "").strip() for el in root.iter()
                         if el.tag.rsplit("}", 1)[-1] == "rootfile"]
                if not any(paths):
                    return [checker.critical("No OPF rootfile in container.xml", "META-INF/container.xml")]
                opf = posixpath.normpath(next(p for p in paths if p))
                if opf.startswith(("../", "/")) or opf == ".." or opf not in names:
                    return [checker.critical("Missing or unsafe OPF path", opf)]
                package = ET.fromstring(archive.read(opf))
                if package.tag.rsplit("}", 1)[-1] != "package":
                    return [checker.error("OPF root element is not package", opf)]
                return [checker.ok()]
        except (zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError, EOFError,
                OSError, ValueError, ET.ParseError, NotImplementedError) as exc:
            return [checker.critical(
                f"Cannot read EPUB package: {type(exc).__name__}: {exc}", str(path))]

    def _run_checker(
        self,
        checker: BaseChecker,
        context: EPUBContext,
    ) -> list[CheckResult]:
        """
        Execute one checker safely.

        A checker exception is converted into a CRITICAL CheckResult
        instead of crashing the entire batch.
        """

        try:
            raw_results = checker.check(context)

        except Exception as exc:
            return [
                self._runner_error(
                    message=(
                        f"Checker '{checker.name}' raised an exception"
                    ),
                    file=str(context.path),
                    location=checker.name,
                    exception=exc,
                )
            ]

        return self._normalize_checker_results(
            checker=checker,
            results=raw_results,
        )

    # ------------------------------------------------------------------
    # Checker result handling
    # ------------------------------------------------------------------

    def _normalize_checker_results(
        self,
        checker: BaseChecker,
        results: Any,
    ) -> list[CheckResult]:
        """
        Normalize checker output into list[CheckResult].

        Current project checkers return lists.

        This method also handles a single CheckResult defensively,
        making the Runner slightly more tolerant of future checkers.
        """

        if results is None:
            return [
                self._runner_error(
                    message=(
                        f"Checker '{checker.name}' returned no result"
                    ),
                    file="",
                    location=checker.name,
                )
            ]

        if isinstance(results, CheckResult):
            return [results]

        if isinstance(results, (list, tuple)):
            normalized: list[CheckResult] = []

            for result in results:

                if isinstance(result, CheckResult):
                    normalized.append(result)

                else:
                    normalized.append(
                        self._runner_error(
                            message=(
                                f"Checker '{checker.name}' "
                                "returned an invalid result"
                            ),
                            file="",
                            location=checker.name,
                        )
                    )

            if normalized:
                return normalized

            return [
                self._runner_error(
                    message=(
                        f"Checker '{checker.name}' "
                        "returned an empty result list"
                    ),
                    file="",
                    location=checker.name,
                )
            ]

        return [
            self._runner_error(
                message=(
                    f"Checker '{checker.name}' "
                    "returned an unsupported result type"
                ),
                file="",
                location=checker.name,
            )
        ]

    # ------------------------------------------------------------------
    # Checker creation
    # ------------------------------------------------------------------

    def _create_checkers(
        self,
        checker_names: Sequence[str] | None,
    ) -> list[BaseChecker]:
        """
        Create checker instances from the registry.

        None means all registered checkers.
        """

        if checker_names is None:
            return self.registry.create_all()

        names = list(checker_names)

        if not names:
            raise ValueError(
                "At least one checker must be selected."
            )

        unknown = [
            name
            for name in names
            if not self.registry.exists(name)
        ]

        if unknown:
            available = ", ".join(
                self.registry.names()
            )

            unknown_text = ", ".join(
                str(name)
                for name in unknown
            )

            raise KeyError(
                f"Unknown checker(s): {unknown_text}. "
                f"Available checkers: {available}"
            )

        return self.registry.create_selected(
            names
        )

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    @staticmethod
    def _notify_progress(
        callback: ProgressCallback | None,
        snapshot: ProgressSnapshot,
    ) -> None:
        """
        Notify the caller about progress.

        A callback exception is deliberately allowed to propagate.
        This makes programming errors in GUI/CLI callbacks visible
        instead of silently hiding them.
        """

        if callback is None:
            return

        callback(snapshot)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_job(
        job: ScanJob,
    ) -> None:
        """
        Validate a ScanJob before execution.
        """

        if not isinstance(job, ScanJob):
            raise TypeError(
                "job must be a ScanJob instance."
            )

        if not job.path.exists():
            raise FileNotFoundError(
                f"EPUB file does not exist: {job.path}"
            )

        if not job.path.is_file():
            raise IsADirectoryError(
                f"Expected an EPUB file: {job.path}"
            )

        if job.path.suffix.casefold() != ".epub":
            raise ValueError(
                f"Expected an EPUB file: {job.path}"
            )

    @classmethod
    def _validate_jobs(
        cls,
        jobs: Sequence[ScanJob],
    ) -> None:
        """
        Validate a complete list of ScanJob objects.
        """

        for job in jobs:
            cls._validate_job(job)

    # ------------------------------------------------------------------
    # Batch source
    # ------------------------------------------------------------------

    @staticmethod
    def _determine_batch_source(
        jobs: Sequence[ScanJob],
    ) -> Path:
        """
        Determine a useful source path for BatchResult.

        For a single EPUB, the EPUB path itself is returned.

        For multiple EPUBs, the common parent directory is returned.
        """

        if not jobs:
            return Path.cwd()

        if len(jobs) == 1:
            return jobs[0].path

        try:
            common = Path(
                Path.cwd().anchor
            )

            common_path = jobs[0].path

            for job in jobs[1:]:
                common_path = Path(
                    _common_path(
                        common_path,
                        job.path,
                    )
                )

            return common_path

        except Exception:
            return jobs[0].path.parent

    # ------------------------------------------------------------------
    # Context handling
    # ------------------------------------------------------------------

    @staticmethod
    def _close_context(
        context: EPUBContext | None,
    ) -> None:
        """
        Close an EPUBContext safely.

        Closing errors should not hide the actual checker result.
        """

        if context is None:
            return

        try:
            context.close()

        except Exception:
            pass

    # ------------------------------------------------------------------
    # Error result creation
    # ------------------------------------------------------------------

    @classmethod
    def _runner_error(
        cls,
        message: str,
        file: str = "",
        location: str = "",
        exception: Exception | None = None,
    ) -> CheckResult:
        """
        Create a CRITICAL CheckResult for Runner-level failures.
        """

        if exception is not None:
            message = (
                f"{message}: "
                f"{exception.__class__.__name__}: "
                f"{exception}"
            )

        return CheckResult(
            checker=cls.RUNNER_CHECKER_NAME,
            success=False,
            message=message,
            file=file,
            location=location,
            severity=Severity.CRITICAL,
        )


# ----------------------------------------------------------------------
# Standalone helper
# ----------------------------------------------------------------------

def _common_path(
    first: Path,
    second: Path,
) -> str:
    """
    Return the common path between two filesystem paths.

    pathlib.Path.commonpath() does not exist, so os.path.commonpath()
    is used internally here without exposing os.path throughout the
    Runner implementation.
    """

    import os

    return os.path.commonpath(
        [
            str(first),
            str(second),
        ]
    )
