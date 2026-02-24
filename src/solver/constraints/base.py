from abc import ABC, abstractmethod


class Constraint(ABC):
    def __init__(self, world, var_factory, T_MAX):
        self.world = world
        self.var = var_factory
        self.T_MAX = T_MAX

    @abstractmethod
    def generate(self):
        """Yield CNF clauses"""
        yield []
