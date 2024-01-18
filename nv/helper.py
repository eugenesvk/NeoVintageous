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

from typing import Union
import NeoVintageous.dep.kdl as kdl
def _flatten_kdl_gen(kdl_dic, key_parent, sep, lvl, ignore):
    lvl += 1
    if isinstance(kdl_dic, dict):
        d = kdl_dic
        for key, val in d.items():
            if lvl in ignore and key in ignore[lvl]: # skip dict groups that are dupes of node names
                key_new = key_parent
            else:
                key_new = key_parent + sep + key if key_parent else key
            if   isinstance(val, dict):
                yield from flatten_kdl(val, key_new, sep=sep,lvl=lvl,ignore=ignore).items()
            elif isinstance(val, kdl.Node):
                yield from flatten_kdl(val, key_new, sep=sep,lvl=lvl,ignore=ignore).items()
            else:
                yield key_new, val
    else:
        doc_node = kdl_dic
        key = doc_node.name if isinstance(doc_node, kdl.Node) else ''
        for node_child in doc_node.nodes:
            key_new = key_parent + sep + key if key_parent else key
            yield from flatten_kdl(node_child, key_new, sep=sep,lvl=lvl,ignore=ignore).items()
        if isinstance(doc_node, kdl.Node):
            key_this = key_parent + sep + key if key_parent else key
            for key,val in doc_node.props.items():
                key_new = key_this + sep + key if key_this else key
                yield key_new, val
            for i, arg in enumerate(doc_node.args):
                # tag = arg.tag   if hasattr(arg,'tag'  ) else ''
                val = arg.value if hasattr(arg,'value') else arg
                if i == 0: # store only the 1st arg without any prefixes
                    key_new = key_this
                else:
                    key_new = key_this + str(i+1) # add a numeric prefix
                yield key_new, val
def flatten_kdl(kdl_dic:Union[kdl.Document,kdl.Node,dict], key_parent:str = '', sep:str = '.', lvl:int=0, ignore:dict={1:[],2:[]}):
    """convert KDL document or a dictionary of KDL nodes into a flat dictionary, ignoring 2nd+ argument, but retaining key=val properties"""
    return dict(_flatten_kdl_gen(kdl_dic, key_parent, sep, lvl, ignore))
