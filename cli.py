
"""
cli.py

Command-line interface for EPUB Health Checker.

This module connects:
- Scanner
- CheckerRegistry
- Runner
- ConsolePrinter
- JSON / CSV / HTML exporters

It does not modify main.py.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from engine.scanner import Scanner
from engine.checker_registry import CheckerRegistry
from engine.runner import Runner
from core.printer import ConsolePrinter
from core.exporters import (
    JSONReporter,
    CSVReporter,
    HTMLReporter,
)


def build_registry() -> CheckerRegistry:
    """
    Register all current EPUB checkers.

    Explicit registration makes the CLI predictable and
    prevents importing arbitrary modules automatically.
    """

    from checks.structure_check import StructureChecker
    from checks.opf_check import OPFChecker
    from checks.opf_validation import OPFValidationChecker
    from checks.metadata_check import MetadataChecker
    from checks.html_check import HTMLChecker
    from checks.link_check import LinkChecker
    from checks.navigation_check import NavigationChecker
    from checks.ncx_check import NCXChecker
    from checks.accessibility_check import AccessibilityChecker
    from checks.quality_check import QualityChecker
    from checks.css_check import CSSChecker
    from checks.image_check import ImageChecker
    from checks.font_check import FontChecker
    from checks.security_check import SecurityChecker
    from checks.performance_check import PerformanceChecker

    registry = CheckerRegistry()

    checker_classes = [
        StructureChecker,
        OPFChecker,
        OPFValidationChecker,
        MetadataChecker,
        HTMLChecker,
        LinkChecker,
        NavigationChecker,
        NCXChecker,
        AccessibilityChecker,
        QualityChecker,
        CSSChecker,
        ImageChecker,
        FontChecker,
        SecurityChecker,
        PerformanceChecker,
    ]

    for checker_class in checker_classes:
        registry.register(checker_class)

    return registry


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="EPUB Health Checker",
        description=(
            "Validate one EPUB or recursively scan "
            "a directory of EPUB files."
        ),
    )

    parser.add_argument(
        "path",
        nargs="?",
        help="EPUB file or directory to scan",
    )

    parser.add_argument(
        "--list-checkers",
        action="store_true",
        help="Show available checkers",
    )

    parser.add_argument(
        "--checkers",
        nargs="+",
        metavar="NAME",
        help="Checker names to run (default: all)",
    )

    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not scan subdirectories",
    )

    parser.add_argument(
        "--format",
        choices=["json", "csv", "html", "all", "none"],
        default="all",
        help="Report output format (default: all)",
    )

    parser.add_argument(
        "--output",
        default="reports",
        help="Output directory (default: reports)",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-book console output",
    )

    return parser


def select_checkers(
    registry: CheckerRegistry,
    requested: list[str] | None,
) -> list[str]:
    available = registry.names()

    if requested is None:
        return available

    lookup = {
        name.casefold(): name
        for name in available
    }

    selected = []
    unknown = []

    for name in requested:
        actual = lookup.get(name.casefold())

        if actual is None:
            unknown.append(name)
        elif actual not in selected:
            selected.append(actual)

    if unknown:
        raise ValueError(
            "Unknown checker(s): "
            + ", ".join(unknown)
            + "\nAvailable checkers: "
            + ", ".join(available)
        )

    return selected


def export_reports(
    result,
    output_dir: Path,
    output_format: str,
) -> None:
    if output_format == "none":
        return

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    reporters = {
        "json": (JSONReporter(), ".json"),
        "csv": (CSVReporter(), ".csv"),
        "html": (HTMLReporter(), ".html"),
    }

    selected_formats = (
        list(reporters)
        if output_format == "all"
        else [output_format]
    )

    for format_name in selected_formats:
        reporter, extension = reporters[format_name]

        output_path = output_dir / (
            "epub_health_report" + extension
        )

        reporter.save(result, output_path)

        print(f"[EXPORT] {output_path.resolve()}")


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    try:
        registry = build_registry()

        if args.list_checkers:
            print("Available EPUB checkers:")

            for name in registry.names():
                print(f"  - {name}")

            return 0

        if not args.path:
            parser.error(
                "A path is required unless "
                "--list-checkers is used."
            )

        selected = select_checkers(
            registry,
            args.checkers,
        )

        scanner = Scanner()

        jobs = scanner.scan(
            args.path,
            recursive=not args.no_recursive,
        )

        if not jobs:
            print(
                "No EPUB files found.",
                file=sys.stderr,
            )
            return 1

        print(f"Found {len(jobs)} EPUB file(s).")
        print(f"Selected {len(selected)} checker(s).")

        runner = Runner(registry)
        printer = ConsolePrinter()

        def on_progress(snapshot):
            if args.quiet:
                return

            completed = snapshot.completed
            total = snapshot.total
            percent = snapshot.percent

            print(
                f"\rProgress: {completed}/{total} "
                f"({percent:.1f}%)",
                end="",
                flush=True,
            )

            if completed == total:
                print()

        batch = runner.run_batch(
            jobs,
            checker_names=selected,
            progress_callback=on_progress,
        )

        if not args.quiet:
            printer.print_batch(batch)
        else:
            print(
                f"Completed: {batch.total} EPUB(s)"
            )

        export_reports(
            batch,
            Path(args.output),
            args.format,
        )

        # Return nonzero when one or more books failed.
        return 1 if any(
            book.status != "PASS"
            for book in batch.results
        ) else 0

    except (OSError, ValueError, KeyError) as exc:
        print(
            f"Error: {exc}",
            file=sys.stderr,
        )
        return 2

    except KeyboardInterrupt:
        print(
            "\nScan cancelled by user.",
            file=sys.stderr,
        )
        return 130


if __name__ == "__main__":
    sys.exit(main())
