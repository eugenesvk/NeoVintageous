import re
import json
import logging
from typing  import Union, Callable
from pathlib import Path

import sublime
import sublime_plugin

import NeoVintageous.dep.kdl as kdl
from NeoVintageous.nv.modes import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE
from NeoVintageous.nv.modes import Mode, Mode as M, text_to_modes, mode_names, MODE_NAMES_OLD, M_EVENT, M_ANY, M_CMDTXT
from NeoVintageous.nv.cfg import _keybind_prop, re_count, re_subl_tag, re_filetype
from NeoVintageous.nv.cfg_parse import clean_name, clean_cmd, _pre_load, _source

from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL, TFMT, DFMT
_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)

from typing import Union
import typing as tp

def node_tag_val(node:kdl1.Node):
  tag = node.tag   if hasattr(node,'tag'  ) else ''
  val = node.value if hasattr(node,'value') else node.name
  return (tag,val)
def node_tag(node:kdl1.Node) -> Union[str, None]:
  return node.tag
def children(node:kdl1.Node) -> kdl1.Node:
  for child in node.nodes:
    yield child
t_parent = Union[kdl.Document, kdl.Node]
def node_get(doc_or_node:t_parent, name:str, df=None):
  return doc_or_node.get(name, df)

def arg_tag_val           (node:kdl.Node):
  for arg            in node.args      : # Parse arguments
    tag =            arg.tag       if hasattr(arg    ,'tag'  ) else ''
    val =            arg.value     if hasattr(arg    ,'value') else arg
    yield (arg,tag,val)
def arg_tag_val_clean     (node:kdl.Node):
  for arg            in node.args      : # Parse arguments
    tag = clean_name(arg.tag       if hasattr(arg    ,'tag'  ) else '' )
    val = clean_cmd (arg.value     if hasattr(arg    ,'value') else arg)
    yield (arg,tag,val)
def prop_key_tag_val      (node:kdl.Node):
  for (pkey,tag_val) in node.props.items(): # Parse properties
    tag =            tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
    val =            tag_val.value if hasattr(tag_val,'value') else tag_val
    yield (pkey,tag_val,tag,val)
def prop_key_tag_val_clean(node:kdl.Node):
  for (pkey,tag_val) in node.props.items(): # Parse properties
    tag = clean_name(tag_val.tag   if hasattr(tag_val,'tag'  ) else ''     )
    val = clean_cmd (tag_val.value if hasattr(tag_val,'value') else tag_val)
    yield (pkey,tag_val,tag,val)

def get_tag_val_warn(tag_val:kdl.Value,logger:logging.Logger=None,node_name:str=''):
  """split KDL value into tag and value, and warn if tag exists"""
  # val = tag_val.value if hasattr(tag_val,'value') else tag_val # ignore tag
  if hasattr(tag_val,'value'):
    tag = tag_val.tag
    val = tag_val.value
    if logger:
      logger.warn("node ‘%s’ has unrecognized tag in value ‘%s’",node_name,tag_val)
  else:
    tag = None
    val = tag_val
  return (tag,val)

def clean_node_name(node:kdl.Node,rec:bool=True,parent:Union[str,None]=None): # recursively clean KDL node names (remove separators ␠⭾-_. etc)
  node.name = re.sub(node_separator,'',node.name.casefold())
  if rec:
    if   node.name in ['keybind','rc']: # don't normalize keybind/init Ex commands
      return
    elif node.name == 'alias'\
      and parent   == 'abolish': # don't normalize children of ‘alias’ as they can be - _
      return
    elif node.name == 'event': # don't normalize event cli commands (but normalize the initial (mode)Event node)
      rec = False
    if node.name == 'abolish':
      for node in node.nodes:
        clean_node_name(node, rec=rec, parent='abolish')
    else:
      for node in node.nodes:
        clean_node_name(node, rec=rec)

def parse_kdl_config(cfg:str, cfg_p:Path, kdl_docs:list, enclose_in:str='',var_d:dict={}):
  _log.cfg("  1parse_kdl_config @ %s with vars %s",cfg_p,var_d)

  def fn_i(kdl_py_obj, parse_fragment):
    # print(f"kdl_py_obj = |{kdl_py_obj}|") # (i)"Ctrl"
    # print(f"tag=|{kdl_py_obj.tag}| val=|{kdl_py_obj.value}|") #tag=|i| val=|Ctrl|
    # print(f"parse_fragment.fragment=|{parse_fragment.fragment}|") # "Ctrl" raw text of the value after the tag
    # raise parse_fragment.error("str_err") # kdl.errors.ParseError: 1:N parse error: str_err
    # .error(str) takes a custom error message and returns a kdl.ParseError with the ParseFragment's location already built in, ready for you to raise. This should be used if your conversion fails for any reason, so your errors look the same as native parse errors
    return kdl_py_obj
  def fn_import(kdl_py_obj, parse_fragment, kdl_docs=kdl_docs):
    # print(f"kdl_py_obj = |{kdl_py_obj}|") # #import (keybind)"NV.key.kdl" tvar=(var)"a"
    # print(f"tag=|{kdl_py_obj.tag}| name=|{kdl_py_obj.name}|") #tag=None val=#import
    # print(f"parse_fragment.fragment=|{parse_fragment.fragment}|") # "#import" raw text of the value after the tag
    import_var = {}
    for i,key in enumerate(prop_d := kdl_py_obj.props):
      val = prop_d[key]
      # print(f"{i} {key}={val}")
      if hasattr(val,'tag'): # print(f"  tag={val.tag}")
        import_var[key] = val

    _log.cfg("%s",import_var)
    var_set   = dict()
    var_d_new = dict()
    for pkey,tag_val in kdl_py_obj.props.items(): # Parse properties for var_name=(var)"val" pairs
      tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''      #(var)
      val = tag_val.value if hasattr(tag_val,'value') else tag_val #"val"
      if tag in ['var','$']:
        var_set[pkey] = val
      if tag in ['varpass','$→']:
        if pkey in var_d['set']:
          var_set[pkey] = var_d['set'][pkey]
          _log.cfg("  passing %s=%s",pkey,var_d['set'][pkey])
        else:
          _log.warn("  ‘%s’ variable is supposed to be passed from the variables available to this config, but it can't be found in %s (parsing ‘%s’)", pkey, list(var_d['set'].keys()), kdl_py_obj)
        if val:
          _log.warn("  ‘varpass’ variable ‘%s’ should have an empty value, not ‘%s’", pkey,val)
    var_d_new['set'] = var_set

    for arg in kdl_py_obj.args: # import (keybind)"./NV/mykeys.kdl"
      tag = arg.tag   if hasattr(arg,'tag'  ) else enclose_in # todo: or enclose twice?
      val = arg.value if hasattr(arg,'value') else arg
      ext = '' if val.lower().endswith('.kdl') else '.kdl'
      fname = val + ext
      enclose_pre = (tag + ' {\n') if tag else '' # keybind
      enclose_pos =          '\n}' if tag else ''
      _log.debug("arg=‘%s’ tag=‘%s’ cfg_p.parent=‘%s’ val=‘%s’%s\n(cfg_p=‘%s’)"
        ,         arg,     tag,     cfg_p.parent,     val,   ext,  cfg_p)
      if (cfg_import_f := Path(cfg_p.parent,fname).expanduser()).exists():
        try:
          with open(cfg_import_f, 'r', encoding='utf-8', errors='replace') as f:
            cfg_import = enclose_pre + f.read() + enclose_pos
        except FileNotFoundError as e:
          sublime.error_message(f"{PACKAGE_NAME}:\nTried and failed to load\n{cfg_import_f}")
          break
      else:
        sublime.error_message(f"{PACKAGE_NAME}:\nCouldn't find config\n{cfg_import_f}\nimported in\n{cfg_p}")
        break
      parse_kdl_config(cfg_import, cfg_import_f, kdl_docs, enclose_in=tag, var_d=var_d_new)
    return None # consume imports, successfull will be stored as separate docs, so drop kdl_py_obj

  parseConfig = kdl.ParseConfig(
    nativeUntaggedValues  =True         #|True| produce native Py objects (str int float bool None) for ()untagged values, or kdl-Py objects (kdl.String kdl.Decimal...)
    ,nativeTaggedValues   =True         #|True| produce native Py objects for (tagged)values for predefined tags like i8..u64 f32 uuid url regex
    #,valueConverters     = {"i":fn_i}  # A dictionary of tag->converter functions
    ,nodeConverters       = {(None,"import"):fn_import,(None,"Import"):fn_import # match untagged import node ()
      } # A dictionary of NodeKey->converter functions
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
  doc = kdl.Parser(parseConfig, printConfig).parse(cfg)
  for node in doc.nodes:
    clean_node_name(node)
  # print(type(doc),'\n',doc)
  kdl_docs += [(doc,var_d)] # append parsed doc to the list

  return (doc,var_d)

def _parse_rc_g_kdl(rc_g:kdl.Node):
  win = sublime.active_window()
  for node in rc_g.nodes: # r#":set invrelativenumber"#
    _parse_rc_cfg_kdl(win,rc_cfg=node)
def _parse_rc_cfg_kdl(win,rc_cfg:kdl.Node) -> None:
  if not (cfgT := type(rc_cfg)) is kdl.Node:
    _log.error("Type of ‘rc’ config group should be kdl.Node, not ‘%s’",cfgT)
    return None
  node = rc_cfg               # r#":set invrelativenumber"#
  if node.args or\
    node.props:
    _log.warn("‘rc’ config nodes must have no arguments/properties ‘%s’",node)
    return None
  opt_name = node.name     # r#":set invrelativenumber"#
  if opt_name:
    # print(f"‘rc’ config: node with no args/props, running as an Ex command ‘{node}’")
    _source(win, [opt_name], nodump=True)
    return None

def _parse_general_g_kdl(general_g:kdl.Node,CFG:dict,DEF:dict):
  win = sublime.active_window()
  st_pref = sublime.load_settings('Preferences.sublime-settings')
  if (src_pre := general_g.get((None,"source"))):
    if (args := src_pre.args):
      tag_val = args[0] #(t)"/dvorak.neovintageous" if (t) exists (though shouldn't)
      # val = tag_val.value if hasattr(tag_val,'value') else tag_val # ignore tag
      if hasattr(tag_val,'value'):
        val = tag_val.value # ignore tag
        _log.warn("node ‘%s’ has unrecognized tag in argument ‘%s’"
          ,      src_pre.name,                               tag_val)
      else:
        val = tag_val
      # print(f"loading source first ‘{val}’")
      _pre_load(win,val)
  for node in general_g.nodes: # set relativenumber=true
    _parse_general_cfg_kdl1(general_cfg=node,CFG=CFG,DEF=DEF,st_pref=st_pref)

def _parse_set_kdl(node:kdl.Node,cfg='') -> None:
  from NeoVintageous.nv.ex_cmds import ex_set # inline import to avoid circular dependency errors
  args = dict()
  if (win := sublime.active_window()):
    args['window'] = win
    if (view := win.active_view()):
      args['view'] = view

  for arg in node.args:          # Parse arguments
    tag = clean_name(arg.tag   if hasattr(arg,'tag'  ) else '' )
    val = clean_cmd (arg.value if hasattr(arg,'value') else arg)
    _log.debug(f"set option from kdl arg: ¦{val}¦")
    ex_set(option=val,value=None, **args)
  for pkey,tag_val in node.props.items(): # Parse properties
    tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
    val = tag_val.value if hasattr(tag_val,'value') else tag_val
    _log.debug(f"set option from kdl prop: ¦{pkey}¦=¦{val}¦")
    if   val == True:
      opt_key =       pkey
      opt_val = None
    elif val == False:
      opt_key = 'no' +pkey
      opt_val = None
    elif val in ['inv','invert','!']:
      opt_key = 'inv'+pkey
      opt_val = None
    elif val in ['show','?']:
      opt_key =       pkey+'?'
      opt_val = None
    else:
      opt_key =       pkey
      opt_val = val
    ex_set(option=opt_key,value=opt_val, **args)

from NeoVintageous.nv import variables
def _parse_let_kdl(node:kdl.Node,cfg='') -> None:
  if not node.props:
    _log.warn("%sconfig has a ‘let’ command without var=value properties (%s)",
      f'‘{cfg}’ ' if cfg else '',                                     node)
  for pkey,tag_val in node.props.items():
    tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
    val = tag_val.value if hasattr(tag_val,'value') else tag_val
    _log.debug(f"set var from kdl: ¦{pkey}¦=¦{val}¦")
    variables.set(pkey,val)

def _parse_general_cfg_kdl1(general_cfg:kdl.Node,CFG:dict,DEF:dict,st_pref=None) -> None:
  if not (cfgT := type(general_cfg)) is kdl.Node:
    _log.error("Type of ‘general’ config group should be kdl.Node, not ‘%s’",cfgT)
    return None
  node = general_cfg          # set relativenumber=true
  opt_name    = node.name     # ‘set’
  if   opt_name == '≠': # skip comment nodes (todo: when lib supports roundtrip, save as actual comments)
    return
  elif opt_name == 'source': # source was loaded before
    return
  elif opt_name == 'let':
    _parse_let_kdl(node)
    return None
  elif opt_name == 'set':
    _parse_set_kdl(node)
    return None
  elif opt_name == 'vardef': #vardef pre="‹" pos="›"
    # print('CFG pre',CFG)
    tag_val = node.name
    tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
    val = tag_val.value if hasattr(tag_val,'value') else tag_val
    if tag: # vardef should have no tags
      _log.warn("node ‘%s’ has unrecognized tag",node.name)
      return None
    for pkey,tag_val in node.props.items(): # parse definition properties
      tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
      val = tag_val.value if hasattr(tag_val,'value') else tag_val
      if pkey == 'pre':
        CFG['var_def'][0] = val #‹
      if pkey == 'pos':
        CFG['var_def'][1] = val #›
    # print('CFG pos',CFG)
    return None
  elif opt_name in DEF['gen_def']:
    opt_d    =   DEF['gen_def'][opt_name]
    name_def = opt_d['key'] # vintageous_auto_switch_input_method
    type_def = opt_d['t']   # bool
    val_def  = opt_d['v']   # False
    if type_def == dict: # todo: iterate over values to strip tags?
      if not node.props:
        _log.error("Unrecognized option type for %s in the ‘general’ config group, expecting %s, but there are no key=val properties!"
            ,                             opt_name,                                   type_def)
      else:
        CFG['general'][name_def] = node.props
        _over = ''
        if  st_pref.has(f"vintageous_{name_def}"): # override Preferences with KDL's
          st_pref.set(f"vintageous_{name_def}", node.props)
          _over = ' (overridden Preferences)'
        if  st_pref.has(           f"{name_def}"): # override Preferences with KDL's
          st_pref.set(           f"{name_def}", node.props)
          _over = ' (overridden Preferences)'
        _log.cfg("set user dict ‘%s’=‘%s’%s",name_def,node.props,_over)
      return None
    else:
      for arg in node.args:
        tag = arg.tag   if hasattr(arg,'tag'  ) else ''
        val = arg.value if hasattr(arg,'value') else arg
        _log.debug("%s %s %s", arg, f"tag={tag}", f"val={val}")
        isSameType = False
        if   isinstance(    type_def,type):
          if isinstance(val,type_def):
            isSameType = True
          else:
            if type_def in [int,float] and\
              type(val) in [int,float]:
                isSameType = True
        elif isinstance(type_def,list):
          for t_ in type_def:
            if isinstance(val,t_):
              isSameType = True
        if not isSameType:
          _log.error("Unrecognized option type for %s in the ‘general’ config group, expecting %s not ‘%s’ (‘%s’)"
            ,                             opt_name,                                   type_def,type(val),val)
          return None
        CFG['general'][name_def] = val
        _over = ''
        if  st_pref.has(f"vintageous_{name_def}"): # override Preferences with KDL's
          st_pref.set(f"vintageous_{name_def}", val)
          _over = ' (overridden Preferences)'
        if  st_pref.has(           f"{name_def}"):
          st_pref.set(           f"{name_def}", val)
          _over = ' (overridden Preferences)'
        _log.cfg("set user ‘%s=%s’ (%s)%s"
          ,         name_def,val, type(val), _over)
        return None
  else:
    _log.error("Unrecognized option type within ‘general’ config group, expecting ‘let’/‘set’/‘-’, not ‘%s’",opt_name)
    return None

import copy
def _parse_keybind_arg(node:kdl.Node, CFG:dict, prop_subl={}):
  cmd_l   = []
  cmd_o   = [] # original unmodified command for later display purposes
  isChain = False
  for arg in node.args:          # Parse arguments
    tag = clean_name(arg.tag   if hasattr(arg,'tag'  ) else '' )
    val = clean_cmd (arg.value if hasattr(arg,'value') else arg)
    val_dirt =       arg.value if hasattr(arg,'value') else arg
    count = 1
    if val == 'chain':
      isChain = True
      continue
    if re_subl_tag.search(tag): # Sublime command per tag, serialize into a json dump
      prop_subl_clean = copy.deepcopy(prop_subl)
      for key in prop_subl: # remove reserved flags so Sublime doesn't choke on them
        if clean_name(key) in CFG['res_tag']:
          del prop_subl_clean[key]
      subl_arg = f',"args":{json.dumps(prop_subl_clean)}' if prop_subl_clean else ''
      cmd      = f'"command":"{val_dirt}"{subl_arg}<CR>'
      cmdo     = val_dirt
      # (Ⓝ)q (subl)"move" by="words" forward=true extend=true
      # →"command":"move","args":{"by": "words", "forward": true, "extend": true}<CR>
      _log.cfg("parsed (subl) command ¦%s¦ val_dirty=¦%s¦ arg=¦%s¦ → ¦%s¦"
        ,                            cmd, val_dirt,subl_arg, prop_subl_clean)
    else:
      cmd  = val
      cmdo = val_dirt
    if count_l := re_count.findall(tag): # find a count tag and add commands×count
      count = int(count_l[0])
    for i in range(1,1+(count if count > 1 else 1)):
      cmd_l.append(cmd)
      cmd_o.append(cmdo)
  return (cmd_l, cmd_o, isChain)
def _parse_vars_kdl(node_vars:kdl.Node,CFG:dict,var_d:dict={}):
  # print(f"var_d pre {var_d}")
  # use var_d from #import key=val props to seed initial values
  pre = CFG['var_def'][0] #‘
  pos = CFG['var_def'][1] #’
  if 'def' in var_d:
    var_def = var_d['def']
    if len(var_def) >= 2:
      pre = var_def[0]
      pos = var_def[1]
  var_set = var_d['set'] if 'set' in var_d else dict()
  for node in node_vars.getAll('vardef'):
    tag_val = node.name
    tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
    val = tag_val.value if hasattr(tag_val,'value') else tag_val
    if tag: # vardef should have no tags
      _log.warn("node ‘%s’ has unrecognized tag",node.name)
      continue
    for pkey,tag_val in node.props.items(): # parse definition properties
      tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
      val = tag_val.value if hasattr(tag_val,'value') else tag_val
      if pkey == 'pre':
        pre = val
      if pkey == 'pos':
        pos = val
  var_def = [pre,pos]
  for node in node_vars.getAll('varset'):
    tag_val = node.name
    tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
    val = tag_val.value if hasattr(tag_val,'value') else tag_val
    if tag: # vardef/set should have no tags
      continue
    for (key,tag_val) in node.props.items(): # 2. testvar=⎇ key=value pairs
      if hasattr(tag_val,'value'): #=(t)⎇ if (t) exists (though shouldn't)
        val = tag_val.value # ignore tag
        _log.warn("node ‘%s’ has unrecognized tag in argument ‘%s’"
          ,      node.name,                               tag_val)
      else:
        val = tag_val
      var_set[key.lower()] = val
  _log.debug("found in vardef¦%s¦ and varset¦%s¦"
    ,                  var_def,         var_set)
  re_flags = 0
  re_flags |= re.MULTILINE | re.IGNORECASE
  re_var_set_p = f'{pre}(' + f'){pos}|{pre}('.join(var_set.keys()) + f'){pos}'
  re_var_set = re.compile(re_var_set_p, flags=re_flags)
  var_d['def'] = var_def
  var_d['set'] = var_set
  var_d['re']  = re_var_set
  # print(f"var_d pos {var_d}")
  return var_d

def _parse_keybinds_kdl(keybinds:kdl.Node,CFG:dict,cfgU,var_d:dict={}):
  var_d_combo = _parse_vars_kdl(keybinds,CFG,var_d)
  from NeoVintageous.nv.mappings import mappings_add_text
  for kb_node in keybinds.nodes: # (Ⓝ)"q" "OpenNameSpace"
    _parse_keybind_kdl(keybind=kb_node, CFG=CFG, cfgU=cfgU, map_add=mappings_add_text, var_d=var_d_combo)
def _parse_keybind_kdl(keybind:kdl.Node, CFG:dict, cfgU, map_add:Callable, gmodes:Mode=Mode(0),var_d:dict={}):
  if not (cfgT := type(keybind)) is kdl.Node:
    _log.error("Type of ‘keybind’ should be kdl.Node, not ‘%s’",cfgT)
    return None
  node = keybind                 # (Ⓝ)"q" "OpenNameSpace"
  mode_s = node.tag              # ‘Ⓝ’
  key    = node.name             # ‘q’
  children = node.nodes          # either full keybinds or just commands with Chain argument
  cmd_o   = []                   # ‘[OpenNameSpace]’ # original user supplied name
  cmd_txt = []                   # ‘[opennamespace]’
  if key in ['vardef','varset'] and node.tag is None: # skip variables (parsed earlier)
    return
  if key == '≠': # skip comment nodes (todo: when lib supports roundtrip, save as actual comments)
    return
  if key == 'let':
    _parse_let_kdl(node)
    return
  if key == 'set':
    _parse_set_kdl(node)
    return
  if var_d and var_d['set']:
    # key_old = key # ‘var_name’ → var_value (match ‘var_name’, but need to find value for var_name, so use index to find the ‘(var_name)’ regex match)
    if key:
      key    = var_d['re'].sub(lambda m: m.group().replace(m.group(),var_d['set'][m[m.lastindex]],1), key   )
    if mode_s:
      mode_s = var_d['re'].sub(lambda m: m.group().replace(m.group(),var_d['set'][m[m.lastindex]],1), mode_s)
    # if not key_old == key:
      # _log.debug("replaced var in key: %s → %s"
        # ,                        key_old, key)
  modes  = text_to_modes(mode_s) # ‘Mode.Normal’ enum for ‘Ⓝ’ (‘Mode.Any’ for None tag)
  if gmodes:
    if mode_s:
      modes |= gmodes        # append modes from a group
    else:
      modes  = gmodes        # replace ‘Mode.Any’ with group mode

  prop = dict()                  # Parse properties
  prop_rest = dict()             # Properties left from known defaults (e.g., part of Sublime commands)
  for pkey,tag_val in node.props.items(): # ‘i="✗" d="Close a tab"’
    tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
    val = tag_val.value if hasattr(tag_val,'value') else tag_val
    for dkey,key_abbrev in _keybind_prop.items():
      if dkey == 'file':
        if pkey in key_abbrev: # ['ft','filetype']
          prop[dkey] = []
          prop[dkey].extend(re_filetype.split(val))
      else:
        if pkey in key_abbrev:
          prop[dkey] = val
      if pkey not in key_abbrev: # non-specified key=val pairs
        if isinstance(val,float) and val.is_integer():
          prop_rest[pkey] = int(val)
        else:
          prop_rest[pkey] = val
  (cmd,cmdo,isChain)    = _parse_keybind_arg(node=node, CFG=CFG, prop_subl=prop_rest) # Parse arguments
  cmd_txt.extend(cmd )
  cmd_o  .extend(cmdo)
  if children and isChain:           # with Chain argument...
    for child in children:         # ...parse children as commands
      prop_rest = dict()
      for pkey,tag_val in child.props.items(): #
        tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
        val = tag_val.value if hasattr(tag_val,'value') else tag_val
        for dkey,key_abbrev in _keybind_prop.items():
          if pkey not in key_abbrev: # non-specified key=val pairs
            prop_rest[pkey] = val
      (cmd,cmdo,_) = _parse_keybind_arg(node=child, CFG=CFG, prop_subl=prop_rest)
      cmd_txt.extend(cmd )
      cmd_o  .extend(cmdo)

  if not modes:
    _log.error("Couldn't parse ‘%s’ to a list of modes, skipping ‘%s’"
      ,                     mode_s,                            node)
    return
  if not key:
    _log.error("Missing keyboard shortcut, skipping ‘%s’",node)
    return
  if not cmd_txt and not children:
    _log.error("Missing text command(s), skipping ‘%s’",node)
    return
  if (m_inv := modes & ~M.CmdTxt): # if there are more modes than allowed
    # s = 's' if len(m_inv) > 1 else '' # TODO len fails in py3.8
    mode_sym = ''
    for mode in M_ANY: # TODO: m_inv iteration fails in py3.8
      if mode & m_inv: # todo: store original re matches in text_to_mode to allow roundtrip of modes matching user input
        mode_sym += mode_names[mode][0]
    _log.warn(          "Invalid mode%s ‘%s’ in ‘%s’ in node ‘%s’"
      ,'s' if len(mode_sym) > 1 else '',mode_sym,mode_s,     node)
  if cmd_txt:
    for mode in M_CMDTXT: # iterate over all of the allowed modes
      if mode & modes:  # if it's part of the keybind's modes, register the key
        cfgU.text_commands[mode][key] = cmd_txt
        map_add(mode=MODE_NAMES_OLD[mode], key=key, cmd=cmd_txt, cmd_o=cmd_o, prop=prop)
        # print(f"kb map+ ({mode}){key}={cmd_txt} with {prop}")
  if children and not isChain:       # without Chain argument...
    for child in children:         # ...parse children as keybinds
      _parse_keybind_kdl(keybind=child, CFG=CFG, cfgU=cfgU, map_add=map_add, gmodes=modes, var_d=var_d)

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

def flatten_kdl(kdl_dic:Union[kdl1.Document,kdl1.Node,dict], key_parent:str = '', sep:str = '.', lvl:int=0, ignore:dict={1:[],2:[]}):
  """convert KDL document or a dictionary of KDL nodes into a flat dictionary, ignoring 2nd+ argument, but retaining key=val properties"""
  return dict(_flatten_kdl_gen(kdl_dic, key_parent, sep, lvl, ignore))

def parse_kdl_doc(s,v_untag:bool=False,v_tag:bool=False):
  parseConfig = kdl.ParseConfig(
    nativeUntaggedValues    = v_untag  #|True| produce native Py objects (str int float bool None) untagged values (no (foo)prefix), or kdl-Py objects (kdl.String kdl.Decimal...)
    ,nativeTaggedValues     = v_tag    #|True| produce native Py objects for (tagged)values for predefined tags like i8..u64 f32 uuid url regex
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
