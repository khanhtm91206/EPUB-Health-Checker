from .base_security_check import BaseSecurityCheck


class FormCheck(BaseSecurityCheck):

    def run(self, ctx, doc, results):

        for form in doc.forms:

            results.append(

                self.warning(

                    "<form> element detected",

                    doc.path

                )

            )