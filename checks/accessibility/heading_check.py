from .base_html_check import BaseHTMLCheck


class HeadingCheck(BaseHTMLCheck):

    def run(
        self,
        ctx,
        doc,
        results
    ):

        headings = []

        for level in range(1, 7):

            for node in doc.root.iter(f"{{*}}h{level}"):

                headings.append((level, node))

        if not headings:

            results.append(

                self.warning(

                    "Document has no heading",

                    doc.path

                )

            )

            return

        h1_count = sum(

            1

            for level, _ in headings

            if level == 1

        )

        if h1_count > 1:

            results.append(

                self.warning(

                    "Multiple H1 headings",

                    doc.path

                )

            )

        previous = headings[0][0]

        for level, _ in headings[1:]:

            if level > previous + 1:

                results.append(

                    self.warning(

                        f"Heading level skipped (H{previous} -> H{level})",

                        doc.path

                    )

                )

                break

            previous = level