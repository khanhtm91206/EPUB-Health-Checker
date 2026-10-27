from checks.base_checker import BaseChecker


class StructureChecker(BaseChecker):

    name = "Structure"

    def check(self, ctx):

        if not ctx.exists("mimetype"):

            return [
                self.critical(
                    "Missing mimetype"
                )
            ]

        if not ctx.exists("META-INF/container.xml"):

            return [
                self.critical(
                    "Missing container.xml"
                )
            ]

        if not ctx.exists(ctx.opf_path):

            return [
                self.critical(
                    "Missing OPF",
                    ctx.opf_path
                )
            ]

        return [
            self.ok()
        ]