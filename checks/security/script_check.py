from .base_security_check import BaseSecurityCheck


class ScriptCheck(BaseSecurityCheck):

    def run(self, ctx, doc, results):

        for script in doc.scripts:

            results.append(

                self.critical(

                    "<script> element detected",

                    doc.path

                )

            )