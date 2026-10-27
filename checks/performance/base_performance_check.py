from models import CheckResult, Severity


class BasePerformanceCheck:

    checker = "Performance"

    def warning(self, message, file="", location=""):

        return CheckResult(

            checker=self.checker,

            success=False,

            message=message,

            file=file,

            location=location,

            severity=Severity.WARNING

        )

    def info(self, message="", file=""):

        return CheckResult(

            checker=self.checker,

            success=True,

            message=message,

            file=file,

            severity=Severity.INFO

        )