from checks.base_checker import BaseChecker


class XMLChecker(BaseChecker):

    def load_xml(

        self,

        ctx,

        path,

        results

    ):

        try:

            return ctx.read_xml(path)

        except Exception as e:

            results.append(

                self.error(

                    f"Cannot parse XML : {e}",

                    path

                )

            )

            return None