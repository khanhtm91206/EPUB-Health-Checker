import hashlib

from .base_performance_check import BasePerformanceCheck


class DuplicateCSSCheck(BasePerformanceCheck):

    def run(self, ctx, results):

        hashes = {}

        for item in ctx.css_files:

            data = ctx.read_bytes(item["path"])

            digest = hashlib.sha256(data).hexdigest()

            if digest in hashes:

                results.append(

                    self.warning(

                        f"Duplicate CSS ({hashes[digest]})",

                        item["path"]

                    )

                )

            else:

                hashes[digest] = item["path"]