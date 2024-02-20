from typing import Union

from NeoVintageous.nv.ex_cmds import do_ex_user_cmdline
from NeoVintageous.nv.mappings import Mapping
from NeoVintageous.nv.settings import get_action_count, get_mode, get_motion_count, get_partial_sequence, get_text, get_partial_text, get_register, get_sequence, set_action_count, set_motion_count, set_register
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
    rhs = mapping.rhs
    if (m_txt := get_mode(view) == OPERATOR_PENDING):
        rhs = get_sequence(view)[:-len(get_partial_sequence(view))] + mapping.rhs
    _log.key(' evalMap ‹‘%s’=‘%s’←‘%s’› m%s'
        ,mapping.lhs
        ,('Ⓞ'        if m_txt == OPERATOR_PENDING else '') + rhs
        ,mapping.rhs if m_txt == OPERATOR_PENDING else '_'
        ,m_txt)

    reg    = get_register    (view)
    acount = get_action_count(view)
    mcount = get_motion_count(view)
    reset_command_data       (view) # Resets temp data to build a (partial)command
    set_register             (view, reg   )
    set_motion_count         (view, mcount)
    set_action_count         (view, acount)

    _handle_rhs(view.window(), rhs)
    # _log.key(" evalMap m%s end", get_mode(view))

def evaluate_mapping_text(view, mapping: Mapping) -> None:
    rhs = [mapping.rhs] if isinstance(mapping.rhs, str) else mapping.rhs
    if ((m_txt := get_mode(view)) == OPERATOR_PENDING):
        txt  = get_text        (view) # [openregister  2  copychar]
        txtP = get_partial_text(view) # [f]
        for el in reversed(txtP):
            if el == txt[-1]:
                del  txt[-1]
        rhs = txt + mapping.rhs
    _log.key(' evalMapT ‹‘%s’=%s‘%s’←‘%s’› m%s'
        ,mapping.lhs
        ,('Ⓞ'        if m_txt == OPERATOR_PENDING else '')
        ,rhs
        ,mapping.rhs if m_txt == OPERATOR_PENDING else '_'
        ,m_txt)

    reg    = get_register    (view)
    acount = get_action_count(view)
    mcount = get_motion_count(view)
    reset_command_data       (view) # Resets temp data to build a (partial)command
    set_register             (view, reg   )
    set_motion_count         (view, mcount)
    set_action_count         (view, acount)

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
    text_commands = [rhs] if isinstance(rhs, str) else rhs; _c = len(text_commands)
    for i,text_cmd in enumerate(text_commands):
        if not text_cmd: # skip empty commands
            continue
        mode = get_mode(view)
        cont = (i > 0) # pass to Hprocess notation as a continuation (like in a key sequence)
        _log.key(" —%s¦%s— ‘%s’cmd_t @ _hRHS_text m%s",i+1,_c,text_cmd,mode)
        if text_cmd.startswith('"command"'):
            _log.debug(" redirect Sublime's text ‘\"command\"’ to _hRHS as ‘:%s’",text_cmd)
            _handle_rhs(win, ':'+text_cmd)
        elif ':' in text_cmd:
            _log.debug(" redirect text command with ‘:’ command to _hRHS as ‘%s’",text_cmd)
            _handle_rhs(win,     text_cmd)
        else:
            if len(text_cmd) == 0:
                if (mode == OPERATOR_PENDING): # ToDO: is this needed?
                    seq = get_sequence(view)[:-len(get_partial_sequence(view))] + text_cmd
                else:
                    seq =                                                         text_cmd
                _log.key("  ‘%s’text_cmd NotFound, but it's 1 symbol, so process it anyway%s m‘%s’"
                    ,text_cmd,(f" as Ⓞ‘{seq}’" if mode == OPERATOR_PENDING else ''),mode)
                win.run_command('nv_process_notation',{'keys':seq, 'check_user_mappings':False,'cont':cont})
            else:
                _log.key("  ‘%s’text_cmd process w/o translating to a sequence m‘%s’",text_cmd,mode)
                win.run_command('nv_process_cmd_text',{'text_cmd':text_cmd, 'cont':cont})
                continue
