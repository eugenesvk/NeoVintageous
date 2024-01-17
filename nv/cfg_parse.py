from pathlib import Path

import sublime
import sublime_plugin

import NeoVintageous.dep.kdl as kdl
from NeoVintageous.plugin import PACKAGE_NAME

import re
re_flags = 0
re_flags |= re.MULTILINE | re.IGNORECASE
node_separator_p = r"\s|-|_|\."
node_separator = re.compile(node_separator_p, flags=re_flags)
def clean_node_name(node:kdl.Node): # recursively clean KDL node names (remove separators ␠⭾-_. etc)
  node.name = re.sub(node_separator,'',node.name.casefold())
  if not node.name == 'keymap': # don't normalize keybinds
    for node in node.nodes:
      clean_node_name(node)

def parse_kdl_config(cfg:str, cfg_p:Path, kdl_docs:list, enclose_in:str=''):
  # print(f"  parse_kdl_config = {cfg_p}")

  def fn_i(kdl_py_obj, parse_fragment):
    # print(f"kdl_py_obj = |{kdl_py_obj}|") # (i)"Ctrl"
    # print(f"tag=|{kdl_py_obj.tag}| val=|{kdl_py_obj.value}|") #tag=|i| val=|Ctrl|
    # print(f"parse_fragment.fragment=|{parse_fragment.fragment}|") # "Ctrl" raw text of the value after the tag
    # raise parse_fragment.error("str_err") # kdl.errors.ParseError: 1:N parse error: str_err
    # .error(str) takes a custom error message and returns a kdl.ParseError with the ParseFragment's location already built in, ready for you to raise. This should be used if your conversion fails for any reason, so your errors look the same as native parse errors
    return kdl_py_obj
  def fn_import(kdl_py_obj, parse_fragment, kdl_docs=kdl_docs): # todo fails (None,None) https://github.com/tabatkins/kdlpy/issues/8
    import_var = {}
    for i,key in enumerate(prop_d := kdl_py_obj.props):
      val = prop_d[key]
      # print(f"{i} {key}={val}")
      if hasattr(val,'tag'): # print(f"  tag={val.tag}")
        import_var[key] = val

    # print(import_var)
    for arg in kdl_py_obj.args:
      tag = arg.tag   if hasattr(arg,'tag'  ) else ''
      val = arg.value if hasattr(arg,'value') else arg
      # print(arg, f"tag={tag}", f"val={val}")
      if (cfg_import_f := Path(cfg_p.parent,val).expanduser()).exists():
        try:
          with open(cfg_import_f, 'r', encoding='utf-8', errors='replace') as f:
            cfg_import = (tag + '{\n' if tag else '') + f.read() + ('\n}' if tag else '')
        except FileNotFoundError as e:
          sublime.error_message(f"{PACKAGE_NAME}:\nTried and failed to load\n{cfg_import_f}")
          break
      else:
        sublime.error_message(f"{PACKAGE_NAME}:\nCouldn't find config\n{cfg_import_f}\nimported in\n{cfg_p}")
        break
      parse_kdl_config(cfg_import, cfg_import_f, kdl_docs, enclose_in='keybind')
    return None # consume imports, successfull will be stored as separate docs, so drop kdl_py_obj

  parseConfig = kdl.ParseConfig(
    nativeUntaggedValues	=True       	#|True| produce native Py objects (str int float bool None) for ()untagged values, or kdl-Py objects (kdl.String kdl.Decimal...)
    ,nativeTaggedValues 	=True       	#|True| produce native Py objects for (tagged)values for predefined tags like i8..u64 f32 uuid url regex
    #,valueConverters   	= {"i":fn_i}	# A dictionary of tag->converter functions
    ,nodeConverters     	= {(None,"#import"):fn_import,(None,"#Import"):fn_import # match untagged import node
      ,                      (None, "import"):fn_import,(None, "Import"):fn_import} # A dictionary of NodeKey->converter functions
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
  kdl_docs += [doc] # append parsed doc to the list

  return doc
