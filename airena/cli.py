import os, sys, imp, argparse, logging

from airena.app import Application

class ArgumentError(Exception): pass
    

class SimconfAction(argparse.Action):
    def __call__(self, parser, namespace, filename, option_string=None):
        if not os.path.exists(filename):
            raise ArgumentError('The file `%s` does not exist.' % filename)

        dirname = os.path.dirname(filename)
        basename = os.path.basename(filename)
        modulename = basename.split('.')[0]

        sys.path.append(dirname)

        file, filename, description = imp.find_module(modulename)
        module = imp.load_module(modulename, file, filename, description)
        
        sys.path.remove(dirname)

def get_args():
    parser = argparse.ArgumentParser(
        description="A platform for experimenting with AI agents",)
    parser.add_argument('simconf', action=SimconfAction)
    try:
        return parser.parse_args(sys.argv[1:])
    except ArgumentError, e:
        print "airena: error: %s" % e.message

def main():
    args = get_args()
    if args is not None:
        app = Application(args)
    app.start()

if __name__ == '__main__':
    sys.exit(main())
