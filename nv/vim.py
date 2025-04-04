import logging
import traceback

from sublime import windows as _windows

from NeoVintageous.nv.polyfill import status_message as _status_message
from NeoVintageous.nv.rc import cfgU

from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL
_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)

# NeoVintageous always runs actions based on selections. Some Vim commands,
# however, behave differently depending on whether the current mode is NORMAL or
# VISUAL. To differentiate NORMAL mode operations (involving only an action, or
# a motion plus an action) from VISUAL mode, we need to add an additional mode
# for handling selections that won't interfere with the actual VISUAL mode. This
# is INTERNAL_NORMAL's job. INTERNAL_NORMAL is a pseudomode, because global
# state's .mode property should never set to it, yet it's set in vi_cmd_data
# often. Note that for pure motions we still use plain NORMAL mode.
from NeoVintageous.nv.modes import Mode as M, text_to_modes, text_to_mode_alone, mode_names, mode_names_rev
from NeoVintageous.nv.modes import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE

ACTION_MODES = (NORMAL, VISUAL, VISUAL_LINE, VISUAL_BLOCK)
MOTION_MODES = (NORMAL, OPERATOR_PENDING, VISUAL, VISUAL_LINE, VISUAL_BLOCK)

DIRECTION_UP = 1
DIRECTION_DOWN = 2

EOF = '\x00'
NL = '\n'

_MODES = {
    M.Insert         	: 'ⓘ',
    M.InternalNormal 	: '',
    M.Normal         	: 'Ⓝ',
    M.OperatorPending	: 'Ⓞ',
    M.VV             	: 'Ⓥ',
    M.Visual         	: 'Ⓥ',
    M.VisualBlock    	: 'Ⓥ▋',
    M.VisualLine     	: 'Ⓥ━',
    M.Unknown        	: '❓',
    M.Replace        	: 'Ⓡ',
    M.Select         	: 'Ⓢ',
}

_MODE2CHAR = {
    INSERT: 'i',
    NORMAL: 'n',
    SELECT: 's',
    VISUAL: 'v',
    VISUAL_LINE: 'V',  # Sometimes "l" in code e.g. case-insensitive situations.
    VISUAL_BLOCK: 'b',
}
DEF = {
    'prefix' : '',
    'suffix' : '',
    'idmode' : 'vim-mode',
    'idseq'  : 'vim-seq',
    'statepopup'  : False,
}
DEFM = dict()
for m in mode_names: # Mode.N enum variants
    DEFM[m] = None
import copy
CFG  = copy.deepcopy(DEF) # copy defaults to be able to reset values on config reload
CFGM = copy.deepcopy(DEFM)

def reload_with_user_data_kdl() -> None:
    global CFG, CFGM
    if hasattr(cfgU,'kdl'): # skip on initial import when Plugin API isn't ready, so no settings are loaded
        from NeoVintageous.nv.state import CFG as SCFG
        CFG['statepopup'] = SCFG['enable']

    if hasattr(cfgU,'kdl') and (cfg := cfgU.kdl.get('status',None)): # skip on initial import when Plugin API isn't ready, so no settings are loaded
        _log.debug("@nv.vim: Parsing config status")
        for cfg_key in CFG: # 1a. parse arguments for non-mode statuses
            if (node := cfgU.cfg_parse.node_get(cfg,cfg_key,None)): # id_seq "vim-seq" node/arg pair
                args = False
                for i,(arg,tag,val) in enumerate(cfgU.cfg_parse.arg_tag_val(node)):
                    args = True
                    if i == 0:
                        if tag:
                            _log.warn("node ‘%s’ has unrecognized tag in argument ‘%s’",node.name,arg)
                        CFG[node.name] = val #;_log.debug('indicator key_help from arg @%s %s',node.name,val)
                    elif i > 0:
                        _log.warn("node ‘%s’ has extra arguments in its child ‘%s’ (only the 1st was used): ‘%s’...",cfg_key,node.name,arg)
                        break
                if not args:
                    _log.warn("node ‘%s’ is missing arguments in its child ‘%s’"
                        ,         cfg_key,                               node.name)
        for node in cfgU.cfg_parse.children(cfg): # 1b. parse arguments for mode statuses
            for (arg,tag,val) in cfgU.cfg_parse.arg_tag_val(node):
                if tag:
                    _log.warn("node ‘%s’ has unrecognized tag in argument ‘%s’",node.name,arg)
                if (mode := mode_names_rev.get(node.name        ,\
                            mode_names_rev.get(node.name.upper(),None))): # kdl keys are converted to lowercase, so check 'i' and 'I'
                    CFGM[mode] = val ;_log.debug("status mode CFGM ‘%s’ from ‘%s’ argument ‘%s’",mode,node.name,val)
        node = cfg
        for i,(key,tag_val,tag,val) in enumerate(cfgU.cfg_parse.prop_key_tag_val(node)): # 2. parse properties id_seq="vim-seq", alternative notation to child node/arg pairs
            if tag:
                _log.warn("node ‘%s’ has unrecognized tag in property ‘%s=%s’",node.name,key,tag_val)
            if key in CFG: # 2a. for non-mode statuses
                CFG[key] = val ;_log.debug("status from property ‘%s=%s’",key,val)
            elif key in mode_names_rev: # 2b. for mode statuses
                mode = mode_names_rev[key]
                CFGM[mode] = val ;_log.debug("status mode CFGM from property ‘%s=%s’",key,val)
            else:
                _log.error("node ‘%s’ has unrecognized property ‘%s=%s’",node.name,key,tag_val)
    else:
        CFG = copy.deepcopy(DEF) # copy defaults to be able to reset values on config reload


def mode_to_name(mode: str) -> str:
    mode_enum = text_to_modes(mode)
    try:
        return _MODES[mode_enum]
    except KeyError:
        return '❔'


def mode_to_char(mode: str) -> str:
    try:
        return _MODE2CHAR[mode]
    except KeyError:
        return ''


def reset_status_line(view, mode: str) -> None:
    view.erase_status(CFG['idseq'])
    if mode == NORMAL:
        view.set_status(CFG['idmode'], _MODES[M.Normal])
    if CFG['statepopup'] and view.is_popup_visible():
        view.hide_popup()


def is_visual_mode(mode: str) -> bool:
    return mode in (VISUAL, VISUAL_LINE, VISUAL_BLOCK)


def is_ex_mode(view) -> bool:
    return view.settings().get('_nv_ex_mode')


def message(msg: str, *args: str) -> None:
    _status_message('NeoVintageous: ' + msg, *args)


def status_message(msg: str, *args: str) -> None:
    _status_message(msg, *args)


def run_motion(instance, motion: dict) -> None:
    instance.run_command(motion['motion'], motion['motion_args'])


def run_action(instance, action: dict) -> None:
    instance.run_command(action['action'], action['action_args'])


def enter_normal_mode(view_or_window, mode: str = None) -> None:
    view_or_window.run_command('nv_enter_normal_mode', {'mode': mode})


def enter_insert_mode(view_or_window, mode: str) -> None:
    view_or_window.run_command('nv_enter_insert_mode', {'mode': mode})


def enter_visual_mode(view_or_window, mode: str, force: bool = False) -> None:
    view_or_window.run_command('nv_enter_visual_mode', {'mode': mode})


def enter_visual_line_mode(view_or_window, mode: str, force: bool = False) -> None:
    view_or_window.run_command('nv_enter_visual_line_mode', {'mode': mode})


def enter_visual_block_mode(view_or_window, mode: str, force: bool = False) -> None:
    view_or_window.run_command('nv_enter_visual_block_mode', {'mode': mode})


def clean_views() -> None:
    for window in _windows():
        for view in window.views():
            clean_view(view)

def clean_view(view) -> None: # Reset mode, caret, state, etc. In the case of plugin errors this clean routine prevents the normal functioning of editor becoming unusable e.g. the cursor getting stuck in a block shape or the mode getting stuck
    try:
        settings = view.settings()
        for cfg in ['command_mode','inverse_caret_state','vintage']:
            if  settings.has  (cfg):
                settings.erase(cfg)
    except Exception:  # pragma: no cover
        traceback.print_exc()
