from .base_html_check import BaseHTMLCheck


class LangCheck(BaseHTMLCheck):

    def run(
        self,
        ctx,
        doc,
        results
    ):

        lang = doc.language

        if lang == "":

            results.append(

                self.warning(

                    "Missing html language",

                    doc.path

                )

            )

            return

        if len(lang.strip()) < 2:

            results.append(

                self.warning(

                    "Invalid language code",

                    doc.path

                )

            )