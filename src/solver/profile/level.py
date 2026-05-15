"""CooperationLevel enum and the top-level cooperation_level helper."""

from __future__ import annotations

from enum import StrEnum

from lle import World


class CooperationLevel(StrEnum):
    """
    Precise classification of an LLE world's cooperation requirement.

    Values are the lowercase strings used throughout the project (thesis,
    CLI choices, test fixtures). Inheriting from StrEnum keeps equality with
    plain strings so existing string-based call sites remain valid.

    Members fall into three groups:

    * ``UNSOLVABLE`` — the world cannot be solved at all.
    * ``INDEPENDENT`` — solvable without any agent ever shielding another.
    * ``COOPERATIVE`` and below — cooperation is required; the remaining
      members refine the *shape* of the dependency structure.
    """

    UNSOLVABLE = "unsolvable"
    INDEPENDENT = "independent"
    COOPERATIVE = "cooperative"
    ASYMMETRIC = "asymmetric"
    MUTUAL = "mutual"
    CHAIN = "chain"
    DISTRIBUTED = "distributed"
    FULLY_COUPLED = "fully_coupled"

    @classmethod
    def cooperative_subtypes(cls) -> tuple["CooperationLevel", ...]:
        """Return the levels that imply cooperation is required."""
        return (
            cls.COOPERATIVE,
            cls.ASYMMETRIC,
            cls.MUTUAL,
            cls.CHAIN,
            cls.DISTRIBUTED,
            cls.FULLY_COUPLED,
        )


def cooperation_level(
    world: World,
    T_MAX: int = 10,
    movement_method: str = "local",
) -> CooperationLevel:
    """Return the precise cooperation classification of ``world``."""
    from .analyzer import CooperationProfileAnalyzer

    return CooperationProfileAnalyzer(
        world,
        T_MAX=T_MAX,
        movement_method=movement_method,
    ).analyze().profile
