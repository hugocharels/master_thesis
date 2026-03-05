from abc import ABC, abstractmethod


class Constraint(ABC):
    def __init__(self, world, var_factory, T_MAX):
        self.world = world
        self.var = var_factory
        self.T_MAX = T_MAX
        self.profiler = None

    def set_profiler(self, constraint_profiler):
        """Set the profiler for this constraint"""
        self.profiler = constraint_profiler

    @abstractmethod
    def generate(self):
        """Yield CNF clauses"""
        return []

    def _profile_method(self, method_name: str, method_func):
        """Helper to profile a method that generates clauses"""
        if self.profiler:
            with self.profiler.profile_method(method_name) as method_profiler:
                clauses = method_profiler.count_clauses(method_func())
                return clauses
        else:
            return list(method_func())
