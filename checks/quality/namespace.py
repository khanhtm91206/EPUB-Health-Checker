from .base_quality_check import BaseQualityCheck


class NamespaceCheck(BaseQualityCheck):

    XHTML = "http://www.w3.org/1999/xhtml"

    def run(self, ctx, doc, results):

        root = doc.root

        if not root.tag.startswith("{"):

            results.append(

                self.error(

                    "Missing XHTML namespace",

                    doc.path

                )

            )

            return

        namespace = root.tag.split("}")[0][1:]

        if namespace != self.XHTML:

            results.append(

                self.error(

                    "Invalid XHTML namespace",

                    doc.path

                )

            )