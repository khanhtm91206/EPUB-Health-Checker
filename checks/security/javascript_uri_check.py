from .base_security_check import BaseSecurityCheck


class JavaScriptURICheck(BaseSecurityCheck):

    def run(self, ctx, doc, results):

        ATTRIBUTES = [

            "href",

            "src",

            "action",

            "formaction",

        ]

        for node in doc.root.iter():

            for attr in ATTRIBUTES:

                value = node.attrib.get(attr)

                if not value:
                    continue

                value = value.strip().lower()

                if value.startswith("javascript:"):

                    results.append(

                        self.critical(

                            f'JavaScript URI detected ({attr})',

                            doc.path

                        )

                    )