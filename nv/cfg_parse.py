import re
import logging
from typing  import Union
from pathlib import Path

import sublime
import sublime_plugin

import NeoVintageous.dep.kdl as kdl
import NeoVintageous.dep.kdl2 as kdl2
_libckdl = False
try:
  import ckdl
  _libckdl = True
except ImportError:
  _libckdl = False
except ModuleNotFoundError:
  _libckdl = False
from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL, TFMT
from NeoVintageous.plugin import PACKAGE_NAME

_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)
if _log.hasHandlers(): # clear existing handlers, including sublime's
    logging.getLogger(__name__).handlers.clear()
    # _log.addHandler(stream_handler)
_L = True if _log.isEnabledFor(logging.CFG) else False


re_flags = 0
re_flags |= re.MULTILINE | re.IGNORECASE
node_separator_p = r"\s|-|−|–|—|⁃|_|\."
path_separator_p = r"\s|-|−|–|—|⁃|_"
node_separator = re.compile(node_separator_p, flags=re_flags)
path_separator = re.compile(path_separator_p, flags=re_flags)
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
def clean_node_name2(node:kdl2.Node,rec:bool=True,parent:Union[str,None]=None): # recursively clean KDL2 node names (remove separators ␠⭾-_. etc)
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
        clean_node_name2(node, rec=rec, parent='abolish')
    else:
      for node in node.nodes:
        clean_node_name2(node, rec=rec)
def clean_node_name_c(node:ckdl.Node,rec:bool=True,parent:Union[str,None]=None): # recursively clean KDL2 node names (remove separators ␠⭾-_. etc)
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
      for node in node.children:
        clean_node_name_c(node, rec=rec, parent='abolish')
    else:
      for node in node.children:
        clean_node_name_c(node, rec=rec)
def clean_name(name:str): # clean name by removing separators ␠⭾-_. and converting to lowercase
  return re.sub(node_separator,'',name.casefold()) if  name                                              else name
def clean_cmd (name:str): # convert command name to lowercase (don't remove _ since sublime uses those as seps)
  return                          name.casefold()  if (name and not (len(name) == 1 and name.isascii())) else name
def clean_path(name:str): # clean path segment by removing separators ␠⭾-_ but NOT . and converting to lowercase
  return re.sub(path_separator,'',name.casefold()) if  name                                              else name

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
def parse_kdl2_doc(s,v_untag:bool=False,v_tag:bool=False):
  parseConfig = kdl2.ParseConfig(
    nativeUntaggedValues    = v_untag  #|True| produce native Py objects (str int float bool None) untagged values (no (foo)prefix), or kdl-Py objects (kdl.String kdl.Decimal...)
    ,nativeTaggedValues     = v_tag    #|True| produce native Py objects for (tagged)values for predefined tags like i8..u64 f32 uuid url regex
  )
  printConfig = kdl2.PrintConfig(
    indent             ="  "   #|"\t"|
    ,semicolons        =False  #|False|
    ,printNulls        =True   #|True| if False, skip over any "null"/None arg/props. Corrupts docs that use "null" keyword intentionally, but can be useful if you'd prefer to use a None value as a signal that the argument has been removed
    ,respectStringType =True   #|True| output strings as the same type they were in the input, either raw (r#"foo"#) or normal ("foo") (only kdl-Py, not native ones (e.g, set nativeUntaggedValues=False))
    ,respectRadix      =True   #|True| ≈respectStringType, output numbers as the radix they were in the input, like 0x1b for hex numbers. False: print decimal numbers (kdl-Py)
    ,exponent          ="e"    #|e| character to use for the exponent part of decimal numbers, when printed with scientific notation, "e" or "E" (kdl-Py)
  )
  return kdl2.Parser(parseConfig, printConfig).parse(s)

def parse_kdl_config(cfg:str, cfg_p:Path, kdl_docs:list, enclose_in:str='',var_d:dict={}):
  _log.cfg("  parse_kdl_config @ %s with vars %s",cfg_p,var_d)

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
    nativeUntaggedValues	=True       	#|True| produce native Py objects (str int float bool None) for ()untagged values, or kdl-Py objects (kdl.String kdl.Decimal...)
    ,nativeTaggedValues 	=True       	#|True| produce native Py objects for (tagged)values for predefined tags like i8..u64 f32 uuid url regex
    #,valueConverters   	= {"i":fn_i}	# A dictionary of tag->converter functions
    ,nodeConverters     	= {(None,"import"):fn_import,(None,"Import"):fn_import # match untagged import node ()
      } # A dictionary of NodeKey->converter functions
  )
  printConfig = kdl.PrintConfig(
    indent            	="  " 	#|"\t"|
    ,semicolons       	=False	#|False|
    ,printNullArgs    	=True 	#|True| if False, skip over any "null"/None arguments. Corrupts docs that use "null" keyword intentionally, but can be useful if you'd prefer to use a None value as a signal that the argument has been removed
    ,printNullProps   	=True 	#|True| =printNullArgs, but applies to properties
    ,respectStringType	=True 	#|True| output strings as the same type they were in the input, either raw (r#"foo"#) or normal ("foo") (only kdl-Py, not native ones (e.g, set nativeUntaggedValues=False))
    ,respectRadix     	=True 	#|True| ≈respectStringType, output numbers as the radix they were in the input, like 0x1b for hex numbers. False: print decimal numbers (kdl-Py)
    ,exponent         	="e"  	#|e| character to use for the exponent part of decimal numbers, when printed with scientific notation, "e" or "E" (kdl-Py)
  )
  doc = kdl.Parser(parseConfig, printConfig).parse(cfg)
  for node in doc.nodes:
    clean_node_name(node)
  # print(type(doc),'\n',doc)
  kdl_docs += [(doc,var_d)] # append parsed doc to the list

  return (doc,var_d)

def parse_kdl2_config(cfg:str, cfg_p:Path, kdl_docs:list, enclose_in:str='',var_d:dict={}):
  _log.cfg("  parse_kdl2_config @ %s with vars %s",cfg_p,var_d)

  def fn_i(kdl_py_obj, parse_fragment):
    return kdl_py_obj
  def fn_import(kdl_py_obj, parse_fragment, kdl_docs=kdl_docs):
    import_var = {}
    for (key, val) in kdl_py_obj.getProps((...,...)):
      if hasattr(val,'tag') and val.tag is not None:
        import_var[key] = val

    _log.cfg("%s",import_var)
    var_set   = dict()
    var_d_new = dict()
    for (pkey,tag_val) in kdl_py_obj.getProps((...,...)): # Parse properties for var_name=(var)"val" pairs
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

    for arg in kdl_py_obj.getArgs((...,...)): # import (keybind)"./NV/mykeys.kdl"
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
      parse_kdl2_config(cfg_import, cfg_import_f, kdl_docs, enclose_in=tag, var_d=var_d_new)
    return None # consume imports, successfull will be stored as separate docs, so drop kdl_py_obj

  parseConfig = kdl2.ParseConfig(
    nativeUntaggedValues	=True       	#|True| produce native Py objects (str int float bool None) for ()untagged values, or kdl-Py objects (kdl2.String kdl2.Decimal...)
    ,nativeTaggedValues 	=True       	#|True| produce native Py objects for (tagged)values for predefined tags like i8..u64 f32 uuid url regex
    #,valueConverters   	= {"i":fn_i}	# A dictionary of tag->converter functions
    ,nodeConverters     	= {(None,"import"):fn_import,(None,"Import"):fn_import # match untagged import node ()
      } # A dictionary of NodeKey->converter functions
  )
  printConfig = kdl2.PrintConfig(
    indent            	="  " 	#|"\t"|
    ,semicolons       	=False	#|False|
    ,printNulls       	=True 	#|True| if False, skip over any "null"/None arg/props. Corrupts docs that use "null" keyword intentionally, but can be useful if you'd prefer to use a None value as a signal that the argument has been removed
    ,respectStringType	=True 	#|True| output strings as the same type they were in the input, either raw (r#"foo"#) or normal ("foo") (only kdl-Py, not native ones (e.g, set nativeUntaggedValues=False))
    ,respectRadix     	=True 	#|True| ≈respectStringType, output numbers as the radix they were in the input, like 0x1b for hex numbers. False: print decimal numbers (kdl-Py)
    ,exponent         	="e"  	#|e| character to use for the exponent part of decimal numbers, when printed with scientific notation, "e" or "E" (kdl-Py)
  )
  doc = kdl2.Parser(parseConfig, printConfig).parse(cfg)
  for node in doc.nodes:
    clean_node_name2(node)
  # print(type(doc),'\n',doc)
  kdl_docs += [(doc,var_d)] # append parsed doc to the list

  return (doc,var_d)

def parse_user_sublime_cmdline(line:str) -> Union[str,None]:
  command = sublime.decode_value('{'+line+'}')
  if   not  'command' in command:
    return None
  elif not  'args'    in command:
    command['args'] = None
  return command

_dump_to_kdl = False
_NVRC_KDL = None
if _dump_to_kdl:
  _NVRC_KDL = parse_kdl2_doc('')

def _pre_load(window,source) -> None:
  if source and isinstance(source, str):
    try:
      _source(window, iter(sublime.load_resource(source).splitlines()))
      _log.info('sourced %s', source)
    except FileNotFoundError as e:
      print('NeoVintageous:', e)
def _source(window, source, nodump=False) -> None:
  from NeoVintageous.nv.ex_cmds import do_ex_cmdline # inline import to avoid circular dependency errors
  try:
    window.settings().set('_nv_sourcing', True)
    for line in source:
      ex_cmdline = _parse_line(line)
      if ex_cmdline:
        do_ex_cmdline(window, ex_cmdline)
      elif _dump_to_kdl and not nodump:
        node_key = kdl2.Node(tag=None, name='≠', args=[kdl2.RawString(line.rstrip())])
        _NVRC_KDL.nodes.append(node_key)
  finally:
    window.settings().erase('_nv_sourcing')
# Recursive mappings (:map, :nmap, :omap, :smap, :vmap) are not supported. They were removed in version 1.5.0. They were removed because they were they were implemented as non-recursive mappings.
_PARSE_LINE_PATTERN = re.compile('^\\s*(?::)?(?P<cmdline>(?P<cmd>(?:[nsviox])?noremap|let|set|(?:[nsviox])?unmap) .*)$')
def _parse_line(line: str):
  try:
    line = line.rstrip()
    if line:
      match = _PARSE_LINE_PATTERN.match(line)
      if match:
        cmdline = match.group('cmdline')
        # Ensure there is leading colon, because the parser pattern omits it.
        if cmdline:
          cmdline = ':' + cmdline

        # The '|' character is used to chain commands. Users should
        # escape it with a slash or use '<bar>'. See :h map-bar. It's
        # translated to <bar> internally (implementation detail).
        # See https://github.com/NeoVintageous/NeoVintageous/issues/615.
        cmdline = cmdline.replace('\\|', '<bar>')
        cmdline = cmdline.replace('\t', ' ') # avoid bugs with tab literal

        if '|' in cmdline:
          # Using '|' to separate map commands is currently not supported.
          raise Exception('E488: Trailing characters: {}'.format(line.rstrip()))

        return cmdline
  except Exception as e:
    message('error detected while processing {} at line "{}":\n{}'.format(_file_name(), line.rstrip(), str(e)))

  return None
