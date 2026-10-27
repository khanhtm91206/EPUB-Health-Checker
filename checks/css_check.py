import logging
import re

import cssutils

from checks.resource_checker import ResourceChecker


# ==========================================
# Disable cssutils console warnings
# ==========================================

cssutils.log.setLevel(logging.CRITICAL)


class CSSChecker(ResourceChecker):

    name = "CSS"

    def check(self, ctx):

        results = []

        hashes = set()

        for css in ctx.css_files:

            path = css["path"]

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

            self._validate_css(
                ctx,
                data,
                path,
                results
            )

        unused = set()

        for css in ctx.css_files:

            path = css["path"]

            if path in unused:
                continue

            if path not in ctx.used_css:

                unused.add(path)

                results.append(

                    self.warning(

                        "Unused CSS",

                        path

                    )

                )

        if not results:

            results.append(

                self.ok()

            )

        return results

    # ====================================================

    def _validate_css(

        self,

        ctx,

        data,

        path,

        results

    ):

        try:

            sheet = cssutils.parseString(

                data.decode(

                    "utf-8",

                    errors="replace"

                )

            )

        except Exception as e:

            results.append(

                self.error(

                    f"Invalid CSS: {e}",

                    path

                )

            )

            return

        self._check_urls(

            ctx,

            path,

            sheet,

            results

        )

        self._check_font_face(

            ctx,

            path,

            sheet,

            results

        )

    # ====================================================

    def _check_urls(

        self,

        ctx,

        css_file,

        sheet,

        results

    ):

        for rule in sheet:

            if rule.type != rule.STYLE_RULE:

                continue

            for prop in rule.style:

                urls = re.findall(

                    r'url\((.*?)\)',

                    prop.value

                )

                for url in urls:

                    url = url.strip().strip("'\"")

                    if (

                        not url

                        or url.startswith("data:")

                        or url.startswith("http:")

                        or url.startswith("https:")

                    ):

                        continue

                    full_path = ctx.resolve_path(

                        css_file,

                        url

                    )

                    if not ctx.exists(full_path):

                        results.append(

                            self.error(

                                f"Missing resource: {url}",

                                css_file

                            )

                        )

                        continue

                    lower = full_path.lower()

                    if lower.endswith((

                        ".png",

                        ".jpg",

                        ".jpeg",

                        ".gif",

                        ".webp",

                        ".svg",

                        ".bmp",

                        ".tif",

                        ".tiff"

                    )):

                        ctx.used_images.add(full_path)

                    elif lower.endswith((

                        ".ttf",

                        ".otf",

                        ".woff",

                        ".woff2"

                    )):

                        ctx.used_fonts.add(full_path)

    # ====================================================

    def _check_font_face(

        self,

        ctx,

        css_file,

        sheet,

        results

    ):

        for rule in sheet:

            if rule.type != rule.FONT_FACE_RULE:

                continue

            for prop in rule.style:

                if prop.name != "src":

                    continue

                urls = re.findall(

                    r'url\((.*?)\)',

                    prop.value

                )

                for url in urls:

                    url = url.strip().strip("'\"")

                    full_path = ctx.resolve_path(

                        css_file,

                        url

                    )

                    if not ctx.exists(full_path):

                        results.append(

                            self.error(

                                f"Missing font: {url}",

                                css_file

                            )

                        )

                        continue

                    ctx.used_fonts.add(full_path)