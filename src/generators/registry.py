GENERATOR_REGISTRY = {}


def register_generator(name):
    def decorator(cls):
        GENERATOR_REGISTRY[name] = cls
        return cls

    return decorator
