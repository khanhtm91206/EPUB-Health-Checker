from .base_html_check import BaseHTMLCheck


class AltCheck(BaseHTMLCheck):

    def run(

        self,

        ctx,

        doc,

        results

    ):

        for img in doc.images:

            alt = img.attrib.get("alt")

            if alt is None:

                results.append(

                    self.error(

                        "Image missing alt attribute",

                        doc.path

                    )

                )

                continue

            if not alt.strip():

                results.append(

                    self.warning(

                        "Empty alt attribute",

                        doc.path

                    )

                )