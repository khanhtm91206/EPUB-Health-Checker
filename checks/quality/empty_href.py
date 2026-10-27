from .base_quality_check import BaseQualityCheck


class EmptyHrefCheck(BaseQualityCheck):

    def run(self, ctx, doc, results):

        for link in doc.links:

            href = link.attrib.get("href", "").strip()

            if href == "":

                results.append(

                    self.warning(

                        "Empty href attribute",

                        doc.path

                    )

                )