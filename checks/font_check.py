import io

from fontTools.ttLib import TTFont

from checks.resource_checker import ResourceChecker


class FontChecker(ResourceChecker):

    name = "Font"

    def check(self, ctx):

        results = []

        hashes = set()

        for font in ctx.font_files:

            path = font["path"]

            data = self.read_resource(
                ctx,
                path,
                results
            )

            if data is None:
                continue

            self.check_duplicate(
                data,
                path,
                hashes,
                results
            )

            self._validate_font(
                data,
                path,
                results
            )

        if not results:

            results.append(
                self.ok()
            )

        return results

    # ==================================

    def _validate_font(
        self,
        data,
        path,
        results
    ):

        try:

            TTFont(
                io.BytesIO(data)
            )

        except Exception:

            results.append(
                self.error(
                    "Corrupted font",
                    path
                )
            )