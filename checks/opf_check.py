from checks.base_checker import BaseChecker


class OPFChecker(BaseChecker):

    name = "OPF"

    def check(self, ctx):

        if ctx.opf_tree is None:

            return [

                self.critical(

                    "Cannot parse OPF"

                )

            ]

        return [

            self.ok()

        ]