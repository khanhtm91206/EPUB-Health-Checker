"""Performance checks with fault isolation for missing EPUB resources.

Drop-in replacement for checks/performance_check.py.
Existing six subchecks are preserved without modification.
"""

from zipfile import BadZipFile, LargeZipFile

from checks.base_checker import BaseChecker
from checks.performance.html_size_check import HTMLSizeCheck
from checks.performance.css_size_check import CSSSizeCheck
from checks.performance.image_size_check import ImageSizeCheck
from checks.performance.font_size_check import FontSizeCheck
from checks.performance.duplicate_css_check import DuplicateCSSCheck
from checks.performance.duplicate_image_check import DuplicateImageCheck


class PerformanceChecker(BaseChecker):
    name = "Performance"

    def __init__(self):
        self.checks = [
            HTMLSizeCheck(),
            CSSSizeCheck(),
            ImageSizeCheck(),
            FontSizeCheck(),
            DuplicateCSSCheck(),
            DuplicateImageCheck(),
        ]

    def check(self, ctx):
        results = []
        for checker in self.checks:
            try:
                checker.run(ctx, results)
            except KeyError as exc:
                # Subcheck may have emitted findings before the missing item.
                # Keep those findings; let the next subcheck run normally.
                results.append(self.warning(
                    "Performance check skipped a missing archive resource "
                    f"during {type(checker).__name__}: {exc}"
                ))
            except (OSError, EOFError, BadZipFile, LargeZipFile) as exc:
                # Unexpected read/decompression errors should be visible but
                # must not stop the remaining independent performance checks.
                results.append(self.error(
                    f"{type(checker).__name__} could not read an EPUB resource: "
                    f"{type(exc).__name__}: {exc}"
                ))

        if not results:
            results.append(self.ok())
        return results

