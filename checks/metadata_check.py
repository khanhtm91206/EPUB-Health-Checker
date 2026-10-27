from checks.base_checker import BaseChecker


class MetadataChecker(BaseChecker):

    name = "Metadata"

    REQUIRED = [

        "title",

        "language",

        "identifier"

    ]

    def check(self, ctx):

        results = []

        for tag in self.REQUIRED:

            if not ctx.metadata.get(tag):

                results.append(

                    self.warning(

                        f"Missing {tag}"

                    )

                )

        if not results:

            results.append(

                self.ok()

            )

        return results