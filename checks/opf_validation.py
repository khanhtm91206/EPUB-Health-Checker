from checks.base_checker import BaseChecker


class OPFValidationChecker(BaseChecker):

    name = "OPF Validation"

    def check(self, ctx):

        results = []

        # -------------------------
        # Missing file
        # -------------------------

        for item in ctx.manifest.values():

            if not ctx.exists(item["path"]):

                results.append(

                    self.error(

                        "Missing file",

                        item["path"]

                    )

                )

        # -------------------------
        # Invalid spine
        # -------------------------

        for idref in ctx.spine:

            if idref not in ctx.manifest:

                results.append(

                    self.error(

                        f"Invalid spine reference: {idref}"

                    )

                )

        # -------------------------
        # Duplicate href
        # -------------------------

        used = set()

        for item in ctx.manifest.values():

            href = item["href"]

            if href in used:

                results.append(

                    self.warning(

                        f"Duplicate href: {href}"

                    )

                )

            used.add(href)

        if not results:

            results.append(

                self.ok()

            )

        return results