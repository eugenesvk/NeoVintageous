import platform
import os
import json
import re
from pathlib import Path
from typing import Union

import sublime
import sublime_plugin

import NeoVintageous.dep.json5kit as json5kit # noqa: F401,F403
from NeoVintageous.dep.json5kit     	import Json5Node, Json5Array, Json5String, Json5Object # noqa: F401,F403
from NeoVintageous.nv.layout_convert	import lyt, LayoutConverter
from NeoVintageous.plugin import PACKAGE_NAME

__all__ = [
  'NvUserKeymap',
  'NvDefaultKeymapKdl',
  'NvOldCfgKeymapKdl',
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
        print(f"// Autogenerated via ‘{self.name}’ command from ‘{nv_keymap_path}’, changes will be overwritten", file=file)
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

from NeoVintageous.nv.modes import Mode as M, M_ANY, INSERT,INTERNAL_NORMAL,NORMAL,OPERATOR_PENDING,REPLACE,SELECT,UNKNOWN,VISUAL,VISUAL_BLOCK,VISUAL_LINE
from NeoVintageous.nv.modes import mode_names, mode_names_rev, MODE_NAMES_OLD, MODE_HELP
def mode_full_to_abbrev(mode_full:str,i=1):
  if not mode_full or len(mode_full) == 1:
    return mode_full
  return mode_names[mode_names_rev[mode_full]][i] # mode_names = {Mode.N:['Ⓝ','N','normal',NORMAL]

def mode_group_sort(modes:Union[list,M], filler:str='') -> list:
  """group individual modes (VV+VB+VL=V) and sort to move NIV first"""
  sort_order   = [[M.Map,M.N],[M.I],[M.V,M.X,M.VV]]
  m_enum = M(0)
  if   isinstance(modes, list):
    for m in modes: # convert to enum
      m_enum |= mode_names_rev.get(m,M(0))
  elif isinstance(modes, M):
    m_enum = modes
  else:
    print(f"Modes should be of type list or Mode, not ‘{type(modes)}’")
    return []

  mode_l_sort = []
  filler = '' # '_'
  for   mgroup in sort_order: # move grouped then NIV modes first, ordered
    isFill = True # if no single mode from a group matches, add a filler
    for m in mgroup:
      mode_sym = mode_names[m][0]
      if m in m_enum:
        mode_l_sort	+= [mode_sym]
        m_enum     	^= m    	# remove
        isFill     	 = False	# don't add filler since at least 1 from mode group matched
    if isFill:
      mode_l_sort += [filler]
  for m in M_ANY: # TODO: m_enum iteration fails in py3.8
    if m & m_enum:
      mode_sym = mode_names[m][0]
      mode_l_sort += [mode_sym] # add the remaining modes
  # print(f"from {modes} to {mode_l_sort}")
  return (mode_l_sort,m_enum)


class NvDefaultKeymapKdl(ApplicationCommand):
  def __init__(self):
    self.keymap	= "NeoVintageous.key-def.kdl"
    self.dest  	= f"$packages/{PACKAGE_NAME}/{self.keymap}" # ($platform)

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
        (mode_l_sort,m_enum) = mode_group_sort(mode_l)
        mode_s = "".join(mode_l_sort) # Ⓝⓘ
        cmd_txt = map_cmd2textcmd[cmd][0] # ViDeleteUpToCursor → DeleteUpToCursor
        node_key = kdl.Node(tag=mode_s, name=keybind, args=[cmd_txt])
        keymap_kdl.nodes.append(node_key)
        # print(f"  {i}{j} {keybind}={cmd} @ {mode_l}")

    dest = expand(kwargs.get('file',self.dest)) # expand Sublime variables
    if not (parent := Path(dest).parent).exists():
      try:
        os.mkdir(parent)
        print(f"{PACKAGE_NAME}: created folder ‘{parent}’ to store the generated keybinds as KDL")
      except FileNotFoundError as e:
        sublime.error_message(f"{PACKAGE_NAME}: need to create user keybinds at ‘{dest}’, but its grand-parent folder doesn't exist:\n‘{e}’")
        return
      except FileExistsError as e:
        pass
    try:
      with open(dest, 'w') as file:
        print(f"/*Autogenerated default ‘{PACKAGE_NAME}’ keybinds in KDL via ‘{self.name()}’ command, changes will be overwritten", file=file)
        print(f' (mode)Key "CommandName"   where mode is an abbreviated name or icon from:{MODE_HELP}*/', file=file)
        print(keymap_kdl, file=file)
        sublime.message_dialog(f"{PACKAGE_NAME}:\nKeybinds in KDL generated at '{dest}'")
      sublime.active_window().open_file(dest)
    except FileNotFoundError as e:
      sublime.error_message(f"{PACKAGE_NAME}:\nTried and failed to save generated keybinds to\n{dest}")


class NvOldCfgKeymapKdl(ApplicationCommand):
  def __init__(self):
    self.keymap	= "NeoVintageous.key-user.kdl"
    self.dest  	= f"$packages/{PACKAGE_NAME}/{self.keymap}" # ($platform)

  def run(self, **kwargs):
    from NeoVintageous.nv.vi.keys  import  mappings as kbDef # [mode][<C-x>]=cls<ViDecrement>
    from NeoVintageous.nv.mappings import _mappings as kbUsr # [m][w]    =f
    #                                                          [m][<C-J>]=:SwapLineDown<CR>
    # with filetype                                             = {'':cmd_all, 'go':cmd}
    from NeoVintageous.nv.vi.keys import map_cmd2textcmd, map_textcmd2cmd
    # map_textcmd2cmd[cmd] = cls(*args,**kwargs)
    # map_cmd2textcmd[cls internal command Name] = [textual,command,name(s)] from ↑ (preserves CaSe)

    key2cmd_ft_m = {} # {<C-w>:{'ViDelete':{'file':[mode_insert,mode_normal]}}}
    def add_one(mode:M, key, fileT, cmd): # add 1 combo to key2cmd_ft_m
      if   key in key2cmd_ft_m:
        if cmd in key2cmd_ft_m[key]:
          if fileT in key2cmd_ft_m[key][cmd]:
            key2cmd_ft_m[key] [cmd] [fileT] |= mode  # add an extra               mode
          else:
            key2cmd_ft_m[key] [cmd] [fileT]  = mode  # add a new             file/mode
        else:
          key2cmd_ft_m  [key] [cmd]={fileT:    mode} # add a new         cmd/file/mode
      else:
        key2cmd_ft_m    [key]={cmd :{fileT:    mode}} #add a new keybind/cmd/file/mode

    for   mode_s ,mode_d      in  kbUsr.items(): # generate key2cmd_ft_m
      mode:M = mode_names_rev[mode_s]
      for keybind,cmd_or_file in mode_d.items(): # <C-x>  <ViDecrement> or 'go':<ViDecrement>
        if isinstance(cmd_or_file  , str):
          fileT = ''
          cmd = cmd_or_file # <ViDecrement>
          add_one(  mode=mode, key=keybind, fileT=fileT, cmd=cmd)
        elif isinstance(cmd_or_file, dict):
          for fileT,cmd in cmd_or_file.items(): #'':cmd1 , 'go':cmd2
            add_one(mode=mode, key=keybind, fileT=fileT, cmd=cmd)
        else:
          print(f"error parsing keybind=‘{keybind}’ , cmd_or_file=‘{cmd_or_file}’")
    # print('key2cmd_ft_m', key2cmd_ft_m)

    keymap_kdl = parse_kdl_doc('')
    for     keybind,keybind_d in key2cmd_ft_m.items():  # generate keymap_kdl from User keybinds
      for   cmd_s  ,fileT_d   in    keybind_d.items():
        fileT_d_rev_comb = dict() # store a list of filetypes per unique mode combo to avoid 1 line per each file
        for fileT  ,modes     in      fileT_d.items(): # combine file types if modes are the same
          if modes in fileT_d_rev_comb:
            fileT_d_rev_comb[modes] += [fileT]
          else:
            fileT_d_rev_comb[modes]  = [fileT]

        for modes  ,fileT     in fileT_d_rev_comb.items():
          (mode_l_sort,m_enum) = mode_group_sort(modes)
          mode_s = "".join(mode_l_sort) # Ⓝⓘ
          cmd_txt = cmd_s
          props = {}
          fileT_noblank = [f for f in fileT if not f == ''] # ignore '' file types that mean any
          if fileT_noblank:
            props['file'] = " ".join(fileT_noblank)

          for  mode in M_ANY: # TODO: m_enum iteration fails in py3.8
            if mode & modes:
              mode_name = MODE_NAMES_OLD[mode]
              if mode_name not in kbDef: # empty modes or _ fillers
                continue
              elif (cmd_cls := kbDef[mode_name].get(cmd_s)): # b → <...ViMoveByWordsBackward>
                T = type(cmd_cls)
                cmd_txt = map_cmd2textcmd[T][0] # ViMoveByWordsBackward → MoveByWordsBackward
                props['def'] = cmd_s # save ‘b’ default vim key to props ‘def’
                break
          if '"' in cmd_txt: # create a raw string to avoid escaping quotes
            arg = kdl.RawString(tag=None,value=cmd_txt)
          else:
            arg = kdl.   String(tag=None,value=cmd_txt)
          node_key = kdl.Node(tag=mode_s, name=keybind, args=[arg], props=props)
          # (Ⓝ)d "MoveByWordsBackward" def="b"

          keymap_kdl.nodes.append(node_key)

    dest = expand(kwargs.get('file',self.dest)) # expand Sublime variables
    if not (parent := Path(dest).parent).exists():
      try:
        os.mkdir(parent)
        print(f"{PACKAGE_NAME}: created folder ‘{parent}’ to store the generated keybinds as KDL")
      except FileNotFoundError as e:
        sublime.error_message(f"{PACKAGE_NAME}: need to create user keybinds at ‘{dest}’, but its grand-parent folder doesn't exist:\n‘{e}’")
        return
      except FileExistsError as e:
        pass
    try:
      with open(dest, 'w') as file:
        print(f"/*Autogenerated user ‘{PACKAGE_NAME}’ keybinds in KDL (from .neovintageousrc) via ‘{self.name()}’ command, changes will be overwritten", file=file)
        print(f' (mode)Key "CommandName"   where mode is an abbreviated name or icon from:{MODE_HELP}*/', file=file)
        print(keymap_kdl, file=file)
        sublime.message_dialog(f"{PACKAGE_NAME}:\nKeybinds in KDL generated at '{dest}'")
      sublime.active_window().open_file(dest)
    except FileNotFoundError as e:
      sublime.error_message(f"{PACKAGE_NAME}:\nTried and failed to save generated keybinds to\n{dest}")
