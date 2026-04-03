from generators.random_solvable_generator import RandomSolvableGenerator
from generators.registry import register_generator
from solver import LLEAdapter
from solver.cooperation_solver import CooperationSolver


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
        return obj

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.debug_rejections = False

    def _is_cooperative(self, world) -> bool:
        world.reset()
        adapted = LLEAdapter(world)
        result = CooperationSolver(adapted, T_MAX=self.t_max).analyze()
        return result.cooperation_needed

    def generate(self):
        for attempt in range(1, self.max_attempts + 1):
            layout = self._make_candidate_layout()

            valid, reason = self.validate_candidate(layout)
            if not valid:
                if self.debug_rejections:
                    print(f"[reject #{attempt}] invalid_layout={reason}")
                continue

            try:
                world = self._build_world_from_layout(layout)
            except Exception as e:
                if self.debug_rejections:
                    print(f"[reject #{attempt}] lle_build_error={type(e).__name__}")
                continue

            try:
                if not self._meets_difficulty_window(world):
                    if self.debug_rejections:
                        print(f"[reject #{attempt}] outside_difficulty_window")
                    continue

                if not self._is_cooperative(world):
                    if self.debug_rejections:
                        print(f"[reject #{attempt}] non_cooperative")
                    continue

                if self.debug_rejections:
                    print(f"[accept #{attempt}] cooperative_and_solvable")
                return world

            except Exception as e:
                if self.debug_rejections:
                    print(f"[reject #{attempt}] solver_error={type(e).__name__}")
                continue

        raise RuntimeError(
            "Could not find a cooperative solvable world in "
            f"{self.max_attempts} attempts for window "
            f"t_min={self.t_min}, t_max={self.t_max}."
        )
