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
  'NvOldCfgKdl',
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
      if key_combo_raw == '<character>':
        node = node.replace(json.dumps('', ensure_ascii=False))
      elif (reM := re.match(reSingleKey, key_combo_raw)):
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
from NeoVintageous.nv.cfg_parse import parse_kdl_doc

from NeoVintageous.nv.modes import Mode as M, M_ANY, INSERT,INTERNAL_NORMAL,NORMAL,OPERATOR_PENDING,REPLACE,SELECT,UNKNOWN,VISUAL,VISUAL_BLOCK,VISUAL_LINE
from NeoVintageous.nv.modes import mode_names, mode_names_rev, mode_full_to_abbrev, mode_group_sort, MODE_NAMES_OLD, MODE_HELP

class NvDefaultKeymapKdl(ApplicationCommand):
  def __init__(self):
    self.keymap	= "NeoVintageous.key-def.kdl"
    self.dest  	= f"$packages/{PACKAGE_NAME}/{self.keymap}" # ($platform)

  def run(self, **kwargs):
    # Regular keybinds
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
          map_key2cmd_modes  [    keybind]={T  : [mode]} # add a new keybind/command
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


    # Plugins' keybinds
    from NeoVintageous.nv.plugin import mappings # [mode_normal][<C-n>]=<MultipleCursorsStart>
    from NeoVintageous.nv.plugin import map_cmd2textcmd # '...MultipleCursorsStart' = ['MultipleCursorsStart']
    map_key2cmd_modes = {} # {<C-n>:{'MultipleCursorsStart':[mode_normal,mode_visual]}}
    for     i, mode    in enumerate(mappings):  # generate map_key2cmd_modes
      mode_d = mappings[mode] # [<C-n>]=<MultipleCursorsStart>
      for j, keybind in enumerate(mode_d): # <C-n>
        cmd = mode_d[keybind] # <MultipleCursorsStart>
        T = type(cmd) # <class 'NeoVintageous.nv.plugin_multiple_cursors.MultipleCursorsStart'>
        if not T in map_cmd2textcmd:
          _log.warn("function command ‘%s’ is missing from nv.plugin's map_cmd2textcmd, likely it has no ‘register_text’ annotation",T)
          continue
        cmd_txt = map_cmd2textcmd[T][0] # MultipleCursorsStart → MultipleCursorsStart
        if keybind in map_key2cmd_modes:
          if T in map_key2cmd_modes[keybind]:
            map_key2cmd_modes[    keybind][T] += [mode]  # add an extra mode to the same keybind
          else:
            map_key2cmd_modes[    keybind][T]  = [mode]  # add an extra command/mode
        else:
          map_key2cmd_modes  [    keybind]={T  : [mode]} # add a new keybind/command
        # [<C-n>] = { <...MultipleCursorsStart'>: mode_normal...}

    keymap_plugin_kdl = parse_kdl_doc('')
    for     i, keybind    in enumerate(map_key2cmd_modes): # generate keymap_plugin_kdl from default plugin keybinds
      keybind_d = map_key2cmd_modes[keybind]
      for j, cmd in enumerate(keybind_d):
        mode_l      = keybind_d[cmd] #  ['mode_insert','mode_normal']
        (mode_l_sort,m_enum) = mode_group_sort(mode_l)
        mode_s = "".join(mode_l_sort) # Ⓝⓘ
        cmd_txt = map_cmd2textcmd[cmd][0] # MultipleCursorsStart → MultipleCursorsStart
        node_key = kdl.Node(tag=mode_s, name=keybind, args=[cmd_txt])
        keymap_plugin_kdl.nodes.append(node_key)
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
        print(f'// Plugins', file=file)
        print(keymap_plugin_kdl, file=file)
        sublime.message_dialog(f"{PACKAGE_NAME}:\nKeybinds in KDL generated at '{dest}'")
      sublime.active_window().open_file(dest)
    except FileNotFoundError as e:
      sublime.error_message(f"{PACKAGE_NAME}:\nTried and failed to save generated keybinds to\n{dest}")

class NvOldCfgKeymapKdl(ApplicationCommand):
  def __init__(self):
    self.keymap	= "NeoVintageous.key-user.kdl"
    self.dest  	= f"$packages/{PACKAGE_NAME}/{self.keymap}" # ($platform)

  def run(self, **kwargs):
    from NeoVintageous.nv.mappings import key2textcmd
    from NeoVintageous.nv.mappings import _mappings as kbUsr  # [m][w]    =f
    #                                                           [m][<C-J>]=:SwapLineDown<CR>
    # with filetype                                              = {'':cmd_all, 'go':cmd}

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

    keymap_kdl = parse_kdl_doc('') # generate keymap_kdl from User keybinds
    for     keybind,keybind_d in key2cmd_ft_m.items(): # l : {h : {'':Mode.S|N}}}
      for   cmd_s  ,fileT_d   in    keybind_d.items(): #      h   {'':Mode.S|N}}}
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

          def_cmd = None
          for  mode in M_ANY: # TODO: m_enum iteration fails in py3.8
            if mode & modes:
              textcmd_d = key2textcmd(keybind, mode)
              if (_cmd_txt := textcmd_d['main'  ]): # ‘b’ → <...ViMoveByWordsBackward>
                def_cmd = _cmd_txt
                break
              if (_cmd_txt := textcmd_d['plugin']): # ‘gh’ → <...MultipleCursorsStart>
                def_cmd = _cmd_txt
                break
          props = {}
          fileT_noblank = [f for f in fileT if not f == ''] # ignore '' file types that mean any
          if fileT_noblank:
            props['file'] = " ".join(fileT_noblank)

          cmd_txt_d = dict()
          # keys/plugins can have different commands/mode for the same key
            # nnoremap l k   MoveUpByLines
            # snoremap l k   MultipleCursorsRemove
          # while they will be grouped into one: key2cmd_ft_m {'l':{'k':{'':<Mode.Select|Normal>}}}, so split unique by mode(s)
          # cmd_txt_d {MoveUpByLines         : M.N
          #            MultipleCursorsRemove : M.S }
          for  mode in M_ANY: # TODO: m_enum iteration fails in py3.8
            if mode & modes:
              if not (textcmd_d := key2textcmd(cmd_s, mode)): # empty modes or _ fillers
                continue
              if (cmd_txt := textcmd_d['main'  ]): # ‘b’ → <...ViMoveByWordsBackward>
                if cmd_txt not in cmd_txt_d:
                  cmd_txt_d[cmd_txt]  = M(0)
                cmd_txt_d  [cmd_txt] |= mode
                # print(f"found cmd in def ¦{cmd_txt}¦ for T=¦{T}¦")
              if (cmd_txt := textcmd_d['plugin']): # ‘gh’ → <...MultipleCursorsStart>
                if cmd_txt not in cmd_txt_d:
                  cmd_txt_d[cmd_txt]  = M(0)
                cmd_txt_d  [cmd_txt] |= mode
                # print(f"found cmd in plug ¦{cmd_txt}¦ for T=¦{T}¦")
          # print(f"found unique key/plugin commands ¦{cmd_txt_d}¦")
          for cmd_txt,mode_enum in cmd_txt_d.items():
            if cmd_s:
              props['defk'] = cmd_s # save ‘b’ default vim key to props ‘defk’
            if def_cmd:
              props['defc'] = def_cmd # save ‘MultipleCursorsSkip’ default command for ‘l’ key to props ‘defc’
            if '"' in cmd_txt: # create a raw string to avoid escaping quotes
              arg = kdl.RawString(tag=None,value=cmd_txt)
            else:
              arg = kdl.   String(tag=None,value=cmd_txt)
            node_key = kdl.Node(tag=f"{mode_enum:®}", name=keybind, args=[arg], props=props)
            # (Ⓝ)d     "MoveByWordsBackward"  def="b"
            # (Ⓝ)<D-d> "MultipleCursorsStart" def="gh"

            keymap_kdl.nodes.append(node_key)

    dest = expand(kwargs.get('file',self.dest)) # expand Sublime variables
    data_name = 'keybinds in KDL'
    msg  = f'/*Autogenerated user ‘{PACKAGE_NAME}’ keybinds in KDL (from .neovintageousrc) via ‘{self.name()}’ command, changes will be overwritten'
    msg += f' (mode)Key "CommandName"   where mode is an abbreviated name or icon from:{MODE_HELP}*/'
    save_to_plugin_folder(dest=dest, data=keymap_kdl,data_name=data_name, pre_msg=msg)


import NeoVintageous.nv.cfg_parse
class NvOldCfgKdl(ApplicationCommand):
  def __init__(self):
    self.keymap	= "NeoVintageous.rc.kdl"
    self.dest  	= f"$packages/{PACKAGE_NAME}/{self.keymap}" # ($platform)

  def run(self, **kwargs):
    # reload config with dumping to kdl enabled
    NeoVintageous.nv.cfg_parse._dump_to_kdl = True
    NeoVintageous.nv.cfg_parse._NVRC_KDL = parse_kdl_doc('')
    sublime.active_window().run_command(cmd='neovintageous',args={'action':'reload_rc_file'})
    NeoVintageous.nv.cfg_parse._dump_to_kdl = False

    keymap_kdl = NeoVintageous.nv.cfg_parse._NVRC_KDL
    dest = expand(kwargs.get('file',self.dest)) # expand Sublime variables
    data_name = 'config in KDL'
    msg  = f'/*Autogenerated user ‘{PACKAGE_NAME}’ config in KDL (from .neovintageousrc as is line-by-line) via ‘{self.name()}’ command, changes will be overwritten\n'
    msg += f' - r#"" ...   preserves commented lines with nodes named -\n'
    msg += f' (mode)Key "CommandName"   where mode is an abbreviated name or icon from:{MODE_HELP}*/'
    save_to_plugin_folder(dest=dest, data=keymap_kdl,data_name=data_name, pre_msg=msg)


def save_to_plugin_folder(dest, data, data_name, pre_msg):
  if not (parent := Path(dest).parent).exists():
    try:
      os.mkdir(parent)
      print(f"{PACKAGE_NAME}: created folder ‘{parent}’ to store ‘{data_name}’")
    except FileNotFoundError as e:
      sublime.error_message(f"{PACKAGE_NAME}: need to save ‘{data_name}’ at ‘{dest}’, but its grand-parent folder doesn't exist:\n‘{e}’")
      return
    except FileExistsError as e:
      pass
  try:
    with open(dest, 'w') as file:
      print(pre_msg, file=file)
      print(data   , file=file)
      sublime.message_dialog(f"{PACKAGE_NAME}:\nSaved ‘{data_name}’ at ‘{dest}’")
    sublime.active_window().open_file(dest)
  except FileNotFoundError as e:
    sublime.error_message(f"{PACKAGE_NAME}:\nTried and failed to save ‘{data_name}’ to\n{dest}")
