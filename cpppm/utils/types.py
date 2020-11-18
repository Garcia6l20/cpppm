def fq_type_name(obj):
    return f'{obj.__class__.__module__}.{obj.__class__.__qualname__}'


def check_type(obj, accept_types):
    if isinstance(accept_types, type):
        return type(obj) == accept_types
    elif isinstance(accept_types, str):
        return fq_type_name(obj) == accept_types
    else:
        for accept_type in accept_types:
            if check_type(obj, accept_type):
                return True
    return False


def type_dir(klass):
    """like dir() but returns accumulated dictionary over base classes

    Useful to get object elements without invoking them (eg.: for property type resolution).
    """
    content = dict()
    ns = getattr(klass, '__dict__', None)
    if ns is not None:
        content.update(klass.__dict__)
    bases = getattr(klass, '__bases__', None)
    if bases is not None:
        # Note that since we are only interested in the keys, the order
        # we merge classes is unimportant
        for base in bases:
            content.update(type_dir(base))
    return content
