"""
core/exporters/json_reporter.py

JSON exporter for EPUB Health Checker.

This module is responsible only for converting scan results into JSON
and writing them to disk. It does not run checkers and does not print
anything to the console.

Supported objects
-----------------
- Report
- BookResult
- BatchResult
- CheckResult
- dictionaries / lists containing supported values
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class JSONReporter:
    """Export EPUB Health Checker results as JSON."""

    def __init__(
        self,
        indent: int = 2,
        ensure_ascii: bool = False,
    ) -> None:
        """
        Create a JSON reporter.

        Parameters
        ----------
        indent:
            JSON indentation level. Use None for compact JSON.

        ensure_ascii:
            Keep Unicode characters readable when False.
        """

        self.indent = indent
        self.ensure_ascii = ensure_ascii

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def serialize(self, value: Any) -> Any:
        """
        Convert a supported result object into JSON-compatible data.
        """

        return self._serialize(value)

    def to_json(self, value: Any) -> str:
        """
        Convert a result object into a JSON string.
        """

        data = self.serialize(value)

        return json.dumps(
            data,
            indent=self.indent,
            ensure_ascii=self.ensure_ascii,
        )

    def save(
        self,
        value: Any,
        output: str | Path,
    ) -> Path:
        """
        Save a result object as a JSON file.

        Parent directories are created automatically.

        Returns
        -------
        Path
            The resolved output path.
        """

        output_path = Path(output)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            self.to_json(value) + "\n",
            encoding="utf-8",
        )

        return output_path

    def export(
        self,
        value: Any,
        output: str | Path,
    ) -> Path:
        """Alias for :meth:`save`."""

        return self.save(
            value,
            output,
        )

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def save_report(
        self,
        report: Any,
        output: str | Path,
    ) -> Path:
        """Save a legacy Report object as JSON."""

        return self.save(
            report,
            output,
        )

    def save_book_result(
        self,
        book_result: Any,
        output: str | Path,
    ) -> Path:
        """Save one BookResult as JSON."""

        return self.save(
            book_result,
            output,
        )

    def save_batch_result(
        self,
        batch_result: Any,
        output: str | Path,
    ) -> Path:
        """Save one BatchResult as JSON."""

        return self.save(
            batch_result,
            output,
        )

    # ------------------------------------------------------------------
    # Internal serialization
    # ------------------------------------------------------------------

    def _serialize(
        self,
        value: Any,
    ) -> Any:
        """
        Recursively convert a value into JSON-compatible data.
        """

        if value is None:
            return None

        if isinstance(
            value,
            (str, int, float, bool),
        ):
            return value

        if isinstance(
            value,
            (datetime, date),
        ):
            return value.isoformat()

        if isinstance(
            value,
            Enum,
        ):
            return value.value

        if isinstance(
            value,
            Path,
        ):
            return str(value)

        if isinstance(
            value,
            dict,
        ):
            return {
                str(key): self._serialize(item)
                for key, item in value.items()
            }

        if isinstance(
            value,
            (list, tuple, set),
        ):
            return [
                self._serialize(item)
                for item in value
            ]

        # Prefer an object's own serialization method.
        for method_name in (
            "as_dict",
            "to_dict",
        ):
            method = getattr(
                value,
                method_name,
                None,
            )

            if callable(method):
                return self._serialize(
                    method()
                )

        if is_dataclass(value):
            return self._serialize(
                asdict(value)
            )

        if hasattr(value, "__dict__"):
            return {
                key: self._serialize(item)
                for key, item in vars(value).items()
                if not key.startswith("_")
            }

        raise TypeError(
            f"Object of type "
            f"{type(value).__name__} "
            "is not JSON serializable."
        )


# ----------------------------------------------------------------------
# Convenience functions
# ----------------------------------------------------------------------

def to_json(
    value: Any,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> str:
    """
    Convert a result object to JSON without creating a reporter.
    """

    return JSONReporter(
        indent=indent,
        ensure_ascii=ensure_ascii,
    ).to_json(value)


def save_json(
    value: Any,
    output: str | Path,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> Path:
    """
    Save a result object to JSON without creating a reporter.
    """

    return JSONReporter(
        indent=indent,
        ensure_ascii=ensure_ascii,
    ).save(
        value,
        output,
    )