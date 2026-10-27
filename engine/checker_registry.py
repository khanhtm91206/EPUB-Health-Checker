"""
engine/checker_registry.py

Registry for all available EPUB checkers.

Responsibilities
----------------
- Register checker classes.
- Enable/disable checkers.
- Return checker instances.
- Support GUI, CLI and batch runner.

Author
------
EPUB Health Checker
"""

from __future__ import annotations

from typing import Dict, List, Type

from checks.base_checker import BaseChecker


class CheckerRegistry:
    """
    Stores all available checker classes.

    Example
    -------
    registry = CheckerRegistry()

    registry.register(HTMLChecker)
    registry.register(CSSChecker)

    checkers = registry.create_selected(
        ["HTML", "CSS"]
    )
    """

    def __init__(self) -> None:
        self._checkers: Dict[str, Type[BaseChecker]] = {}

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #

    def register(self, checker_class: Type[BaseChecker]) -> None:
        """
        Register a checker class.

        Parameters
        ----------
        checker_class
            Checker class derived from BaseChecker.
        """

        checker = checker_class()

        name = checker.name

        if name in self._checkers:
            raise ValueError(
                f'Checker "{name}" has already been registered.'
            )

        self._checkers[name] = checker_class

    # ------------------------------------------------------------------ #
    # Query
    # ------------------------------------------------------------------ #

    def names(self) -> List[str]:
        """
        Return all checker names.
        """

        return sorted(self._checkers.keys())

    def exists(self, name: str) -> bool:
        """
        Check whether a checker exists.
        """

        return name in self._checkers

    def count(self) -> int:
        """
        Number of registered checkers.
        """

        return len(self._checkers)

    # ------------------------------------------------------------------ #
    # Factory
    # ------------------------------------------------------------------ #

    def create(self, name: str) -> BaseChecker:
        """
        Create one checker instance.
        """

        if name not in self._checkers:
            raise KeyError(
                f'Unknown checker "{name}".'
            )

        return self._checkers[name]()

    def create_selected(
        self,
        names: List[str]
    ) -> List[BaseChecker]:
        """
        Create checker instances from a list of names.
        """

        result: List[BaseChecker] = []

        for name in names:
            result.append(self.create(name))

        return result

    def create_all(self) -> List[BaseChecker]:
        """
        Create every registered checker.
        """

        return [
            checker()
            for checker in self._checkers.values()
        ]