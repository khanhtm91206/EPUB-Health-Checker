from .base_security_check import BaseSecurityCheck


class ObjectCheck(BaseSecurityCheck):

    def run(self, ctx, doc, results):

        for obj in doc.objects:

            results.append(

                self.error(

                    "<object> element detected",

                    doc.path

                )

            )