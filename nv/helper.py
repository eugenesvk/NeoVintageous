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
            nprops = doc_node.getProps((...,...))
            for key,val in nprops:
                key_new = key_this + sep + key if key_this else key
                yield key_new, val
            nargs = doc_node.getArgs((...,...))
            for i, arg in enumerate(nargs):
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

import threading
class Singleton(type): # doesn't deadlock: if both Class_1 and Class_2 implement old singleton pattern, calling the constructor of Class_1 in Class_2 (or vice versa) would dead-lock since all the classes implemented through that meta-class share the same lock
    def __new__(mcs, name, bases, attrs): # Assume target class is created (=this method to be called) in the main thread
        cls = super(Singleton, mcs).__new__(mcs, name, bases, attrs)
        cls.__shared_instance__ = None
        cls.__shared_instance_lock__ = threading.Lock() # class implementing primitive lock objects. It allows the thread running our code to be the only thread accessing the code within the lock's context manager (cls._lock block), so long as it holds the lock
        return cls
    def __call__(cls, *args, **kwargs):
        if cls.__shared_instance__ is None: # check twice to avoid the edge case when 2 classes are created (alternative is to wrap it in a lock, but it's expensive):
            # 1. cls._instance is None in this thread
            # 2. another thread is about to call cls._instance = super(Singleton, cls).__new__(cls)
            with cls.__shared_instance_lock__: # another thread could have created the instance before we acquired the lock. So check that the instance is still nonexistent
                if not cls.__shared_instance__:
                    cls.__shared_instance__ = super(Singleton, cls).__call__(*args, **kwargs)
        return cls.__shared_instance__

class Symbol:
    def __init__(self, name=''):
        self.name = f"Symbol({name})"
    def __repr__(self):
        return self.name
