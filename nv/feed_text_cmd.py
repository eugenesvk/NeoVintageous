import logging
import time
from datetime import datetime

from NeoVintageous.nv.mappings import IncompleteMapping, Mapping, mappings_can_resolve, mappings_can_resolve_text, mappings_resolve, mappings_resolve_text
from NeoVintageous.nv.mappings_handler import evaluate_mapping, evaluate_mapping_text
from NeoVintageous.nv.settings import append_sequence, append_seq_icon, get_count, get_action_count, get_capture_register, get_mode, get_motion_count, get_partial_sequence, get_partial_text, get_sequence, get_setting, is_interactive, set_action_count, set_capture_register, set_mode, set_motion_count, set_partial_sequence, set_partial_text, set_register
from NeoVintageous.nv.state import evaluate_state, get_action, get_motion, init_view, is_runnable, must_collect_input, reset_command_data, set_action, set_motion, update_status_line
from NeoVintageous.nv.ui import ui_bell
from NeoVintageous.nv.vi.cmd_base import CommandNotFound, ViCommandDefBase, ViMotionDef, ViOperatorDef
from NeoVintageous.nv.vi.cmd_defs import ViOpenNameSpace, ViOpenRegister
from NeoVintageous.nv.vi.keys import resolve_keypad_count, to_bare_command_name
from NeoVintageous.nv.modes import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE
from NeoVintageous.nv.vim import enter_normal_mode, is_visual_mode
from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL, TFMT, addLoggingLevel, stream_handler

_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)
if _log.hasHandlers(): # clear existing handlers, including sublime's
    logging.getLogger(__name__).handlers.clear()
    # _log.addHandler(stream_handler)
_L = True if _log.isEnabledFor(logging.KEY) else False


class FeedTextCmdHandler():
    def __init__(self, view, text_cmd:str, count:int, do_eval:bool):
        self.view     = view
        self.window   = self.view.window()
        self.text_cmd = text_cmd
        self.count    = count
        self.do_eval  = do_eval

        self.mode     = get_mode(self.view)
        if _L:
            seq  = get_sequence        (view)
            seqP = get_partial_sequence(view)
            #txt  = get_text            (view)
            txtP = get_partial_text    (view)
            _log.keyt('\n—————T⌨️%s %s #%s Eval=%s             seq‘%s’ P‘%s’ txtP‘%s’'
            ,text_cmd,self.mode,count,do_eval,seq,seqP,txtP ) # ⏰%s,TFMT.format(t=datetime.now()))
    def handle(self) -> None: # TextCmd
        self   ._handle_bad_selection()



        if self._handle_register():
            return
        if self._collect_input():
            return
        self   ._handle()
    def _handle_bad_selection(self) -> None: # TextCmd
        if _is_selection_malformed              (self.view, self.mode):
            self.mode = _fix_malformed_selection(self.view, self.mode)



















    def _append_sequence(self) -> None: # TextCmd
        _log.keyt('‘%s’ icon status ‘%s’'
            ,self.text_cmd,self.cmd.icon)
        append_sequence         (self.view,                  self.text_cmd)
        append_seq_icon         (self.view, self.cmd.icon or self.text_cmd)
        update_status_line      (self.view)
    def _handle_register(self) -> bool: # TextCmd
        if get_capture_register (self.view):
            # set_register        (self.view, self.text_cmd)
            set_partial_sequence(self.view, '')
            set_partial_text    (self.view, '')
            return True
        return False
    def _collect_input(self) -> bool: # TextCmd
        motion = get_motion(self.view)
        action = get_action(self.view)
        _log.keyyt("mot‘%s’⋅#%s act‘%s’⋅#%s ⋅#%s", motion, get_motion_count(self.view), action, get_action_count(self.view), get_count(self.view))

        if must_collect_input(self.view, motion, action):
            if motion and\
               motion.accept_input:
                _log.warn('must collect input for a motion, but this is a text command, not a key')
                # motion.accept(self.key)
                # set_motion   (self.view, motion)  # Processed motion needs to reserialised and stored
            else:
                _log.warn('must collect input for an action, but this is a text command, not a key')
                # action.accept(self.key)
                # set_action   (self.view, action)  # Processed action needs to reserialised and stored

            if self.do_eval and is_runnable(self.view):
                _log.keyt('doeval on a runnable, reset_command_data')
                evaluate_state    (self.view)
                reset_command_data(self.view)
            return True
        return False


















    def _handle(self) -> None: # TextCmd
        if _L:
          self.dbg = ''
            # _log.keyt("  @_h ⌨️%s %s #%s Eval=%s usrMap=%s",self.key,self.mode,self.repeat_count,self.do_eval,self.check_user_mappings) # ⏰%s,TFMT.format(t=datetime.now()))
        text_cmd = self.text_cmd
        mode     = self.mode
        view     = self.view














        cmd = mappings_resolve_text(view, text_command=text_cmd, mode=mode, check_user_mappings=False)
        if isinstance(cmd, CommandNotFound):
            _log.warn("  ‘%s’text_cmd NotFound, skipping m‘%s’",text_cmd,mode)
            return






        self.cmd = cmd
        self   ._append_sequence() # status bar vim-seq sequence
        if (isCmdHandled := self._handle_cmd()):
            if _L:
                _log.keyt('%s',self.dbg)
            return
        else:
            _log.warn("  ‘%s’text_cmd couldn't be handled m‘%s’",text_cmd,get_mode(self.view))


    def _handle_mapping_text(self, mapping: Mapping) -> None:
        if self.do_eval: # TODO Review What happens if Mapping + do_eval=False
            evaluate_mapping_text(self.view, mapping)




























































    def _handle_cmd(self) -> bool:


        cmd  = self.cmd
        if isinstance(cmd, IncompleteMapping):
            if _L:
                self.dbg += f" ↩+ ¦¦cmd=IncompleteMapping"
            return True
        if isinstance(cmd, ViOpenNameSpace  ):
            if _L:
                self.dbg += f" ↩+ ¦{cmd}¦cmd=OpenNameSpace"
            return True
        if isinstance(cmd, ViOpenRegister   ):
            if _L:
                self.dbg += f" ↩+ ¦{cmd}¦cmd=OpenRegister→set"
            set_capture_register(self.view, True)
            return True
        if isinstance(cmd, Mapping):
            if _L:
                self.dbg += f" ↩+ ‹‘{cmd.lhs}’=‘{cmd.rhs}’› cmd=Map→_h "
            self._handle_mapping_text(cmd)
            return True
        if isinstance(cmd, CommandNotFound):
            if _L:
                self.dbg += f" ↩− cmd=NotFound"
            if self._handle_command_not_found(cmd):
                return True
        # if (isinstance(cmd, ViOperatorDef) and get_mode(self.view) == OPERATOR_PENDING): # unreachable code?
        #     cmd = mappings_resolve_text(self.view, text_command=self.text_cmd)
        #     if self._handle_command_not_found(cmd):
        #         if _L:
        #             self.dbg += f" ↩− ¦{_cmd_in}¦cmd=ⓄOperatorDef→NotFound"
        #         return True
        #     else:
        #         if _L:
        #             self.dbg += f" ↩+ ¦{cmd}¦cmd←¦{_cmd_in}¦ⓄOperatorDef"
        if _L:
            self.dbg += f", _hCmd"
        self._handle_command(cmd, self.do_eval)
        if _L:
            self.dbg += f" ↩+ ¦{cmd}¦cmd=_handle_cmd"
        return True





    def _handle_command(self, command:ViCommandDefBase, do_eval:bool) -> None:
        """ Raises ValueError if too many motions|actions, or unexpected command type"""
        _is_runnable = is_runnable(self.view)

        if   isinstance(command, ViMotionDef):
            if _is_runnable:
                raise ValueError('too many motions')
            set_motion  (self.view, command)
            if  get_mode(self.view) == OPERATOR_PENDING:
                set_mode(self.view, NORMAL)
        elif isinstance(command, ViOperatorDef):
            if _is_runnable:
                raise ValueError('too many actions')
            set_action  (self.view, command)
            if command.motion_required and not is_visual_mode(get_mode(self.view)):
                set_mode(self.view, OPERATOR_PENDING)
        else:
            raise ValueError('unexpected command type')

        if is_interactive(self.view):
            if command.accept_input and command.input_parser and command.input_parser.is_panel():
                command.input_parser.run_command(self.view.window())

        if get_mode(self.view) == OPERATOR_PENDING:
            set_partial_sequence(self.view, '')
            set_partial_text    (self.view, '')
        if do_eval:
            evaluate_state      (self.view)

    def _handle_command_not_found(self, command) -> bool:
        if isinstance(command, CommandNotFound):
            if  get_mode(self.view) == OPERATOR_PENDING:
                set_mode(self.view, NORMAL)
            reset_command_data(self.view)
            ui_bell()
            return True
        return False


def _is_selection_malformed(view, mode) -> bool:
    return mode not in (VISUAL, VISUAL_LINE, VISUAL_BLOCK, SELECT) and view.has_non_empty_selection_region()


def _fix_malformed_selection(view, mode: str) -> str:
    if mode == NORMAL and len(view.sel()) > 1: # If a selection was made via the mouse or a built-in ST command the selection may be in an inconsistent state e.g. incorrect mode. https://github.com/NeoVintageous/NeoVintageous/issues/742
        mode = VISUAL
        set_mode(view, mode)
    elif mode != VISUAL and view.has_non_empty_selection_region(): # Try to fixup a malformed visual state. For example, apparently this can happen when a search is performed via a search panel and "Find All" is pressed. In that case, multiple selections may need fixing.
        view.window().run_command('nv_enter_visual_mode', {'mode': mode})
    init_view(view) # TODO Extract fix malformed selections specific logic from init_view()
    return mode
