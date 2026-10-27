from checks.base_checker import BaseChecker

from checks.quality.duplicate_id import DuplicateIDCheck
from checks.quality.empty_tag import EmptyTagCheck
from checks.quality.empty_href import EmptyHrefCheck
from checks.quality.empty_src import EmptySrcCheck
from checks.quality.broken_fragment import BrokenFragmentCheck
from checks.quality.nested_anchor import NestedAnchorCheck
from checks.quality.namespace import NamespaceCheck


class QualityChecker(BaseChecker):

    name = "Quality"

    def __init__(self):

        self.checks = [

            DuplicateIDCheck(),

            EmptyTagCheck(),

            EmptyHrefCheck(),

            EmptySrcCheck(),

            BrokenFragmentCheck(),

            NestedAnchorCheck(),

            NamespaceCheck(),

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