from .base_html_check import BaseHTMLCheck


class LandmarkCheck(BaseHTMLCheck):

    LANDMARKS = {

        "header",

        "main",

        "nav",

        "footer",

        "aside"

    }

    def run(
        self,
        ctx,
        doc,
        results
    ):

        found = False

        for node in doc.root.iter():

            tag = node.tag.split("}")[-1].lower()

            if tag in self.LANDMARKS:

                found = True

                break

        if not found:

            results.append(

                self.warning(

                    "No landmark element found",

                    doc.path

                )

            )