from models import CheckResult, Severity


class BaseChecker:

    name = "Checker"

    def ok(self):

        return CheckResult(
            checker=self.name,
            success=True,
            severity=Severity.INFO
        )

    def warning(
        self,
        message,
        file="",
        location=""
    ):

        return CheckResult(
            checker=self.name,
            success=False,
            message=message,
            file=file,
            location=location,
            severity=Severity.WARNING
        )

    def error(
        self,
        message,
        file="",
        location=""
    ):

        return CheckResult(
            checker=self.name,
            success=False,
            message=message,
            file=file,
            location=location,
            severity=Severity.ERROR
        )

    def critical(
        self,
        message,
        file="",
        location=""
    ):

        return CheckResult(
            checker=self.name,
            success=False,
            message=message,
            file=file,
            location=location,
            severity=Severity.CRITICAL
        )