import matplotlib.pyplot as plt

from cli import build_parser
from generators import GENERATOR_REGISTRY


def main():
    parser = build_parser()
    args = parser.parse_args()

    generator_cls = GENERATOR_REGISTRY[args.generator]
    generator = generator_cls.from_args(args)

    for i in range(args.number):
        world = generator.generate()

        if args.display or args.save:
            if args.display:
                plt.imshow(world.get_image())
                plt.axis("off")
                plt.show()

            if args.save:
                args.save.mkdir(parents=True, exist_ok=True)
                filepath = args.save / f"generated_level_{i}.txt"
                with open(filepath, "w") as f:
                    f.write(world.world_string)

                plt.imshow(world.get_image())
                plt.axis("off")
                plt.savefig(args.save / f"generated_level_{i}.png")


if __name__ == "__main__":
    main()
