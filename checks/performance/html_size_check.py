from .base_performance_check import BasePerformanceCheck


class HTMLSizeCheck(BasePerformanceCheck):

    LIMIT = 500 * 1024      # 500 KB

    def run(self, ctx, results):

        for item in ctx.html_files:

            size = len(ctx.read_bytes(item["path"]))

            if size > self.LIMIT:

                results.append(

                    self.warning(

                        f"Large HTML ({size:,} bytes)",

                        item["path"]

                    )

                )