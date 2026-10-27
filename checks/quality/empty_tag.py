from .base_quality_check import BaseQualityCheck


class EmptyTagCheck(BaseQualityCheck):

    TAGS = {

        "p",

        "div",

        "span",

    }

    def run(self, ctx, doc, results):

        for node in doc.root.iter():

            tag = node.tag.split("}")[-1].lower()

            if tag not in self.TAGS:
                continue

            text = (node.text or "").strip()

            children = list(node)

            if text:
                continue

            if children:
                continue

            results.append(

                self.warning(

                    f"Empty <{tag}> element",

                    doc.path

                )

            )