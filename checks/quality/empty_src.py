from .base_quality_check import BaseQualityCheck


class EmptySrcCheck(BaseQualityCheck):

    def run(self, ctx, doc, results):

        for img in doc.images:

            src = img.attrib.get("src", "").strip()

            if src == "":

                results.append(

                    self.error(

                        "Empty src attribute",

                        doc.path

                    )

                )