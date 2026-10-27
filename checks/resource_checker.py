import hashlib

from checks.base_checker import BaseChecker


class ResourceChecker(BaseChecker):

    def read_resource(
        self,
        ctx,
        path,
        results
    ):

        try:

            return ctx.read_bytes(path)

        except Exception:

            results.append(
                self.error(
                    "Cannot read resource",
                    path
                )
            )

            return None

    def sha256(self, data):

        return hashlib.sha256(data).hexdigest()

    def check_duplicate(
        self,
        data,
        path,
        hashes,
        results
    ):

        digest = self.sha256(data)

        if digest in hashes:

            results.append(
                self.warning(
                    "Duplicate resource",
                    path
                )
            )

        hashes.add(digest)