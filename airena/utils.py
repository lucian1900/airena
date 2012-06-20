from straight.plugin import load as load_plugins

def load(namespace, subclasses, class_name):
    classes = load_plugins(namespace, subclasses=subclasses)

    for cls in classes:
        if class_name == cls.__name__:
            return cls

