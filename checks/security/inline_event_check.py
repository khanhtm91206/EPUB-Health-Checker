from .base_security_check import BaseSecurityCheck


class InlineEventCheck(BaseSecurityCheck):

    EVENTS = [

        "onclick",
        "ondblclick",
        "onmousedown",
        "onmouseup",
        "onmousemove",
        "onmouseover",
        "onmouseout",

        "onkeydown",
        "onkeypress",
        "onkeyup",

        "onload",
        "onunload",
        "onerror",
        "onfocus",
        "onblur",
        "onchange",
        "onsubmit",
        "onreset",
        "oninput",

    ]

    def run(self, ctx, doc, results):

        for node in doc.root.iter():

            for event in self.EVENTS:

                if event in node.attrib:

                    results.append(

                        self.error(

                            f'Inline event "{event}" detected',

                            doc.path

                        )

                    )