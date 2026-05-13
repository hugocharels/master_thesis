"""Smoke test: every symbol in __all__ can be imported."""

import importlib


def test_solver_public_api():
    mod = importlib.import_module("solver")
    for name in mod.__all__:
        assert hasattr(mod, name), f"solver.__all__ lists {name!r} but it is missing"


def test_generators_public_api():
    mod = importlib.import_module("generators")
    for name in mod.__all__:
        assert hasattr(mod, name), f"generators.__all__ lists {name!r} but it is missing"
