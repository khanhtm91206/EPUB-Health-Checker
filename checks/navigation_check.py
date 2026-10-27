import xml.etree.ElementTree as ET

from checks.base_checker import BaseChecker


class NavigationChecker(BaseChecker):

    name = "Navigation"

    def check(self, ctx):

        if ctx.nav_file is None:

            return [

                self.warning(

                    "Navigation document not found"

                )

            ]

        path = ctx.nav_file["path"]

        try:

            root = ctx.read_xml(path)

        except Exception:

            return [

                self.error(

                    "Cannot parse navigation document",

                    path

                )

            ]

        return self._validate_nav(

            path,

            root

        )

    # ==========================================

    def _validate_nav(

        self,

        path,

        root

    ):

        ns = {

            "epub": "http://www.idpf.org/2007/ops"

        }

        for nav in root.iter():

            if nav.tag.endswith("nav"):

                epub_type = nav.attrib.get(

                    "{http://www.idpf.org/2007/ops}type",

                    ""

                )

                if epub_type == "toc":

                    return [

                        self.ok()

                    ]

        return [

            self.error(

                "No TOC navigation found",

                path

            )

        ]