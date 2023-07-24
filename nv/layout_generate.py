import platform
import os
import json
import re
from pathlib import Path

import sublime
import sublime_plugin

import NeoVintageous.dep.json5kit as json5kit # noqa: F401,F403
from NeoVintageous.dep.json5kit     	import Json5Node, Json5Array, Json5String, Json5Object # noqa: F401,F403
from NeoVintageous.nv.layout_convert	import lyt, LayoutConverter
from NeoVintageous.plugin import PACKAGE_NAME

__all__ = [
  'NvUserKeymap'
]

def isJstr(key, strVal) -> bool:
  return True if (type(key.value) == Json5String and (key.value.value) == strVal) else False
def isJStrInArr(val, key, strVal) -> bool:
  return True if (isinstance(val, Json5Array) and isJstr(key, strVal)) else False
def convertKeymapLayout(keymap, lyt_from, lyt_to):
  lyt_converter	= LayoutConverter()
  isAlias      	= lyt_converter.isAlias
  keymap_tree = json5kit.parse(keymap)

  reSp = re.compile(r'\s')
  reSingleKey = re.compile(r"""
    (?P<pre>    ^[\s]*)   #
    (?P<keycap> [^\s])    # ←
    (?P<pos>     [\s]*$)  #
    """, re.X)
  reLastKey = re.compile(r"""
    (?P<pre>    ^.*\+[\s]*) # up to and including the last +
    (?P<keycap> [^\s])      # ←
    (?P<pos>    [\s]*$)     #
    """, re.X)
  reLastKeyVim = re.compile(r"""
    (?P<pre>    ^[\s]*<.*-[\s]*)	# <opening and up to and including the last +
    (?P<keycap> [^\s])          	# ←
    (?P<pos>    [\s]*>[\s]*$)   	# closing>
    """, re.X)


  class keyComboTransformer(json5kit.Json5Transformer):
    def visit_String(self, node):
      key_combo_raw = node.value  # 'ctrl + a ' or '<M-q>' for target NV keys
      if   (reM := re.match(reSingleKey, key_combo_raw)):
        if (keycap := reM.group('keycap')):
          keycap_new   	= (lyt_converter.convert(keycap, lyt_from, lyt_to)).replace('\\','\\\\')
          key_combo_new	= re.sub(reSingleKey, fr"\g<pre>{keycap_new}\g<pos>",key_combo_raw)
          node = node.replace(json.dumps(key_combo_new, ensure_ascii=False))
      elif (reM := re.match(reLastKey  , key_combo_raw)):
        if (keycap := reM.group('keycap')):
          keycap_new   	= (lyt_converter.convert(keycap, lyt_from, lyt_to)).replace('\\','\\\\')
          key_combo_new	= re.sub(reLastKey  , fr"\g<pre>{keycap_new}\g<pos>",key_combo_raw)
          node = node.replace(json.dumps(key_combo_new, ensure_ascii=False))
      elif (reM := re.match(reLastKeyVim  , key_combo_raw)):
        if (keycap := reM.group('keycap')):
          keycap_new   	= (lyt_converter.convert(keycap, lyt_from, lyt_to)).replace('\\','\\\\')
          key_combo_new	= re.sub(reLastKeyVim,fr"\g<pre>{keycap_new}\g<pos>",key_combo_raw)
          node = node.replace(json.dumps(key_combo_new, ensure_ascii=False))
      return node

  class DictTransformer(json5kit.Json5Transformer):
    def __init__(self):
      self.objVal2Key 	= {}
      self.objectFound	= False

    def visit_Object(self, node):
      if self.objectFound: # don't parse anything past the first object
        return node
      for key, val in zip(node.keys, node.values):
        if isJStrInArr(val, key, "keys"):
          self.objVal2Key[           val] = key
        if isAlias: # also convert args:{key:"q"}
          if isJstr(           key, "args"):
            if type(      val) == Json5Object:
              for key, val in zip(val.keys, val.values):
                if isJstr(key,"key"):
                  if type(val) == Json5String:
                    self.objVal2Key[val] = key # store args→key:val identities to match later recursion
      super().generic_visit(node)
      return node

    def generic_visit(self, node):
      super().generic_visit(node)
      if self.objVal2Key.get(node):
        node = keyComboTransformer().visit(node)
      return node

  DictTransformer().visit(keymap_tree)

  return keymap_tree.to_source()

class NvUserKeymap(sublime_plugin.ApplicationCommand):
  def __init__(self):
    self.nv_keymap	= "Default.sublime-keymap"
    self.dest     	= "$packages/NeoVintageous_UserKeymap/Default.sublime-keymap" # ($platform)
    self.cmd      	= "NeoVintageous: Generate non-QWERTY key bindings"

  def run(self, **kwargs):
    nv_keymap_path	= f"Packages/{PACKAGE_NAME}/{self.nv_keymap}"
    dest          	= expand(kwargs.get('file', self.dest))
    try:
      nv_keymap_raw = sublime.load_resource(nv_keymap_path) # works, string
    except FileNotFoundError as e:
      sublime.error_message(f"NeoVintageous:\nTried and failed to load\n{nv_keymap_path}")
      return
    try:
      nv_keymap = sublime.decode_value(nv_keymap_raw)
    except ValueError as e:
      sublime.error_message(f"Tried and failed to decode {nv_keymap_path}")
      return
    nv_keymap_user = convertKeymapLayout(nv_keymap_raw, lyt.qwerty, lyt.user)

    if not (parent := Path(dest).parent).exists():
      try:
        os.mkdir(parent)
        print(f"NeoVintageous: created folder ‘{parent}’ to store custom user keymap")
      except FileNotFoundError as e:
        sublime.error_message(f"NeoVintageous: need to create user keymap at ‘{dest}’, but its grand-parent folder doesn't exist:\n‘{e}’")
        return
      except FileExistsError as e:
        pass
    try:
      with open(dest, 'w') as file:
        print(f"// Autogenerated via '{self.cmd}' command from '{nv_keymap_path}', changes will be overwritten", file=file)
        print(nv_keymap_user, file=file)
        sublime.message_dialog(f"NeoVintageous:\nKey bindings updated at '{dest}'")
    except FileNotFoundError as e:
      sublime.error_message(f"NeoVintageous:\nTried and failed to save generated keymap to\n{dest}")
      return

def expand(string):
  return sublime.expand_variables(string, sublime.active_window().extract_variables())
