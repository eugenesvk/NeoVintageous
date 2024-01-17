import os
import subprocess
import logging

from pathlib import Path

import sublime

from NeoVintageous.nv.modes import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE
from NeoVintageous.nv.modes import M_EVENT, Mode as M, text_to_modes, mode_names_rev
from NeoVintageous.nv.rc import cfgU
from NeoVintageous.nv.cfg_parse import clean_name

__all__ = ['NeoVintageousEventsUser'] # User events: run cli commands on mode changes

PLATFORM = sublime.platform() # osx linux windows
from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL
_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)

OS = {  # alternative OS names
  'osx'    	: ['⌘','','🍏','m','mac','osx','macos'],
  'linux'  	: ['🐧'        ,'l','lin','linux'],
  'windows'	: ['⊞','🗔','🪟','w','win','windows'],
}
OSrev = dict() # ⌘ → osx
for name,names_alt in OS.items():
  for name_alt in names_alt:
    OSrev[clean_name(name_alt)] = name
EVENT = { # alternative event names
  'enter'	: ['in','enter'],
  'leave'	: ['out','exit','leave']
}
EVENTrev = dict() # enter → in
for name,names_alt in EVENT.items():
  for name_alt in names_alt:
    EVENTrev[clean_name(name_alt)] = name

DEF = dict()
for       os in OS:
  DEF    [os]            = dict()
  for         mode in M_EVENT:
    DEF  [os][mode]      = dict()
    for             evt in EVENT:
      DEF[os][mode][evt] = [] # empty list of command

def reload_with_user_data_kdl() -> None:
  if hasattr(cfgU,'kdl') and (cfg := cfgU.kdl.get('event',None)): # skip on initial import when Plugin API isn't ready, so no settings are loaded
    global DEF
    for node in cfg.nodes: # (ⓘ)in {(mac)"~/bin" "--var" r#"{"v":1}"#;}
      mode = mode_names_rev.get(clean_name(node.tag ),None) # ‘Mode.Insert’ for ‘ⓘ’
      evt  = EVENTrev      .get(clean_name(node.name),None) # ‘enter’       for ‘in’
      if not mode in M.Event:
        _log.error(f"node ‘{cfg.name}’ has unrecognized mode in tag ‘({node.tag}){node.name}’, skipping")
        continue
      if not evt  in EVENT:
        _log.error(f"node ‘{cfg.name}’ has unrecognized event in name ‘({node.tag}){node.name}’, skipping")
        continue
      # 1. Parse node arguments:  (os)exe arg;
      cmf_full = None
      for i,arg in enumerate(node.args):
        tag_os = arg.tag   if hasattr(arg,'tag'  ) else ''
        val    = arg.value if hasattr(arg,'value') else arg
        if i == 0: # check the os tag in the first argument
          if tag_os:
            if not (os := OSrev.get(tag_os,None)):
              _log.error(f"node ‘{cfg.name}’ has unrecognized OS tag ‘{os}’ in ‘{arg}’, skipping")
              break # stop parsing arguments
          else:
            _log.error(f"node ‘{cfg.name}’ has no OS tag in ‘{arg}’, skipping")
            break # stop parsing arguments
          cmf_full  = [val] # start a new command
        else:
          cmf_full += [val] # append argument to command
      if  cmf_full:
        DEF[os][mode][evt] += [cmf_full] # append full command to the list as a list
        _log.debug(f"added a command from args to ‘{os}’‘{mode}’‘{evt}’ = ‘{cmf_full}’")
      # 2. Parse node children : {(os)exe arg;}
      for node_cmd in node.nodes:
        cmf_full = None
        tag_os = node_cmd.tag  if hasattr(node_cmd,'tag' ) else ''
        exe    = node_cmd.name
        if tag_os:
          if (os := OSrev.get(tag_os,None)):
            cmf_full = [exe] # start a new command
          else:
            _log.error(f"node ‘{cfg.name}’ has unrecognized OS tag ‘{os}’ in ‘{exe}’, skipping")
            continue # skip to another node
        else:
          _log.error(f"node ‘{cfg.name}’ has no OS tag in ‘{exe}’, skipping")
          continue # skip to another node
        for i,arg in enumerate(node_cmd.args):
          tag = arg.tag   if hasattr(arg,'tag'  ) else ''
          val = arg.value if hasattr(arg,'value') else arg
          if tag:
            _log.warn(f"node ‘{cfg.name}’ has unrecognized tag ‘{tag}’ in argument ‘{val}’, ignoring")
          cmf_full  += [val] # append argument to command
        if  cmf_full:
          DEF[os][mode][evt] += [cmf_full] # append full command to the list as a list
          _log.debug(f"added a command from child to ‘{os}’‘{mode}’‘{evt}’ = ‘{cmf_full}’")

def get_full_cmd(os,mode,evt) -> list:
  if     os   in DEF          :
    if   mode in DEF[os]      :
      if evt  in DEF[os][mode]:
        return   DEF[os][mode][evt]

def on_mode_change  (view   , current_mode, new_mode) -> None:
  _log.debug(f"mode Δ {current_mode} ⟶ {new_mode}")
  mode_old = mode_names_rev.get(current_mode,None)
  mode_new = mode_names_rev.get(new_mode    ,None)
  if not (mode_old or mode_new):
    _log.error(f"mode Δ: couldn't match both mode names to modes (‘{current_mode}’|{mode_old} to ‘{new_mode}’|{mode_new})")
    return
  if (cmd_l := get_full_cmd(PLATFORM,mode_old,'leave')):
    for full_cmd in cmd_l:
      run_command(full_cmd, current_mode, new_mode)
  if (cmd_l := get_full_cmd(PLATFORM,mode_new,'enter')):
    for full_cmd in cmd_l:
      run_command(full_cmd, current_mode, new_mode)

def run_command    (full_cmd, current_mode, new_mode) -> None:
  _log.debug(f"full_cmd = {full_cmd}")
  if (bin_path := Path(full_cmd[0]).expanduser()).exists():
    proc  = subprocess.run([bin_path] + full_cmd[1:],capture_output=True)
    out   = proc.stdout.decode().rstrip('\n')
    err   = proc.stderr.decode().rstrip('\n')
    retn  = proc.returncode
    if err:
      _log.ERROR(f"Δ mode ‘{current_mode}’ ⟶ ‘{new_mode}’\n and running ‘{full_cmd}’\n{err}")
  else:
    _log.ERROR(f"Δ mode ‘{current_mode}’ ⟶ ‘{new_mode},’\n executable does NOT exist: ‘{bin_path}’")
