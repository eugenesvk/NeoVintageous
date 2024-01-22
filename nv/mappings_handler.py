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

from typing import Union

from NeoVintageous.nv.ex_cmds import do_ex_user_cmdline
from NeoVintageous.nv.mappings import Mapping
from NeoVintageous.nv.settings import get_action_count
from NeoVintageous.nv.settings import get_mode
from NeoVintageous.nv.settings import get_motion_count
from NeoVintageous.nv.settings import get_partial_sequence, get_partial_text
from NeoVintageous.nv.settings import get_register
from NeoVintageous.nv.settings import get_sequence
from NeoVintageous.nv.settings import set_action_count
from NeoVintageous.nv.settings import set_motion_count
from NeoVintageous.nv.settings import set_register
from NeoVintageous.nv.state import reset_command_data
from NeoVintageous.nv.modes import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE

import logging
from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL
_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)

def evaluate_mapping(view, mapping: Mapping) -> None:
    # TODO Review Why does rhs of mapping need to be resequenced in OPERATOR PENDING mode?
    rhs = mapping.rhs
    if get_mode(view) == OPERATOR_PENDING:
        rhs = get_sequence(view)[:-len(get_partial_sequence(view))] + mapping.rhs

    # TODO Review Why does state need to be reset before running user mapping?
    reg = get_register(view)
    acount = get_action_count(view)
    mcount = get_motion_count(view)
    reset_command_data(view)
    set_register(view, reg)
    set_motion_count(view, mcount)
    set_action_count(view, acount)

    _handle_rhs(view.window(), rhs)

def evaluate_mapping_text(view, mapping: Mapping) -> None:
    # TODO Review Why does rhs of mapping need to be resequenced in OPERATOR PENDING mode?
    rhs = mapping.rhs
    # if get_mode(view) == OPERATOR_PENDING:
    #     rhs = get_sequence(view)[:-len(get_partial_text(view))] + mapping.rhs

    # TODO Review Why does state need to be reset before running user mapping?
    reg = get_register(view)
    acount = get_action_count(view)
    mcount = get_motion_count(view)
    reset_command_data(view)
    set_register(view, reg)
    set_motion_count(view, mcount)
    set_action_count(view, acount)

    _handle_rhs_text(view, rhs)


def _handle_rhs(window, rhs: str) -> None:
    if ':' in rhs:
        # This hacky piece of code (needs refactoring), is to
        # support mappings in the format of {seq}:{ex-cmd}<CR>{seq},
        # where leading and trailing sequences are optional.
        #
        # Examples:
        #
        #   :
        #   :w
        #   :sort<CR>
        #   vi]:sort u<CR>
        #   vi]:sort u<CR>vi]y<Esc>

        colon_pos = rhs.find(':')
        leading = rhs[:colon_pos]
        rhs = rhs[colon_pos:]

        cr_pos = rhs.lower().find('<cr>')
        if cr_pos >= 0:
            command = rhs[:cr_pos + 4]
            trailing = rhs[cr_pos + 4:]
        else:
            # Example :reg
            command = rhs
            trailing = ''

        if leading:
            window.run_command('nv_process_notation', {
                'keys': leading,
                'check_user_mappings': False,
            })

        do_ex_user_cmdline(window, command)

        if trailing:
            window.run_command('nv_process_notation', {
                'keys': trailing,
                'check_user_mappings': False,
            })

    else:
        window.run_command('nv_process_notation', {
            'keys': rhs,
            'check_user_mappings': False,
        })

from NeoVintageous.nv.vi.cmd_base import CommandNotFound
from NeoVintageous.nv         	import plugin
from NeoVintageous.nv.vi      	import keys
from NeoVintageous.nv.mappings	import mappings_resolve_text
def _handle_rhs_text(view, rhs: Union[str, list]) -> None: # find a key that is mapped to the same internal function as from text_command, and pass that key for later processing. Removes the need to repeat internal functions to handle text_commands
    win = view.window()
    mode = get_mode(view)
    for text_command in (text_commands := [rhs] if isinstance(rhs, str) else rhs):
        if ':' in text_command:
            _log.debug(" redirect text command with ‘:’ command to _handle_rhs=%s",text_command)
            _handle_rhs(win, text_command)
        else:
            command_txt = mappings_resolve_text(view, text_commands=text_command, mode=mode, check_user_mappings=False)
            if isinstance(command_txt, CommandNotFound):
                _log.debug("  text_command ‘%s’not resolved",text_command)
                continue
            else:
                if mode in (mappings := plugin.mappings_reverse):
                    dict_cls_to_cmd = mappings[mode]
                    for clsT,seq in dict_cls_to_cmd.items():
                        if clsT == type(command_txt):
                            _log.debug("command_txt matched to key ‘¦%s¦’ from plugin_dict's class ‘¦%s¦’"
                                ,                                    seq,                         clsT)
                            win.run_command('nv_process_notation',{'keys':seq, 'check_user_mappings':False,})
                            break
                if mode in (mappings := keys.mappings_reverse):
                    dict_cls_to_cmd = mappings[mode]
                    value_prev = None
                    for clsT,seq in dict_cls_to_cmd.items():
                        if clsT == type(command_txt):
                            _log.debug("command_txt matched to key ‘¦%s¦’ from keys_dict's class ‘¦%s¦’"
                                ,                                    seq,                         clsT)
                            win.run_command('nv_process_notation',{'keys':seq, 'check_user_mappings':False,})
                            break
