from generators.constrained_random_solvable_generator import ConstrainedRandomSolvableGenerator
from generators.registry import register_generator
from solver import LLEAdapter
from solver.cooperation_profile_analyzer import CooperationProfileAnalyzer


@register_generator("constrained_random_cooperative")
class ConstrainedRandomCooperativeGenerator(ConstrainedRandomSolvableGenerator):
    """
    Random cooperative generator with additional geometric constraints.
    Inherits all constrained geometry from ConstrainedRandomSolvableGenerator
    and additionally enforces that the level requires cooperation.
    """

    @staticmethod
    def add_arguments(parser):
        ConstrainedRandomSolvableGenerator.add_arguments(parser)
        parser.add_argument(
            "--profile",
            choices=[
                "cooperative",
                "asymmetric",
                "mutual",
                "chain",
                "distributed",
                "fully_coupled",
            ],
            default="cooperative",
            help="Target cooperation profile for accepted levels",
        )

    @classmethod
    def from_args(cls, args):
        obj = super().from_args(args)
        obj.profile = args.profile
        return obj

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile = "cooperative"

    def _analyze_profile(self, world):
        world.reset()
        adapted = LLEAdapter(world)
        return CooperationProfileAnalyzer(adapted, T_MAX=self.t_max).analyze()

    def _accept_world(self, world):
        accepted, reason = super()._accept_world(world)
        if not accepted:
            return accepted, reason

        analysis = self._analyze_profile(world)
        if not analysis.matches_profile(self.profile):
            return (
                False,
                f"profile={analysis.profile}, required={self.profile}",
            )

        return True, (
            f"profile={analysis.profile}, constrained_cooperative_and_solvable"
        )

    def _failure_description(self) -> str:
        return "a valid constrained cooperative world"
