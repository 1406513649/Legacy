
def is_stringlike(s):
    try:
        s + ' '
        return True
    except (ValueError, TypeError):
        return False


def is_numberlike(a):
    try:
        a + 2
        return True
    except (ValueError, TypeError):
        return False


def fmt_string_value(item, quoted=False, numfmt='g'):
    if item is None:
        return "''"
    if quoted:
        return '{0!r}'.format(item)
    if is_numberlike(item):
        return '{0:{1}}'.format(item, numfmt)
    return '{0}'.format(item)


def round_up_to_odd(f):
    import numpy as np
    f = int(np.ceil(f))
    return f + 1 if f % 2 == 0 else f
