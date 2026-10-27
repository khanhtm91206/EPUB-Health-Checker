from models import CheckResult, Severity


class BaseHTMLCheck:

    checker = "Accessibility"

    # --------------------------------------------------

    def ok(self):

        return CheckResult(

            checker=self.checker,

            success=True,

            severity=Severity.INFO

        )

    # --------------------------------------------------

    def warning(

        self,

        message,

        file="",

        location=""

    ):

        return CheckResult(

            checker=self.checker,

            success=False,

            message=message,

            file=file,

            location=location,

            severity=Severity.WARNING

        )

    # --------------------------------------------------

    def error(

        self,

        message,

        file="",

        location=""

    ):

        return CheckResult(

            checker=self.checker,

            success=False,

            message=message,

            file=file,

            location=location,

            severity=Severity.ERROR

        )