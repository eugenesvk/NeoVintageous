from typing import Union

from NeoVintageous.nv.ex_cmds import do_ex_user_cmdline
from NeoVintageous.nv.mappings import Mapping
from NeoVintageous.nv.settings import get_action_count, get_mode, get_motion_count, get_partial_sequence, get_partial_text, get_register, get_sequence, set_action_count, set_motion_count, set_register
from NeoVintageous.nv.state import reset_command_data
from NeoVintageous.nv.modes import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE

import logging
from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL
_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)
if _log.hasHandlers(): # clear existing handlers, including sublime's
    logging.getLogger(__name__).handlers.clear()
    # _log.addHandler(stream_handler)
_L = True if _log.isEnabledFor(logging.KEY) else False

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


def _handle_rhs(win, rhs: str) -> None:
    if ':' in rhs: # hacky piece of code (needs refactoring) is to support mappings in the format of {seq}:{ex-cmd}<CR>{seq}, where leading and trailing sequences are optional, eg:
        #      :
        #      :w
        #      :sort  <CR>
        #   vi]:sort u<CR>
        #   vi]:sort u<CR>vi]y<Esc>

        colon_pos = rhs.find(':')
        leading   = rhs[:colon_pos ]
        rhs       = rhs[ colon_pos:]

        cr_pos = rhs.lower().find('<cr>')
        if cr_pos >= 0:
            command  = rhs[:cr_pos + 4 ]
            trailing = rhs[ cr_pos + 4:]
        else: # Example :reg
            command  = rhs
            trailing = ''

        if leading:
            win.run_command('nv_process_notation',{'keys':leading ,'check_user_mappings':False,})
        do_ex_user_cmdline(win, command)
        if trailing:
            win.run_command('nv_process_notation',{'keys':trailing,'check_user_mappings':False,})
    else:
        win    .run_command('nv_process_notation',{'keys':rhs     ,'check_user_mappings':False,})

from NeoVintageous.nv            	import plugin
from NeoVintageous.nv.vi         	import keys
from NeoVintageous.nv.vi.cmd_base	import CommandNotFound
from NeoVintageous.nv.mappings   	import mappings_resolve_text
def _handle_rhs_text(view, rhs: Union[str, list]) -> None: # find a key that is mapped to the same internal function as from text_command, and pass that key for later processing. Removes the need to repeat internal functions to handle text_commands
    win = view.window()
    mode = get_mode(view)
    for text_command in (text_commands := [rhs] if isinstance(rhs, str) else rhs):
        if text_command.startswith('"command"'):
            _log.debug(" redirect Sublime's text ‘\"command\"’ to _handle_rhs=%s",text_command)
            _handle_rhs(win, ':'+text_command)
        elif ':' in text_command:
            _log.debug(" redirect text command with ‘:’ command to _handle_rhs=%s",text_command)
            _handle_rhs(win,     text_command)
        else:
            command_txt = mappings_resolve_text(view, text_command=text_command, mode=mode, check_user_mappings=False)
            if isinstance(command_txt, CommandNotFound):
                _log.debug("  text_command ‘%s’not resolved",text_command)
                continue
            else:
                if mode in (mappings := plugin.mappings_reverse):
                    dict_cls_to_cmd = mappings[mode] # <...plugin_commentary.CommentaryMotion'>:'gc'
                    cmdT = type(command_txt)
                    if (seq := dict_cls_to_cmd.get(cmdT,None)):
                        _log.debug("command_txt matched to key ‘¦%s¦’ from plugin_dict's class ‘¦%s¦’"
                            ,                                    seq,                         cmdT)
                        win.run_command('nv_process_notation',{'keys':seq, 'check_user_mappings':False,})
                        continue
                if mode in (mappings := keys.mappings_reverse):
                    dict_cls_to_cmd = mappings[mode] # <...cmd_defs.ViUndo'>:'u'
                    cmdT = type(command_txt)
                    if (seq := dict_cls_to_cmd.get(cmdT,None)):
                        _log.debug("command_txt matched to key ‘¦%s¦’ from keys_dict's class ‘¦%s¦’"
                            ,                                    seq,                         cmdT)
                        win.run_command('nv_process_notation',{'keys':seq, 'check_user_mappings':False,})
                        continue
