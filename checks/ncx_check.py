import xml.etree.ElementTree as ET

from checks.base_checker import BaseChecker


class NCXChecker(BaseChecker):

    name = "NCX"

    def check(self, ctx):

        if ctx.ncx_file is None:

            return [

                self.warning(

                    "NCX not found"

                )

            ]

        path = ctx.ncx_file["path"]

        try:

            root = ctx.read_xml(path)

        except Exception:

            return [

                self.error(

                    "Cannot parse NCX",

                    path

                )

            ]

        return self._validate(root, path)

    # =========================================

    def _validate(

        self,

        root,

        path

    ):

        nav_map = None

        for node in root.iter():

            if node.tag.endswith("navMap"):

                nav_map = node

                break

        if nav_map is None:

            return [

                self.error(

                    "Missing navMap",

                    path

                )

            ]

        nav_points = []

        for node in nav_map:

            if node.tag.endswith("navPoint"):

                nav_points.append(node)

        if not nav_points:

            return [

                self.error(

                    "No navPoint",

                    path

                )

            ]

        return [

            self.ok()

        ]