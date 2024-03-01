import os, sys, subprocess, logging
from pathlib import Path

import sublime

from NeoVintageous.nv.modes import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE
from NeoVintageous.nv.modes import M_EVENT, Mode as M, text_to_modes, mode_names_rev,mode_clean_names_rev
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
MESSAGE_TARGET = {'class':'AutoHotkey', 'name':'\\AutoHotkey.ahk', 'mid':'nv_a61171a06fc94216a3433cf83cd16e35'}
DEF['postmodemessage'] = MESSAGE_TARGET

import copy
CFG = copy.deepcopy(DEF) # copy defaults to be able to reset values on config reload

def reload_with_user_data_kdl() -> None:
  if hasattr(cfgU,'kdl') and (cfg := cfgU.kdl.get('event',None)): # skip on initial import when Plugin API isn't ready, so no settings are loaded
    global CFG
    for node in cfg.nodes: # (ⓘ)in {(mac)"~/bin" "--var" r#"{"v":1}"#;} or post_mode_message class="AutoHotkey" name="AutoHotkey.ahk"
      if (cfg_key:=node.name) == 'postmodemessage':
        for (key,tag_val) in node.props.items(): # 1. class='AutoHotkey' name='AutoHotkey.ahk' pairs
          key = clean_name(key)
          if hasattr(tag_val,'value'): #class=(t)‘AutoHotkey’ if (t) exists (though shouldn't)
            val = tag_val.value # ignore tag
            _log.warn("node ‘%s’ has unrecognized tag  property ‘%s=%s’"
              ,       node.name,                              key,tag_val)
          else:
            val = tag_val
          if key in MESSAGE_TARGET.keys():
            if val == None:
              CFG[cfg_key].pop(key,None)
            else:
              CFG[cfg_key][key] = val # AutoHotkey
            _log.debug('CFG set to prop @%s %s=%s'
              ,                   cfg_key,key,val)
          else:
            _log.warn("node ‘%s’ has unrecognized key in ‘%s=%s’ property, expecting one of: null %s"
              ,       node.name,                         key,tag_val,' '.join(MESSAGE_TARGET.keys()))
        continue

      # 2. (ⓘ)in {(mac)"~/bin" "--var" r#"{"v":1}"#;}
      mode = mode_clean_names_rev.get(clean_name(node.tag ),None) # ‘Mode.Insert’ for ‘ⓘ’
      evt  = EVENTrev            .get(clean_name(node.name),None) # ‘enter’       for ‘in’
      if not mode or\
         not mode in M.Event:
        _log.error("node ‘%s’ has no/unrecognized mode in tag ‘(%s)%s’, skipping (expecting one of %s)"
          ,            cfg.name,                          node.tag,node.name, ' '.join(list(mode_clean_names_rev.keys())))
        continue
      if not evt  in EVENT:
        _log.error("node ‘%s’ has unrecognized event in name ‘(%s)%s’, skipping"
          ,            cfg.name,                       node.tag,node.name)
        continue
      # 1. Parse node arguments:  (os)exe arg;
      cmf_full = None
      exe = None
      for i,arg in enumerate(node.args):
        tag_os = arg.tag   if hasattr(arg,'tag'  ) else ''
        val    = arg.value if hasattr(arg,'value') else arg
        if i == 0: # check the os tag in the first argument
          if tag_os:
            exe = val
            if not (os := OSrev.get(tag_os,None)):
              _log.error("node ‘%s’ has unrecognized OS tag ‘%s’ in ‘%s’, skipping"
                ,               cfg.name,                    os,     arg)
              break # stop parsing arguments
          else:
            _log.error("node ‘%s’ has no OS tag in ‘%s’, skipping"
              ,               cfg.name,             arg)
            break # stop parsing arguments
          cmf_full  = [val] # start a new command
        else:
          cmf_full += [val] # append argument to command
      if node.props.get('internal',False):
        if (internal_func := CMD_INTERNAL.get(clean_name(exe),None)):
          cmf_full = internal_func
        else:
          cmf_full = None
          _log.error("Unrecognized internal command ‘%s’, expected case/separator insensitive ‘%s’", exe, CMD_INTERNAL.keys())
      if  cmf_full:
        CFG[os][mode][evt].append(cmf_full) # append full command to the list as a list or func
        _log.debug("added a command from args to ‘%s’‘%s’‘%s’ = ‘%s’"
          ,                                      os,mode,evt,   cmf_full)
      # 2. Parse node children : {(os)exe arg;}
      for node_cmd in node.nodes:
        cmf_full = None
        tag_os = node_cmd.tag  if hasattr(node_cmd,'tag' ) else ''
        exe    = node_cmd.name
        if tag_os:
          if (os := OSrev.get(tag_os,None)):
            cmf_full = [exe] # start a new command
          else:
            _log.error("node ‘%s’ has unrecognized OS tag ‘%s’ in ‘%s’, skipping"
              ,               cfg.name,                    os,      exe)
            continue # skip to another node
        else:
          _log.error("node ‘%s’ has no OS tag in ‘%s’, skipping"
            ,               cfg.name,             exe)
          continue # skip to another node
        for i,arg in enumerate(node_cmd.args):
          tag = arg.tag   if hasattr(arg,'tag'  ) else ''
          val = arg.value if hasattr(arg,'value') else arg
          if tag:
            _log.warn("node ‘%s’ has unrecognized tag ‘%s’ in argument ‘%s’, ignoring"
              ,            cfg.name,                   tag,             val)
          cmf_full  += [val] # append argument to command
        if node_cmd.props.get('internal',False):
          if (internal_func := CMD_INTERNAL.get(clean_name(exe),None)):
            cmf_full = internal_func
          else:
            cmf_full = None
            _log.error("Unrecognized internal command ‘%s’, expected case/separator insensitive ‘%s’", exe, CMD_INTERNAL.keys())
        if  cmf_full:
          CFG[os][mode][evt].append(cmf_full) # append full command to the list as a list or func
          _log.debug("added a command from child to ‘%s’‘%s’‘%s’ = ‘%s’"
          ,                                      os,mode,evt,   cmf_full)

  else: # reset config to defaults
    CFG = copy.deepcopy(DEF)

def get_full_cmd(os,mode,evt) -> list:
  if     os   in CFG          :
    if   mode in CFG[os]      :
      if evt  in CFG[os][mode]:
        return   CFG[os][mode][evt]

def execute_mode_change_cmd(view, current_mode, new_mode, mode_old, mode_new) -> None:
  if (cmd_l := get_full_cmd(PLATFORM,mode_old,'leave')):
    for full_cmd in cmd_l:
      if callable(full_cmd):
        full_cmd   (          mode_old    , mode_new)
      else:
        run_command(full_cmd, current_mode, new_mode)
  if (cmd_l := get_full_cmd(PLATFORM,mode_new,'enter')):
    for full_cmd in cmd_l:
      if callable(full_cmd):
        full_cmd   (          mode_old    , mode_new)
      else:
        run_command(full_cmd, current_mode, new_mode)

def on_mode_change  (view   , current_mode, new_mode) -> None:
  _log.debug("mode Δ %s ⟶ %s"
    ,      current_mode  ,  new_mode)
  if current_mode == INTERNAL_NORMAL:
    mode_old = mode_names_rev.get(NORMAL      , None)
  else:
    mode_old = mode_names_rev.get(current_mode, None)
  if new_mode     == INTERNAL_NORMAL:
    mode_new = mode_names_rev.get(NORMAL      , None)
  elif new_mode   == M.Empty: # e.g., moving to a console panel, signal it's not vim's mode
    mode_new = new_mode
  else:
    mode_new = mode_names_rev.get(new_mode    , None)
  if mode_old is None and mode_new is None:
    _log.error("mode Δ: couldn't match both mode names to modes (‘%s’|%s to ‘%s’|%s)"
      ,                                                current_mode,mode_old, new_mode,mode_new)
    return
  if mode_new == M.Empty: # "leave" all modes since this is not vim's view
    for m_old in M_ANY:
      execute_mode_change_cmd(view, current_mode, new_mode,    m_old, mode_new)
  else:
    execute_mode_change_cmd  (view, current_mode, new_mode, mode_old, mode_new)

def run_command    (full_cmd, current_mode, new_mode) -> None:
  _log.debug("full_cmd = ‘%s’",full_cmd)
  if (bin_path := Path(full_cmd[0]).expanduser()).exists():
    proc  = subprocess.run([bin_path] + full_cmd[1:],capture_output=True)
    out   = proc.stdout.decode().rstrip('\n')
    err   = proc.stderr.decode().rstrip('\n')
    retn  = proc.returncode
    if err:
      _log.error("Δ mode ‘%s’ ⟶ ‘%s’\n and running ‘%s’\n%s"
          ,     current_mode,new_mode,        full_cmd  ,err)
  else:
    _log.error("Δ mode ‘%s’ ⟶ ‘%s,’\n executable does NOT exist: ‘%s’"
        ,     current_mode,new_mode,                             bin_path)


if sys.platform.startswith('win') and PLATFORM == 'windows':
  try:
    import Pywin32.setup
    from win32com.client.gencache import EnsureDispatch
    import win32con
    import win32gui
    _pywin = True
  except ImportError:
    _pywin = False
  except ModuleNotFoundError:
    _pywin = False

  import ctypes
  dll     = ctypes.windll
  LPWSTR  = ctypes.c_wchar_p
  UINT    = ctypes.c_uint
  def RaiseIfZero(result, func = None, arguments = ()):
    """Error checking for most Win32 API calls. Function is assumed to return an integer, which is C{0} on error.In that case the C{WindowsError} exception is raised"""
    if not result:
      raise ctypes.WinError()
    return result
  def RegisterWindowMessage(lpString): # UINT RegisterWindowMessageW([in] LPCWSTR lpString);
    f           = dll.user32.RegisterWindowMessageW
    f.argtypes  = [LPWSTR]
    f.restype   = UINT
    f.errcheck  = RaiseIfZero
    return f(lpString)
  ahkIDs = set()
  def cb_collect_winIDs(id, _):
    """Collect window IDs with the specified class name"""
    if not CFG['postmodemessage']['class'].lower() == win32gui.GetClassName (id).lower():
      return
    if not CFG['postmodemessage']['name' ].lower() in win32gui.GetWindowText(id).lower():
      return
    ahkIDs.add(id)

  from NeoVintageous.nv.modes import M_EVENT, M_ANY, Mode as M, text_to_modes, mode_names_rev,mode_clean_names_rev
  def post_mode_message(old, new):
    if not _pywin:
      _log.error("‘PyWin32’ module couldn't be loaded, so can't send any messages!")
      return
    if (old and not isinstance(old,M)) or (new and not isinstance(new,M)):
      _log.error("Mode change message parameters must be of type ‘Mode’, not old=‘%s’ new=‘%s’",type(old),type(new))
      return
    if not (msgID := RegisterWindowMessage(CFG['postmodemessage']['mid'])):
      _log.error("Couldn't register Window Message %s", CFG['postmodemessage']['mid'])
      return
    if not old:
      old = M(0)
    if not new:
      new = M(0)

    import copy
    for ahkID in copy.deepcopy(ahkIDs): # check if window exists before running enum eveyr time, no need to waste
      if not win32gui.IsWindow(ahkID):
        ahkIDs.remove(ahkID)
    if not ahkIDs:
      win32gui.EnumWindows(cb_collect_winIDs, None) # Enumerate all windows and collect those with the specified class name/text
    if not ahkIDs:
      _log.warn("Couldn't find any window of class ‘%s’, containing ‘%s’ in its name"
        ,            CFG['postmodemessage']['class'],   CFG['postmodemessage']['name'])
    for wID in ahkIDs:
      try:
        win32gui.PostMessage(wID, msgID, old+0, new+0) # old=wparam new=lparam
      except Exception as e:
        _log.error("Failed to post a mode change message to winID ‘%s’ due to error %s", wID, e)
else:
  def post_mode_message(old, new):
    return
CMD_INTERNAL = {'postmodemessage':post_mode_message}
