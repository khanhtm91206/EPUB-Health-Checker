from .base_security_check import BaseSecurityCheck


class EmbedCheck(BaseSecurityCheck):

    def run(self, ctx, doc, results):

        for embed in doc.embeds:

            results.append(

                self.error(

                    "<embed> element detected",

                    doc.path

                )

            )