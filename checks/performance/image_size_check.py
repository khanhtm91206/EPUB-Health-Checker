from .base_performance_check import BasePerformanceCheck


class ImageSizeCheck(BasePerformanceCheck):

    LIMIT = 2 * 1024 * 1024

    def run(self, ctx, results):

        for item in ctx.image_files:

            size = len(ctx.read_bytes(item["path"]))

            if size > self.LIMIT:

                results.append(

                    self.warning(

                        f"Large image ({size:,} bytes)",

                        item["path"]

                    )

                )