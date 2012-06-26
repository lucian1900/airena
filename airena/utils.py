from straight.plugin import load as load_plugins

class ClassManager(object):
    def __init__(self, parent_class, namespaces, autoload=True):
        self.parent_class = parent_class
        self.classes = dict()

        if isinstance(namespaces, list):
            self.namespaces = namespaces
        else:
            self.namespaces = [namespaces]

        if autoload:
            self.load()


    def load(self):
        for namespace in self.namespaces:
            self.load_namespace(namespace)

    def load_namespace(self, namespace):
        classes = load_plugins(namespace, 
                               subclasses=self.parent_class, 
                               recurse=True)
        
        for cls in classes:
            self.classes[cls.__name__] = cls


