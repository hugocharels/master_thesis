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
        image = world.get_image()

        if args.display or args.save:
            if args.display:
                fig, ax = plt.subplots()
                ax.imshow(image)
                ax.axis("off")
                plt.show()
                plt.close(fig)

            if args.save:
                args.save.mkdir(parents=True, exist_ok=True)
                filepath = args.save / f"generated_level_{i}.txt"
                with filepath.open("w", encoding="utf-8") as f:
                    f.write(world.world_string)

                plt.imsave(args.save / f"generated_level_{i}.png", image)


if __name__ == "__main__":
    main()
