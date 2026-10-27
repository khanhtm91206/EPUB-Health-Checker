from .base_security_check import BaseSecurityCheck


class IFrameCheck(BaseSecurityCheck):

    def run(self, ctx, doc, results):

        for iframe in doc.iframes:

            results.append(

                self.error(

                    "<iframe> element detected",

                    doc.path

                )

            )