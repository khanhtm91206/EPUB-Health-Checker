class LinkResolver:

    @staticmethod

    def resolve(

        ctx,

        current,

        target

    ):

        fragment = ""

        if "#" in target:

            target, fragment = target.split("#", 1)

        if target == "":

            full = current

        else:

            full = ctx.resolve_path(

                current,

                target

            )

        return full, fragment