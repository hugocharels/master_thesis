import pytest

from benchmark.plots import _sort_level_keys as plot_sort_level_keys
from benchmark.report import _sort_level_keys as report_sort_level_keys
from benchmark.runner import run_benchmark
from generators.random_solvable_generator import RandomSolvableGenerator


@pytest.mark.parametrize(
    "kwargs,match",
    [
        (
            {"size": (3, 3), "agents": 2, "lasers": -1},
            "lasers must be >= 0",
        ),
        (
            {"size": (1, 1), "agents": 1, "lasers": 0, "num_walls": 0},
            "requires 2 unique cells",
        ),
        (
            {"size": (3, 3), "agents": 2, "max_attempts": 0},
            "max_attempts must be >= 1",
        ),
        (
            {"size": (0, 3), "agents": 1},
            "grid dimensions must be >= 1",
        ),
    ],
)
def test_random_solvable_generator_validates_invalid_inputs(kwargs, match):
    with pytest.raises(ValueError, match=match):
        RandomSolvableGenerator(**kwargs)


def test_sort_level_keys_orders_numeric_values_numerically():
    keys = [10, "custom", 2, 1]
    expected = [1, 2, 10, "custom"]

    assert report_sort_level_keys(keys) == expected
    assert plot_sort_level_keys(keys) == expected


def test_run_benchmark_rejects_non_positive_num_runs():
    with pytest.raises(ValueError, match="num_runs must be >= 1"):
        run_benchmark(num_runs=0, levels=[])
