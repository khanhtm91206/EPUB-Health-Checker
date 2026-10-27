from pathlib import Path
from models import CheckResult


def check(path: Path) -> CheckResult:

    try:

        with open(path, "rb") as f:

            if f.read(4) == b'PK\x03\x04':

                return CheckResult(
                    module="Header",
                    success=True
                )

            return CheckResult(
                module="Header",
                success=False,
                message="Invalid ZIP header"
            )

    except Exception as e:

        return CheckResult(
            module="Header",
            success=False,
            message=str(e)
        )