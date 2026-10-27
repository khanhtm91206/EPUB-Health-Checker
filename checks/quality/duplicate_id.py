from .base_quality_check import BaseQualityCheck


class DuplicateIDCheck(BaseQualityCheck):

    def run(self, ctx, doc, results):

        ids = {}

        for node in doc.root.iter():

            value = node.attrib.get("id")

            if not value:
                continue

            ids.setdefault(value, 0)

            ids[value] += 1

        for value, count in ids.items():

            if count > 1:

                results.append(

                    self.error(

                        f'Duplicate id "{value}" ({count} occurrences)',

                        doc.path

                    )

                )