from models import CheckResult, Severity


class BaseSecurityCheck:

    checker = "Security"

    def warning(self, message, file="", location=""):

        return CheckResult(

            checker=self.checker,

            success=False,

            message=message,

            file=file,

            location=location,

            severity=Severity.WARNING

        )

    def error(self, message, file="", location=""):

        return CheckResult(

            checker=self.checker,

            success=False,

            message=message,

            file=file,

            location=location,

            severity=Severity.ERROR

        )

    def critical(self, message, file="", location=""):

        return CheckResult(

            checker=self.checker,

            success=False,

            message=message,

            file=file,

            location=location,

            severity=Severity.CRITICAL

        )