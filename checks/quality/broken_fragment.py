from .base_quality_check import BaseQualityCheck


class BrokenFragmentCheck(BaseQualityCheck):

    def run(self, ctx, doc, results):

        ids = set()

        for node in doc.root.iter():

            value = node.attrib.get("id")

            if value:

                ids.add(value)

        for link in doc.links:

            href = link.attrib.get("href", "").strip()

            if not href.startswith("#"):

                continue

            fragment = href[1:]

            if fragment not in ids:

                results.append(

                    self.error(

                        f'Broken fragment "#{fragment}"',

                        doc.path

                    )

                )