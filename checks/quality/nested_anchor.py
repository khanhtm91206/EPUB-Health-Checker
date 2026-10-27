from .base_quality_check import BaseQualityCheck


class NestedAnchorCheck(BaseQualityCheck):

    def run(self, ctx, doc, results):

        for anchor in doc.links:

            for child in anchor.iter():

                if child is anchor:
                    continue

                tag = child.tag.split("}")[-1].lower()

                if tag == "a":

                    results.append(

                        self.error(

                            "Nested <a> element",

                            doc.path

                        )

                    )

                    break