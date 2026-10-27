from .base_html_check import BaseHTMLCheck


class TitleCheck(BaseHTMLCheck):

    def run(

        self,

        ctx,

        doc,

        results

    ):

        title = doc.title

        if title == "":

            results.append(

                self.warning(

                    "Missing or empty <title>",

                    doc.path

                )

            )