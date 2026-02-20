import argparse
from pathlib import Path

from generators import GENERATOR_REGISTRY


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Level generation CLI")

    parser.add_argument(
        "-n", "--number", type=int, default=1, help="Number of levels to generate"
    )

    parser.add_argument(
        "--display", action="store_true", help="Display generated levels"
    )

    parser.add_argument("--save", type=Path, help="Folder to save generated levels")

    # Subparsers for generators
    subparsers = parser.add_subparsers(
        dest="generator", required=True, help="Generator to use"
    )

    # Let each generator register its own arguments
    for name, generator_cls in GENERATOR_REGISTRY.items():
        subparser = subparsers.add_parser(name, help=generator_cls.__doc__)
        generator_cls.add_arguments(subparser)

    return parser
