from generators.random_solvable_generator import RandomSolvableGenerator
from generators.registry import register_generator
from solver import LLEAdapter
from solver.cooperation_profile_analyzer import CooperationProfileAnalyzer


@register_generator("random_cooperative")
class RandomCooperativeGenerator(RandomSolvableGenerator):
    """
    Inherits random solvable generation, then filters candidates to keep
    only worlds that require cooperation.
    """

    @staticmethod
    def add_arguments(parser):
        RandomSolvableGenerator.add_arguments(parser)
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
        parser.add_argument(
            "--debug-rejections",
            action="store_true",
            help="Print rejection reasons while sampling",
        )

    @classmethod
    def from_args(cls, args):
        obj = cls(
            size=tuple(args.size),
            agents=args.agents,
            lasers=args.lasers,
            num_walls=args.num_walls,
            t_max=args.t_max,
            t_min=args.t_min,
            max_attempts=args.max_attempts,
            seed=args.seed,
        )
        obj.debug_rejections = bool(args.debug_rejections)
        obj.profile = args.profile
        return obj

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.debug_rejections = False
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

        return True, f"profile={analysis.profile}, cooperative_and_solvable"

    def _failure_description(self) -> str:
        return "a cooperative solvable world"
