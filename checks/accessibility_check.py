from checks.base_checker import BaseChecker

from checks.accessibility.alt_check import AltCheck
from checks.accessibility.title_check import TitleCheck
from checks.accessibility.lang_check import LangCheck
from checks.accessibility.heading_check import HeadingCheck
from checks.accessibility.landmark_check import LandmarkCheck


class AccessibilityChecker(BaseChecker):

    name = "Accessibility"

    def __init__(self):

        self.checks = [

            AltCheck(),

            TitleCheck(),

            LangCheck(),

            HeadingCheck(),

            LandmarkCheck(),

        ]

    def check(self, ctx):

        results = []

        for item in ctx.html_files:

            try:

                doc = ctx.get_html(item)

            except Exception:

                continue

            for checker in self.checks:

                checker.run(

                    ctx,

                    doc,

                    results

                )

        if not results:

            results.append(

                self.ok()

            )

        return results