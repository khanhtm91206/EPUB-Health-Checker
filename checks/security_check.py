from checks.base_checker import BaseChecker

from checks.security.script_check import ScriptCheck
from checks.security.iframe_check import IFrameCheck
from checks.security.object_check import ObjectCheck
from checks.security.embed_check import EmbedCheck
from checks.security.form_check import FormCheck
from checks.security.javascript_uri_check import JavaScriptURICheck
from checks.security.inline_event_check import InlineEventCheck


class SecurityChecker(BaseChecker):

    name = "Security"

    def __init__(self):

        self.checks = [

            ScriptCheck(),

            IFrameCheck(),

            ObjectCheck(),

            EmbedCheck(),

            FormCheck(),

            JavaScriptURICheck(),

            InlineEventCheck(),

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