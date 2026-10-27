from models import CheckResult, Severity


class BaseQualityCheck:

    checker = "Quality"

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