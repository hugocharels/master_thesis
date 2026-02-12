import matplotlib.pyplot as plt
from cli import build_parser
from core.types import Agent, CellType, Direction, Entity, Laser
from core.world import World
from lle import LLE

from generators import GENERATOR_REGISTRY


def main():
    parser = build_parser()
    args = parser.parse_args()

    generator_cls = GENERATOR_REGISTRY[args.generator]
    generator = generator_cls.from_args(args)

    for i in range(args.number):
        level = generator.generate()

        if args.display or args.save:
            env = LLE.from_str(level.to_str()).build()

            if args.display:
                plt.imshow(env.get_image())
                plt.axis("off")
                plt.show()

            if args.save:
                args.save.mkdir(parents=True, exist_ok=True)
                filepath = args.save / f"level_{i}.txt"
                with open(filepath, "w") as f:
                    f.write(level.to_str())

                img_path = args.save / f"level_{i}.png"
                plt.imshow(env.get_image())
                plt.axis("off")
                plt.savefig(img_path)


if __name__ == "__main__":
    main()
