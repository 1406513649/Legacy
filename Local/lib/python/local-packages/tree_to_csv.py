import os
from os.path import basename, isdir, isfile, join, sep

d = os.getcwd()
skip = [join(d, f) for f in ('.ipynb_checkpoint', 'Python-2.7', 'Data')]

def tree_to_list(path):
    tree = [path]
    for item in os.listdir(path):
        itempath = join(path, item)
        if isdir(itempath):
            tree.extend(tree_to_list(itempath))
        elif isfile(itempath):
            tree.append(itempath)
    return tree

def tree_to_csv(path, filename):
    tree = tree_to_list(path)
    tree.sort()
    tree = '\n'.join(fix(x) for x in tree if keep(x))
    with open(filename, 'w') as fh:
        fh.write(tree)

def fix(filename):
    return filename.replace(d, '').replace(sep, ',').lstrip(',')

def keep(filename):
    for item in skip:
        if item in filename:
            return False
    if basename(filename).startswith('.'):
        return False
    return True

tree_to_csv(d, 'tmp.csv')
