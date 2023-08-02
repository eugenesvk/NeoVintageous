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
from NeoVintageous.nv.modes import Mode as M, text_to_modes, text_to_mode_alone
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

def reload_with_user_data() -> None:
    if hasattr(cfgU,'status') and (cfg := cfgU.status):
        global _MODES, _id_mode, _id_seq
        for _key in cfg: # 'insert'
            if type(_val := cfg[_key]) == str:
                if (modes := text_to_mode_alone(_key)):
                    _MODES[modes] = _val
        if (_key := 'id_mode') in cfg and type(_val := cfg[_key]) == str:
            _id_mode = _val
        if (_key := 'id_seq')  in cfg and type(_val := cfg[_key]) == str:
            _id_seq = _val


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


_id_mode = 'vim-mode'
_id_seq  = 'vim-seq'
def reset_status_line(view, mode: str) -> None:
    view.erase_status(_id_seq)
    if mode == NORMAL:
        view.set_status(_id_mode, _MODES[M.Normal])


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
