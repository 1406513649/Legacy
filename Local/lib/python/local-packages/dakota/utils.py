def is_stringlike(it):
    try:
        it + ' '
        return True
    except:
        return False

class Repository:
    def __init__(self):
        self._keys = [] 
        self._values = []

    def __contains__(self, item):
        i = self._index(item)
        if i is None:
            return False
        return True

    def __len__(self):
        return len(self._keys)

    def __iter__(self):
        return iter(self._values)

    def __getitem__(self, arg):
        i = self._index(arg)
        if i is None:
            raise IndexError(arg)

    def _index(self, arg):
        if arg in self._values:
            return self._values.index(arg)
        if not is_stringlike(arg):
            return None
        for (i, key) in self._keys:
            if arg.lower() == key:
                return i
        return None

    def append(self, item):
        self._values.append(item)
        for x in dir(item):
            if x.startswith('id_'):
                id_ = getattr(item, x).lower()
                self._keys.append(id_.lower())
                break
        else:
            raise TypeError('no id_')
