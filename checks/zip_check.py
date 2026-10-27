import zipfile

from models import CheckResult


def check(path):

    try:

        with zipfile.ZipFile(path) as z:

            bad = z.testzip()

            if bad is None:

                return CheckResult(
                    "ZIP",
                    True
                )

            return CheckResult(
                "ZIP",
                False,
                f"CRC failed : {bad}"
            )

    except zipfile.BadZipFile:

        return CheckResult(
            "ZIP",
            False,
            "Bad ZIP file"
        )

    except Exception as e:

        return CheckResult(
            "ZIP",
            False,
            str(e)
        )