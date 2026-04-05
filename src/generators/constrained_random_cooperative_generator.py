from generators.constrained_random_solvable_generator import ConstrainedRandomSolvableGenerator
from generators.registry import register_generator
from solver import LLEAdapter
from solver.cooperation_solver import CooperationSolver


@register_generator("constrained_random_cooperative")
class ConstrainedRandomCooperativeGenerator(ConstrainedRandomSolvableGenerator):
    """
    Random cooperative generator with additional geometric constraints.
    Inherits all constrained geometry from ConstrainedRandomSolvableGenerator
    and additionally enforces that the level requires cooperation.
    """

    def _is_cooperative(self, world) -> bool:
        world.reset()
        adapted = LLEAdapter(world)
        result = CooperationSolver(adapted, T_MAX=self.t_max).analyze()
        return result.cooperation_needed

    def generate(self):
        attempts = 0
        while attempts < self.max_attempts:
            attempts += 1
            layout = self._make_candidate_layout()

            valid, reason = self.validate_candidate(layout)
            if not valid:
                if self.debug_rejections:
                    print(f"[reject #{attempts}] {reason}")
                continue

            try:
                world = self._build_world_from_layout(layout)
            except Exception as e:
                if self.debug_rejections:
                    print(f"[reject #{attempts}] lle_build_error={type(e).__name__}")
                continue

            try:
                if not self._meets_difficulty_window(world):
                    if self.debug_rejections:
                        print(
                            f"[reject #{attempts}] outside_difficulty_window"
                            f"[t_min={self.t_min}, t_max={self.t_max}]"
                        )
                    continue

                if not self._is_cooperative(world):
                    if self.debug_rejections:
                        print(f"[reject #{attempts}] non_cooperative")
                    continue

                if self.debug_rejections:
                    print(f"[accept #{attempts}] constrained_cooperative_and_solvable")
                return world

            except Exception as e:
                if self.debug_rejections:
                    print(f"[reject #{attempts}] solver_error={type(e).__name__}")
                continue

        raise RuntimeError(
            "Could not find a valid constrained cooperative world in "
            f"{self.max_attempts} attempts for window "
            f"t_min={self.t_min}, t_max={self.t_max}."
        )
