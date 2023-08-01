from collections.abc import MutableMapping

def _flatten_dict_gen(d, key_parent, sep):
    for key, val in d.items():
        key_new = key_parent + sep + key if key_parent else key
        if isinstance(val, MutableMapping):
            yield from flatten_dict(val, key_new, sep=sep).items()
        else:
            yield key_new, val

def flatten_dict(d:MutableMapping, key_parent:str = '', sep:str = '.'):
    return dict(_flatten_dict_gen(d, key_parent, sep))
