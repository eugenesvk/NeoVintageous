# Copyright (C) 2018-2023 The NeoVintageous Team (NeoVintageous).
#
# This file is part of NeoVintageous.
#
# NeoVintageous is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# NeoVintageous is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NeoVintageous.  If not, see <https://www.gnu.org/licenses/>.

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
    M.V              	: 'Ⓥ',
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
}
import copy
DEF_R = copy.deepcopy(DEF) # save original defaults to reset statuses with old IDs
DEF_R['update_idmode'] = False
DEF_R['update_idseq']  = False
DEFM = dict()
for m in mode_names: # Mode.N enum variants
    DEFM[m] = None

def reload_with_user_data_kdl() -> None:
    if hasattr(cfgU,'kdl') and (cfg := cfgU.kdl.get('status',None)): # skip on initial import when Plugin API isn't ready, so no settings are loaded
        global DEF, DEFM
        _log.debug(f"@nv.vim: Parsing config status")
        for cfg_key in DEF: # 1a. parse arguments for non-mode statuses
            if (node := cfg.get(cfg_key,None)): # id_seq "vim-seq" node/arg pair
                if (args := node.args):
                    tag_val = args[0] #(t)"vim-seq" if (t) exists (though shouldn't)
                    # val = tag_val.value if hasattr(tag_val,'value') else tag_val # ignore tag
                    if hasattr(tag_val,'value'):
                        val = tag_val.value # ignore tag
                        _log.warn(f"node ‘{node.name}’ has unrecognized tag in argument ‘{tag_val}’")
                    else:
                        val = tag_val
                    DEF[node.name] = val
                    #print(f"status from argument ‘{node.name}’ is ‘{tag_val}’")
                elif not args:
                    _log.warn(f"node ‘{cfg_key}’ is missing arguments in its child ‘{node.name}’")
                if len(args) > 1:
                    _log.warn(f"node ‘{cfg_key}’ has extra arguments in its child ‘{node.name}’, only the 1st was used ‘{', '.join(args)}’")
        for node in cfg.nodes: # 1b. parse arguments for mode statuses
            for arg in node.args:
                tag_val = arg #(t)"vim-seq" if (t) exists (though shouldn't)
                # val = tag_val.value if hasattr(tag_val,'value') else tag_val # ignore tag
                if hasattr(tag_val,'value'):
                    val = tag_val.value # ignore tag
                    _log.warn(f"node ‘{node.name}’ has unrecognized tag in argument ‘{tag_val}’")
                else:
                    val = tag_val
                if (mode := mode_names_rev.get(node.name        ,\
                            mode_names_rev.get(node.name.upper(),None))): # kdl keys are converted to lowercase, so check 'i' and 'I'
                    DEFM[mode] = val
                    # print(f"status mode DEFM ‘{mode}’ from ‘{node.name}’ argument ‘{val}’")
        for i,key in enumerate(prop_d := node.props): # 2. parse properties id_seq="vim-seq", alternative notation to child node/arg pairs
            tag_val = prop_d[key] #(t)"vim-seq" if (t) exists (though shouldn't)
            # val = tag_val.value if hasattr(tag_val,'value') else tag_val # ignore tag
            if hasattr(tag_val,'value'):
                val = tag_val.value # ignore tag
                _log.warn(f"node ‘{node.name}’ has unrecognized tag in property ‘{key}={tag_val}’")
            else:
                val = tag_val
            if key in DEF: # 2a. for non-mode statuses
                DEF[key] = val
                #print(f"status from property ‘{key}={val}’")
            elif key in mode_names_rev: # 2b. for mode statuses
                mode = mode_names_rev[key]
                DEFM[mode] = val
                # print(f"status mode DEFM from property ‘{key}={val}’")
            else:
                _log.error(f"node ‘{node.name}’ has unrecognized property ‘{key}={tag_val}’")
# def reload_with_user_data() -> None:
#     if hasattr(cfgU,'status') and (cfg := cfgU.status):
#         global _MODES, _id_mode, _id_seq
#         for _key in cfg: # 'insert'
#             if type(_val := cfg[_key]) == str:
#                 if (modes := text_to_mode_alone(_key)):
#                     _MODES[modes] = _val
#         if (_key := 'id_mode') in cfg and type(_val := cfg[_key]) == str:
#             _id_mode = _val
#         if (_key := 'id_seq')  in cfg and type(_val := cfg[_key]) == str:
#             _id_seq = _val


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
    view.erase_status(DEF['idseq'])
    if mode == NORMAL:
        view.set_status(DEF['idmode'], _MODES[M.Normal])


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


def clean_view(view) -> None:

    # Reset mode, caret, state, etc. In the case of plugin errors this clean
    # routine prevents the normal functioning of editor becoming unusable e.g.
    # the cursor getting stuck in a block shape or the mode getting stuck.

    try:
        settings = view.settings()

        if settings.has('command_mode'):
            settings.erase('command_mode')

        if settings.has('inverse_caret_state'):
            settings.erase('inverse_caret_state')

        if settings.has('vintage'):
            settings.erase('vintage')

    except Exception:  # pragma: no cover
        traceback.print_exc()
