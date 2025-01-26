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
def clean_name(name:str): # clean name by removing separators ␠⭾-_. and converting to lowercase
  return re.sub(node_separator,'',name.casefold()) if  name                                              else name
def clean_cmd (name:str): # convert command name to lowercase (don't remove _ since sublime uses those as seps)
  return                          name.casefold()  if (name and not (len(name) == 1 and name.isascii())) else name
def clean_path(name:str): # clean path segment by removing separators ␠⭾-_ but NOT . and converting to lowercase
  return re.sub(path_separator,'',name.casefold()) if  name                                              else name

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
  if _libckdl:
    from NeoVintageous.nv import cfg_parse_c as cfg_parse
  else:
    from NeoVintageous.nv import cfg_parse2  as cfg_parse
  _NVRC_KDL = cfg_parse.parse_kdl_doc('')

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
        if _libckdl:
          node_key = ckdl.Node(    None,      '≠',      [               line.rstrip() ])
        else:
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
    message('error detected while processing {} at line "{}":\n{}'.format('.neovintageousrc', line.rstrip(), str(e)))

  return None

CFG_CACHE = {"file":dict(), "data":dict()}
