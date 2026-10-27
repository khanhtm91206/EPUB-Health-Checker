"""
engine/scanner.py

EPUB file discovery engine.

Responsibilities
----------------
- Scan a single EPUB file.
- Scan a directory for EPUB files.
- Optionally scan subdirectories recursively.
- Ignore non-EPUB files.
- Produce deterministic scan results.
- Create ScanJob objects for discovered EPUB files.

The Scanner does NOT:
- Open EPUB files.
- Validate EPUB files.
- Run checkers.
- Generate reports.
- Print results.

Those responsibilities belong to other parts of the application.

This separation allows the Scanner to be reused by:
- GUI
- CLI
- Batch Runner
- Tests
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from models import ScanJob


class Scanner:
    """
    Discover EPUB files from a file or directory.

    The Scanner supports two input modes:

    1. Single EPUB file

        scanner.scan("book.epub")

    2. Directory

        scanner.scan("library/")

    Directory scanning can be recursive:

        scanner.scan(
            "library/",
            recursive=True,
        )

    Parameters
    ----------
    epub_extensions:
        File extensions that are considered EPUB files.

        By default only ".epub" is accepted.

        Extensions are normalized to lowercase.
    """

    DEFAULT_EPUB_EXTENSIONS = frozenset({".epub"})

    def __init__(
        self,
        epub_extensions: Iterable[str] | None = None,
    ) -> None:

        if epub_extensions is None:
            self._epub_extensions = self.DEFAULT_EPUB_EXTENSIONS

        else:
            self._epub_extensions = frozenset(
                self._normalize_extension(extension)
                for extension in epub_extensions
            )

            if not self._epub_extensions:
                raise ValueError(
                    "At least one EPUB extension must be provided."
                )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(
        self,
        path: str | Path,
        recursive: bool = True,
    ) -> list[ScanJob]:
        """
        Scan a file or directory for EPUB files.

        Parameters
        ----------
        path:
            EPUB file or directory to scan.

        recursive:
            When scanning a directory:

            True
                Include EPUB files from all subdirectories.

            False
                Only scan EPUB files directly inside the directory.

        Returns
        -------
        list[ScanJob]
            Discovered EPUB files sorted deterministically.

        Raises
        ------
        FileNotFoundError
            If the supplied path does not exist.

        ValueError
            If the supplied path is neither a file nor directory.

        IsADirectoryError
            If a directory is passed to scan_file().

        NotADirectoryError
            If a file is passed to scan_directory().
        """

        target = self._normalize_path(path)

        if not target.exists():
            raise FileNotFoundError(
                f"Scan path does not exist: {target}"
            )

        if target.is_file():
            return self.scan_file(target)

        if target.is_dir():
            return self.scan_directory(
                target,
                recursive=recursive,
            )

        raise ValueError(
            f"Unsupported scan path: {target}"
        )

    def scan_file(
        self,
        path: str | Path,
    ) -> list[ScanJob]:
        """
        Scan exactly one EPUB file.

        The method intentionally returns a list rather than a single
        ScanJob so that the return type is consistent with scan()
        and scan_directory().

        Parameters
        ----------
        path:
            Path to the EPUB file.

        Returns
        -------
        list[ScanJob]
            A list containing zero or one ScanJob.

        Raises
        ------
        FileNotFoundError
            If the file does not exist.

        IsADirectoryError
            If the supplied path is a directory.
        """

        target = self._normalize_path(path)

        if not target.exists():
            raise FileNotFoundError(
                f"EPUB file does not exist: {target}"
            )

        if not target.is_file():
            raise IsADirectoryError(
                f"Expected an EPUB file, got: {target}"
            )

        if not self.is_epub(target):
            return []

        return [
            self._create_job(
                path=target,
                root=None,
            )
        ]

    def scan_directory(
        self,
        directory: str | Path,
        recursive: bool = True,
    ) -> list[ScanJob]:
        """
        Scan a directory for EPUB files.

        Parameters
        ----------
        directory:
            Directory containing EPUB files.

        recursive:
            If True, scan all subdirectories.

            If False, scan only the immediate directory.

        Returns
        -------
        list[ScanJob]
            Discovered EPUB files sorted by relative path.

        Raises
        ------
        FileNotFoundError
            If the directory does not exist.

        NotADirectoryError
            If the supplied path is a file.
        """

        root = self._normalize_path(directory)

        if not root.exists():
            raise FileNotFoundError(
                f"Scan directory does not exist: {root}"
            )

        if not root.is_dir():
            raise NotADirectoryError(
                f"Expected a directory, got: {root}"
            )

        epub_paths = self._discover_epubs(
            root=root,
            recursive=recursive,
        )

        jobs: list[ScanJob] = []

        for epub_path in epub_paths:
            jobs.append(
                self._create_job(
                    path=epub_path,
                    root=root,
                )
            )

        return jobs

    def is_epub(
        self,
        path: str | Path,
    ) -> bool:
        """
        Determine whether a path represents an EPUB file.

        The check is intentionally based on the file extension only.

        It does NOT open or validate the EPUB.

        Parameters
        ----------
        path:
            File path to inspect.

        Returns
        -------
        bool
            True when the path has a supported EPUB extension.
        """

        target = Path(path)

        if not target.is_file():
            return False

        return target.suffix.lower() in self._epub_extensions

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _discover_epubs(
        self,
        root: Path,
        recursive: bool,
    ) -> list[Path]:
        """
        Discover EPUB files beneath a directory.

        Results are sorted by normalized relative path so that scans
        produce the same ordering on every run.
        """

        if recursive:
            candidates = root.rglob("*")

        else:
            candidates = root.iterdir()

        epub_paths: list[Path] = []

        for candidate in candidates:

            if not candidate.is_file():
                continue

            if not self.is_epub(candidate):
                continue

            epub_paths.append(candidate)

        epub_paths.sort(
            key=lambda path: self._sort_key(
                path.relative_to(root)
            )
        )

        return epub_paths

    # ------------------------------------------------------------------
    # ScanJob creation
    # ------------------------------------------------------------------

    def _create_job(
        self,
        path: Path,
        root: Path | None,
    ) -> ScanJob:
        """
        Create a ScanJob for one EPUB.

        File size is captured here so later stages do not need to call
        stat() again merely to display the size.
        """

        resolved_path = path.resolve()

        try:
            size = resolved_path.stat().st_size

        except OSError as exc:
            raise OSError(
                f"Unable to read file information for: "
                f"{resolved_path}"
            ) from exc

        relative_path: str | None

        if root is None:
            relative_path = resolved_path.name

        else:
            try:
                relative_path = str(
                    resolved_path.relative_to(
                        root.resolve()
                    )
                )

            except ValueError:
                # This should normally never happen because the path
                # came from the root directory. Keeping this fallback
                # makes ScanJob creation safe if the method is reused.
                relative_path = resolved_path.name

        return ScanJob(
            path=resolved_path,
            size=size,
            relative_path=relative_path,
        )

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_path(
        path: str | Path,
    ) -> Path:
        """
        Normalize an input path.

        expanduser()
            Supports paths such as ~/books.

        resolve()
            Produces an absolute, normalized path.
        """

        if not isinstance(path, (str, Path)):
            raise TypeError(
                "Scan path must be a string or pathlib.Path."
            )

        return Path(path).expanduser().resolve()

    @staticmethod
    def _normalize_extension(
        extension: str,
    ) -> str:
        """
        Normalize a configured file extension.

        Examples
        --------
        "epub"  -> ".epub"
        ".EPUB" -> ".epub"
        ".epub" -> ".epub"
        """

        if not isinstance(extension, str):
            raise TypeError(
                "EPUB extension must be a string."
            )

        normalized = extension.strip().lower()

        if not normalized:
            raise ValueError(
                "EPUB extension cannot be empty."
            )

        if not normalized.startswith("."):
            normalized = f".{normalized}"

        return normalized

    @staticmethod
    def _sort_key(
        relative_path: Path,
    ) -> str:
        """
        Return a stable sorting key.

        Windows paths are case-insensitive in normal usage, so using
        casefold() prevents unexpected ordering differences caused by
        filename capitalization.
        """

        return str(relative_path).replace(
            "\\",
            "/",
        ).casefold()