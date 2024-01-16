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
  'NvUserKeymap',
  'NvDefaultKeymapKdl',
]

def isJstr(key, strVal) -> bool:
  return True if (type(key.value) == Json5String and (key.value.value) == strVal) else False
def isJStrInArr(val, key, strVal) -> bool:
  return True if (isinstance(val, Json5Array) and isJstr(key, strVal)) else False
def convertKeymapLayout(keymap, lyt_from, lyt_to):
  lyt_converter	= LayoutConverter()
  isAlias      	= lyt_converter.isAlias
  keymap_tree  	= json5kit.parse(keymap)

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

from sublime_plugin import ApplicationCommand
class NvUserKeymap(ApplicationCommand):
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


# Command to generate the KDL version of the default keymap
import NeoVintageous.dep.kdl as kdl
def parse_kdl_doc(s):
  parseConfig = kdl.ParseConfig(
    nativeUntaggedValues    =False  #|True| produce native Py objects (str int float bool None) untagged values (no (foo)prefix), or kdl-Py objects (kdl.String kdl.Decimal...)
    ,nativeTaggedValues     =False  #|True| produce native Py objects for (tagged)values for predefined tags like i8..u64 f32 uuid url regex
  )
  printConfig = kdl.PrintConfig(
    indent              ="  "   #|"\t"|
    ,semicolons         =False  #|False|
    ,printNullArgs      =True   #|True| if False, skip over any "null"/None arguments. Corrupts docs that use "null" keyword intentionally, but can be useful if you'd prefer to use a None value as a signal that the argument has been removed
    ,printNullProps     =True   #|True| =printNullArgs, but applies to properties
    ,respectStringType  =True   #|True| output strings as the same type they were in the input, either raw (r#"foo"#) or normal ("foo") (only kdl-Py, not native ones (e.g, set nativeUntaggedValues=False))
    ,respectRadix       =True   #|True| ≈respectStringType, output numbers as the radix they were in the input, like 0x1b for hex numbers. False: print decimal numbers (kdl-Py)
    ,exponent           ="e"    #|e| character to use for the exponent part of decimal numbers, when printed with scientific notation, "e" or "E" (kdl-Py)
  )
  return kdl.Parser(parseConfig, printConfig).parse(s)

from NeoVintageous.nv.modes import mode_names, mode_names_rev
def mode_full_to_abbrev(mode_full:str,i=1):
  if not mode_full or len(mode_full) == 1:
    return mode_full
  return mode_names[mode_names_rev[mode_full]][i] # mode_names = {Mode.N:['Ⓝ','N','normal',NORMAL]

class NvDefaultKeymapKdl(ApplicationCommand):
  def __init__(self):
    self.keymap	= "NeoVintageous.keymap-default.kdl"
    self.dest  	= f"$packages/{PACKAGE_NAME}/{self.keymap}" # ($platform)
    self.cmd   	= "NeoVintageous: Dump default key bindings in KDL"

  def run(self, **kwargs):
    from NeoVintageous.nv.vi.keys import mappings # [mode_normal][<C-x>]=<ViDecrement>
    from NeoVintageous.nv.vi.keys import map_cmd2textcmd
    map_key2cmd_modes = {} # {<C-w>:{'ViDelete':[mode_insert,mode_normal]}}
    for     i, mode    in enumerate(mappings):  # generate map_key2cmd_modes
      mode_d = mappings[mode] # [<C-x>]=<ViDecrement>
      for j, keybind in enumerate(mode_d): # <C-x>
        cmd = mode_d[keybind] # <ViDecrement>
        T = type(cmd) # <class 'NeoVintageous.nv.vi.cmd_defs.ViDecrement'>
        cmd_txt = map_cmd2textcmd[T][0] # ViDecrement → Decrement
        if keybind in map_key2cmd_modes:
          if T in map_key2cmd_modes[keybind]:
            map_key2cmd_modes[    keybind][T] += [mode]  # add an extra mode to the same keybind
          else:
            map_key2cmd_modes[    keybind][T]  = [mode]  # add an extra command/mode
        else:
          map_key2cmd_modes[        keybind] =  {T:[mode]} # add a new keybind/command
        # [<C-x>] = { <...ViDecrement'>    : mode_insert...
        #             <...ViOpenNameSpace'>: mode_insert}

    keymap_kdl = parse_kdl_doc('')
    for     i, keybind    in enumerate(map_key2cmd_modes): # generate keymap_kdl from default keybinds
      keybind_d = map_key2cmd_modes[keybind]
      for j, cmd in enumerate(keybind_d):
        mode_l      = keybind_d[cmd] #  ['mode_insert','mode_normal']
        mode_sort   = ['mode_normal','mode_insert','mode_visual']
        mode_l_sort = []
        empty = '' # '_'
        for m in mode_sort: # move NIV modes first and sort them as NIV
          if m in mode_l:
            mode_l_sort += [m]
            mode_l.remove(m)
          else:
            mode_l_sort += [empty]
        mode_l_sort += mode_l # add the remaining modes
        mode_s = "".join(mode_full_to_abbrev(mode,0) for mode in mode_l_sort) # Ⓝⓘ
        cmd_txt = map_cmd2textcmd[cmd][0] # ViDeleteUpToCursor → DeleteUpToCursor
        node_key = kdl.Node(tag=mode_s, name=keybind, args=[cmd_txt])
        keymap_kdl.nodes.append(node_key)
        # print(f"  {i}{j} {keybind}={cmd} @ {mode_l}")

    dest = expand(kwargs.get('file',self.dest)) # expand Sublime variables
    if not (parent := Path(dest).parent).exists():
      try:
        os.mkdir(parent)
        print(f"{PACKAGE_NAME}: created folder ‘{parent}’ to store the default keymap as KDL")
      except FileNotFoundError as e:
        sublime.error_message(f"{PACKAGE_NAME}: need to create user keymap at ‘{dest}’, but its grand-parent folder doesn't exist:\n‘{e}’")
        return
      except FileExistsError as e:
        pass

    try:
      with open(dest, 'w') as file:
        print(f"//Autogenerated default ‘{PACKAGE_NAME}’ keymap in KDL via ‘{self.cmd}’ command, changes will be overwritten", file=file)
        print(f'//(mode)Key "CommandName"'      , file=file)
        print(f'//(i)"<C-w>" "DeleteUpToCursor"', file=file)
        print(keymap_kdl, file=file)
        sublime.message_dialog(f"{PACKAGE_NAME}:\nKeymap in KDL generated at '{dest}'")
    except FileNotFoundError as e:
      sublime.error_message(f"{PACKAGE_NAME}:\nTried and failed to save generated keymap to\n{dest}")
