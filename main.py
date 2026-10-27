from pathlib import Path
import sys

from core.epub_context import EPUBContext

from checks.structure_check import StructureChecker
from checks.opf_check import OPFChecker
from checks.opf_validation import OPFValidationChecker
from checks.metadata_check import MetadataChecker
from checks.html_check import HTMLChecker
from checks.css_check import CSSChecker
from checks.image_check import ImageChecker
from checks.font_check import FontChecker
from checks.link_check import LinkChecker
from checks.navigation_check import NavigationChecker
from checks.ncx_check import NCXChecker
from checks.accessibility_check import AccessibilityChecker
from checks.accessibility_check import AccessibilityChecker
from checks.quality_check import QualityChecker
from checks.security_check import SecurityChecker
from checks.performance_check import PerformanceChecker

from core.report import Report
from core.printer import ConsolePrinter


ALL_CHECKERS = [

    StructureChecker(),

    OPFChecker(),

    OPFValidationChecker(),

    MetadataChecker(),

    HTMLChecker(),

    LinkChecker(),

    NavigationChecker(),

    NCXChecker(),

    AccessibilityChecker(),

    QualityChecker(),

    CSSChecker(),

    ImageChecker(),

    FontChecker(),

    SecurityChecker(),

    PerformanceChecker(),

]


def run_epub(epub_path: Path):

    ctx = EPUBContext(epub_path)

    report = Report()

    try:

        ctx.load()

        for checker in ALL_CHECKERS:

            report.add(checker.check(ctx))

    finally:

        ctx.close()

    ConsolePrinter().print_report(

        epub_path,

        report

    )

    report_dir = Path("reports")

    report_dir.mkdir(

        exist_ok=True

    )

    report.save_json(

        report_dir / f"{epub_path.stem}.json"

    )

    return report


def run_folder(folder: Path):

    epubs = sorted(

        folder.rglob("*.epub")

    )

    if not epubs:

        print("No EPUB files found.")

        return

    passed = 0

    failed = 0

    print()

    print("=" * 60)

    print(f"Scanning : {folder}")

    print("=" * 60)

    for epub in epubs:

        try:

            report = run_epub(epub)

            if report.failed == 0:

                passed += 1

            else:

                failed += 1

        except Exception as e:

            failed += 1

            print()

            print(epub.name)

            print(e)

    print()

    print("=" * 60)

    print("Batch Summary")

    print("=" * 60)

    print(f"Total EPUB : {len(epubs)}")

    print(f"Passed     : {passed}")

    print(f"Failed     : {failed}")

    print("=" * 60)


def main():

    if len(sys.argv) != 2:

        print(

            "Usage:\n"

            "python main.py book.epub\n"

            "python main.py samples/"

        )

        return

    path = Path(sys.argv[1])

    if not path.exists():

        print(f"Not found : {path}")

        return

    if path.is_dir():

        run_folder(path)

    else:

        run_epub(path)


if __name__ == "__main__":

    main()