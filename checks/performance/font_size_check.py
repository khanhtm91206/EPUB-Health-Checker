from .base_performance_check import BasePerformanceCheck


class FontSizeCheck(BasePerformanceCheck):

    LIMIT = 1024 * 1024

    def run(self, ctx, results):

        for item in ctx.font_files:

            size = len(ctx.read_bytes(item["path"]))

            if size > self.LIMIT:

                results.append(

                    self.warning(

                        f"Large font ({size:,} bytes)",

                        item["path"]

                    )

                )