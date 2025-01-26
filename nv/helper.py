from collections     import OrderedDict
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

from threading import Timer
import time, threading
import typing as tp

class RepeatableTimer(object):  # Singleton
  _instance: Union[tp.Any,None] = None
  _lock = threading.Lock()
  def __new__(cls, t, cbfn, args=[], kwargs={}):
    if not cls._instance:
      with cls._lock:
        if not cls._instance:
          cls._instance = super().__new__(cls)
          cls._instance.__is_init = False
    return cls._instance
  def __init__(self, t, cbfn, args=[], kwargs={}) -> None:
    self.__is_init: bool
    self.t: Timer
    self._interval = t
    self._cbfn     = cbfn
    self._args     = args
    self._kwargs   = kwargs
    if self.__is_init:
      return
    self.__is_init = True
  def start(self):
    if hasattr(self, "t"): # print("re-starting the timer")
      self.t.cancel() # cancel the old timer and replace it with ↓
    self.t = Timer(self._interval, self._cbfn, self._args, self._kwargs)
    self.t.start()
  def cancel(self):
    if hasattr(self, "t"): # print("canceling the timer")
      self.t.cancel()

  @classmethod
  def cancel(cls):
    cls.stop()
  @classmethod
  def stop(cls):
    if not cls._instance:           # print("no instance exsits, nothing to cancel")
      return
    if hasattr(cls._instance, "t"): # print("cancelled the old timer")
      cls._instance.t.cancel()

import inspect
def fname(): # gets caller's function name
  return inspect.currentframe().f_back.f_code.co_name # w/o f_back gets this fn name

remove_prefix = lambda text, prefix: text[len(prefix):] if text.startswith(prefix) else text

from math import pow
def print_time(pre:str, t:OrderedDict):
  """Print an ordered dictionary of label=time, calculating durations and printing a table"""
  ns = pow(10,9) # nanosecond, which 'monotonic_ns' are measured in
  res = []
  for i,(k,v) in enumerate(t.items()):
    if i == 0:
      v_1 = v
      continue
    else:
      v_s = "{:.2f}".format((v - v_1) / ns)
      res.append(f"{k}\t{v_s}")
      v_1 = v
  res_s = '\n'.join(res)
  print(f"{pre}\n{res_s}") # ⏲

import hashlib
def file_hash(file_path, algo='sha256'):
  """Compute the hash of a file using the specified algorithm"""
  hash_func = hashlib.new(algo)
  with open(file_path,'rb') as file:
    while chunk := file.read(4096): # read the file in chunks of 4096 bytes
      hash_func.update(chunk)
  return hash_func.hexdigest()
