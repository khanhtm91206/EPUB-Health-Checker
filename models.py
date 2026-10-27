from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Severity(Enum):

    INFO = "INFO"

    WARNING = "WARNING"

    ERROR = "ERROR"

    CRITICAL = "CRITICAL"


@dataclass
class CheckResult:

    checker: str

    success: bool

    message: str = ""

    file: str = ""

    location: str = ""

    severity: Severity = Severity.INFO



@dataclass(slots=True)
class ScanJob:
    """
    Represents one EPUB file discovered by the Scanner.

    This model contains only information related to the file itself.
    Progress information (current/total) belongs to the Runner, not
    the ScanJob.

    Attributes
    ----------
    path : Path
        Absolute path to the EPUB file.

    size : int
        File size in bytes.

    relative_path : str | None
        Path relative to the scanned root directory.
        This is useful for GUI display and reports.
    """

    path: Path
    size: int
    relative_path: str | None = None

    @property
    def filename(self) -> str:
        """Return filename including extension."""
        return self.path.name

    @property
    def stem(self) -> str:
        """Return filename without extension."""
        return self.path.stem

    @property
    def extension(self) -> str:
        """Return lowercase extension."""
        return self.path.suffix.lower()

    @property
    def parent(self) -> Path:
        """Return parent directory."""
        return self.path.parent

    @property
    def size_mb(self) -> float:
        """Return file size in megabytes."""
        return round(self.size / (1024 * 1024), 2)

    def as_dict(self) -> dict:
        """
        Convert ScanJob into a serializable dictionary.
        Useful for JSON reports.
        """
        return {
            "path": str(self.path),
            "relative_path": self.relative_path,
            "size": self.size,
            "size_mb": self.size_mb,
        }

    def __str__(self) -> str:
        return self.filename