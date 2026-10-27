import xml.etree.ElementTree as ET

from checks.base_checker import BaseChecker


class LinkChecker(BaseChecker):

    name = "Link"

    LINK_ATTRIBUTES = (

        "href",

        "src",

        "data",

        "poster",

        "{http://www.w3.org/1999/xlink}href",

    )

    def check(self, ctx):

        results = []

        for html in ctx.html_files:

            path = html["path"]

            try:

                root = ctx.read_xml(path)

            except Exception:

                continue

            results.extend(

                self._check_links(

                    ctx,

                    path,

                    root

                )

            )

        if not results:

            results.append(

                self.ok()

            )

        return results

    # =====================================================

    def _check_links(

        self,

        ctx,

        html_file,

        root

    ):

        results = []

        for element in root.iter():

            for attr in self.LINK_ATTRIBUTES:

                target = element.attrib.get(attr)

                if not target:

                    continue

                # ----------------------------
                # Ignore external links
                # ----------------------------

                if target.startswith(

                    (

                        "http://",

                        "https://",

                        "mailto:",

                        "tel:",

                        "javascript:",

                        "data:",

                    )

                ):

                    continue

                fragment = ""

                if "#" in target:

                    target, fragment = target.split("#", 1)

                if target == "":

                    full_path = html_file

                else:

                    full_path = ctx.resolve_path(

                        html_file,

                        target

                    )

                # ----------------------------
                # File exists?
                # ----------------------------

                if not ctx.exists(full_path):

                    results.append(

                        self.error(

                            "Broken link",

                            html_file,

                            target

                        )

                    )

                    continue

                # ----------------------------
                # Anchor
                # ----------------------------

                if fragment:

                    results.extend(

                        self._check_anchor(

                            ctx,

                            full_path,

                            fragment

                        )

                    )

        return results

    # =====================================================

    def _check_anchor(

        self,

        ctx,

        html_file,

        anchor

    ):

        results = []

        try:

            root = ctx.read_xml(html_file)

        except Exception:

            return results

        for element in root.iter():

            if element.attrib.get("id") == anchor:

                return results

        results.append(

            self.error(

                "Broken anchor",

                html_file,

                anchor

            )

        )

        return results