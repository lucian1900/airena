from straight.plugin import load as load_plugins

def load_plugin(parent_class, namespace, fallback=False):
        classes = load_plugins(namespace, 
                               subclasses=parent_class, 
                               recurse=True)
        if len(classes):
            return classes[0]
        elif fallback and '.' in namespace:
            namespace = '.'.join(namespace.split('.')[:-1])
            classes = load_plugins(namespace,
                                   subclasses=parent_class,
                                   recurse=True)
            if len(classes):
                return classes[0]



