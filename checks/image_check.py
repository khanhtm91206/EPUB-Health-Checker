import io

from PIL import Image

from checks.resource_checker import ResourceChecker


class ImageChecker(ResourceChecker):

    name = "Image"

    def check(self, ctx):

        results = []

        hashes = set()

        for image in ctx.image_files:

            path = image["path"]

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

            self._validate_image(
                data,
                path,
                results
            )

        # -------------------------
        # Unused Images
        # -------------------------

        unused = set()

        for image in ctx.image_files:

            path = image["path"]

            if path in unused:
                continue

            if path not in ctx.used_images:

                unused.add(path)

                results.append(
                    self.warning(
                        "Unused image",
                        path
                    )
                )

        if not results:

            results.append(
                self.ok()
            )

        return results

    # ==================================

    def _validate_image(
        self,
        data,
        path,
        results
    ):

        try:

            with Image.open(
                io.BytesIO(data)
            ) as img:

                img.verify()

        except Exception:

            results.append(
                self.error(
                    "Corrupted image",
                    path
                )
            )