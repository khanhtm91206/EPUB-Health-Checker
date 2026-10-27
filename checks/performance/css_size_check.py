from .base_performance_check import BasePerformanceCheck


class CSSSizeCheck(BasePerformanceCheck):

    LIMIT = 200 * 1024

    def run(self, ctx, results):

        for item in ctx.css_files:

            size = len(ctx.read_bytes(item["path"]))

            if size > self.LIMIT:

                results.append(

                    self.warning(

                        f"Large CSS ({size:,} bytes)",

                        item["path"]

                    )

                )