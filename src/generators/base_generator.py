from abc import ABC, abstractmethod

from lle import World


class BaseGenerator(ABC):
    @staticmethod
    @abstractmethod
    def add_arguments(parser):
        pass

    @classmethod
    @abstractmethod
    def from_args(cls, args) -> "BaseGenerator":
        pass

    @abstractmethod
    def generate(self) -> World:
        """Generate and return a fully constructed lle.World."""
        pass
