import logging
import time
from datetime import datetime

from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL
from NeoVintageous.nv.mappings import IncompleteMapping
from NeoVintageous.nv.mappings import Mapping
from NeoVintageous.nv.mappings import mappings_can_resolve, mappings_can_resolve_text
from NeoVintageous.nv.mappings import mappings_resolve, mappings_resolve_text
from NeoVintageous.nv.mappings_handler import evaluate_mapping, evaluate_mapping_text
from NeoVintageous.nv.settings import append_sequence
from NeoVintageous.nv.settings import get_action_count
from NeoVintageous.nv.settings import get_capture_register
from NeoVintageous.nv.settings import get_mode
from NeoVintageous.nv.settings import get_motion_count
from NeoVintageous.nv.settings import get_partial_sequence, get_partial_text
from NeoVintageous.nv.settings import get_sequence
from NeoVintageous.nv.settings import get_setting
from NeoVintageous.nv.settings import is_interactive
from NeoVintageous.nv.settings import set_action_count
from NeoVintageous.nv.settings import set_capture_register
from NeoVintageous.nv.settings import set_mode
from NeoVintageous.nv.settings import set_motion_count
from NeoVintageous.nv.settings import set_partial_sequence, set_partial_text
from NeoVintageous.nv.settings import set_register
from NeoVintageous.nv.state import evaluate_state
from NeoVintageous.nv.state import get_action
from NeoVintageous.nv.state import get_motion
from NeoVintageous.nv.state import init_view
from NeoVintageous.nv.state import is_runnable
from NeoVintageous.nv.state import must_collect_input
from NeoVintageous.nv.state import reset_command_data
from NeoVintageous.nv.state import set_action
from NeoVintageous.nv.state import set_motion
from NeoVintageous.nv.state import update_status_line
from NeoVintageous.nv.ui import ui_bell
from NeoVintageous.nv.vi.cmd_base import CommandNotFound
from NeoVintageous.nv.vi.cmd_base import ViCommandDefBase
from NeoVintageous.nv.vi.cmd_base import ViMotionDef
from NeoVintageous.nv.vi.cmd_base import ViOperatorDef
from NeoVintageous.nv.vi.cmd_defs import ViOpenNameSpace
from NeoVintageous.nv.vi.cmd_defs import ViOpenRegister
from NeoVintageous.nv.vi.keys import resolve_keypad_count
from NeoVintageous.nv.vi.keys import to_bare_command_name
from NeoVintageous.nv.modes import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE
from NeoVintageous.nv.vim import enter_normal_mode
from NeoVintageous.nv.vim import is_visual_mode
from NeoVintageous.nv.log import addLoggingLevel, stream_handler

_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)
if _log.hasHandlers(): # clear existing handlers, including sublime's
    logging.getLogger(__name__).handlers.clear()
    # _log.addHandler(stream_handler)
_L = True if _log.isEnabledFor(logging.KEY) else False

TFMT = '{t.minute:2}:{t.second:2}.{t.microsecond}'

class FeedKeyHandler():

    def __init__(self, view, key: str, repeat_count: int, do_eval: bool, check_user_mappings: bool):
        self.view                = view
        self.window              = self.view.window()
        self.key                 = key
        self.repeat_count        = repeat_count
        self.do_eval             = do_eval
        self.check_user_mappings = check_user_mappings
        self.mode                = get_mode(self.view)
        if _L:
            _log.key('—————⌨️%s %s #%s doEval=%s checkUsrMap=%s ⏰%s'
            ,key,self.mode,repeat_count, do_eval,check_user_mappings,TFMT.format(t=datetime.now()))

    def handle(self) -> None:
        self._handle_bad_selection()

        if self._handle_escape():
            return

        self._append_sequence()

        if self._handle_register():
            return

        if self._collect_input():
            return

        self._handle()

    def _handle_bad_selection(self) -> None:
        if _is_selection_malformed(self.view, self.mode):
            self.mode = _fix_malformed_selection(self.view, self.mode)

    def _handle_escape(self) -> bool:
        if self.key.lower() == '<esc>':
            should_hide_auto_complete_on_escape = (
                self.mode == INSERT and
                self.view.is_auto_complete_visible() and
                not get_setting(self.view, 'auto_complete_exit_from_insert_mode'))

            if should_hide_auto_complete_on_escape:
                self.view.window().run_command('hide_auto_complete')
            elif self.mode == SELECT:
                self.view.run_command('nv_vi_select_big_j', {'mode': self.mode})
            else:
                enter_normal_mode(self.window, self.mode)
                reset_command_data(self.view)

            return True

        return False

    def _append_sequence(self) -> None:
        append_sequence(self.view, self.key)
        update_status_line(self.view)

    def _handle_register(self) -> bool:
        if get_capture_register(self.view):
            set_register(self.view, self.key)
            set_partial_sequence(self.view, '')
            set_partial_text(self.view, '')

            return True

        return False

    def _collect_input(self) -> bool:
        motion = get_motion(self.view)
        action = get_action(self.view)

        if must_collect_input(self.view, motion, action):
            if motion and motion.accept_input:
                motion.accept(self.key)
                set_motion(self.view, motion)  # Processed motion needs to reserialised and stored.
            else:
                action.accept(self.key)
                set_action(self.view, action)  # Processed action needs to reserialised and stored.

            if self.do_eval and is_runnable(self.view):
                evaluate_state(self.view)
                reset_command_data(self.view)

            return True

        return False

    def _handle_count(self) -> bool:
        if self.repeat_count:
            set_action_count(self.view, self.repeat_count)
        else:
            key = resolve_keypad_count(self.key)
            if key.isdigit():
                # NOTE motion/action counts need to be cast to strings because they need
                # to be "joined" to the previous key press, not added. For example when
                # you press the digit 1 followed by 2, it's a count of 12, not 3.
                if not get_action(self.view):
                    if key != '0' or get_action_count(self.view):
                        set_action_count(self.view, get_action_count(self.view) + key)
                        return True
                elif get_mode(self.view) == OPERATOR_PENDING:
                    if key != '0' or get_motion_count(self.view):
                        set_motion_count(self.view, get_motion_count(self.view) + key)
                        return True

        return False

    def _handle(self) -> None:
        if _L:
          self._dbg_seq, self._dbg_txt = '',''
          _log.key("  @_h ⌨️%s %s #%s doEval=%s usrMap=%s ⏰%s",self.key,self.mode,self.repeat_count,self.do_eval,self.check_user_mappings,TFMT.format(t=datetime.now()))
        # If the user has defined a mapping that starts with a number i.e. count then the count handler has to be skipped otherwise it won't resolve. See https://github.com/NeoVintageous/NeoVintageous/issues/434
        can_resolve_txt = mappings_can_resolve_text(self.view, self.key)
        can_resolve_seq = mappings_can_resolve     (self.view, self.key)
        if _L:
          self._dbg_txt += f"{'✓' if can_resolve_txt else '✗'}TXT ⌨️{self.key}"
          self._dbg_seq += f"{'✓' if can_resolve_seq else '✗'}SEQ ⌨️{self.key}"
        if not can_resolve_txt and not can_resolve_seq:
            if self._handle_count():
                if _L:
                    self._dbg_txt += f" ↩ _hCount"; _log.key(self._dbg_txt); _log.key(self._dbg_seq)
                return

        _part_txt = get_partial_text    (self.view)
        _part_seq = get_partial_sequence(self.view)
        set_partial_text                (self.view, _part_txt + self.key)
        set_partial_sequence            (self.view, _part_seq + self.key)

        command_txt = mappings_resolve_text(self.view, check_user_mappings=self.check_user_mappings)
        command_seq = mappings_resolve     (self.view, check_user_mappings=self.check_user_mappings)
        if _L:
            self._dbg_seq += f" part¦{_part_seq}¦"
            self._dbg_txt += f" part¦{_part_txt}¦"
        self.command_seq = command_seq
        self.command_txt = command_txt
        #m# cmd_seq¦<ViSetMark>¦  cmd_txt¦<NeoVintageous.nv.mappings.Mapping object at 0x10a2468b0>¦


        self.command = command_txt
        if (isTextHandled := self._handle_text()):
            return
        else:
            self._handle_seq()

    def _handle_seq(self) -> None:
        cmdS = self.cmdS
        cmdT = self.cmdT
        cmd  = cmdS
        if isinstance(cmd, IncompleteMapping):
            if _L:
                self._dbg_seq += f" ↩ ¦{cmd}¦cmd=IncompleteMapping"
            return
        if isinstance(cmd, ViOpenNameSpace):
            if _L:
                self._dbg_seq += f" ↩ ¦{cmd}¦cmd=OpenNameSpace"
            return
        if isinstance(cmd, ViOpenRegister):
            if _L:
                self._dbg_seq += f" ↩ ¦{cmd}¦cmd=OpenRegister→set"
            set_capture_register(self.view, True)
            return
        if isinstance(cmd, Mapping):
            if _L:
                self._dbg_seq += f" ↩ ¦{cmd}¦cmd=Map→_h ‹‘{cmd.lhs}’ ‘{cmd.rhs}’›"
            self._handle_mapping     (cmd)
            return
        if isinstance(cmd, CommandNotFound): # TODO We shouldn't need to try resolve the command again. The resolver should handle commands correctly the first time. The reason this logic is still needed is because we might be looking at a command like 'dd', which currently doesn't resolve properly. The first 'd' is mapped for NORMAL mode, but 'dd' is not mapped in OPERATOR PENDING mode, so we get a missing command, and here we try to fix that (user mappings are excluded, since they've already been given a chance to evaluate).
            if _L:
                self._dbg_seq += f" ↩ ¦{cmd}¦cmd=NotFound"
            if get_mode(self.view) == OPERATOR_PENDING:
                cmd = mappings_resolve(self.view, sequence=to_bare_command_name(get_sequence(self.view)),mode=NORMAL, check_user_mappings=False)
            else:
                cmd = mappings_resolve(self.view, sequence=to_bare_command_name(get_sequence(self.view)))
            if self._handle_command_not_found(cmd):
                if _L:
                    self._dbg_seq += f" ↩ cmd=NotFound"
                return
            else:
                if _L:
                    self._dbg_seq += f" ¦{cmd}¦cmd=wasNotFound"
        if (isinstance(cmd, ViOperatorDef) and get_mode(self.view) == OPERATOR_PENDING): # TODO This should be unreachable code. The mapping resolver should handle anything that can still reach this point (the first time). We're expecting a motion, but we could still get an action. For example, dd, g~g~ or g~~ remove counts. It looks like it might only be the '>>' command that needs this code.
            if _L:
                self._dbg_seq += f" ¦{cmd}¦cmd=ⓄOperatorDef"
            cmd = mappings_resolve(self.view, sequence=to_bare_command_name(get_sequence(self.view)), mode=NORMAL)
            if self._handle_command_not_found(cmd):
                if _L:
                    self._dbg_seq += f" ↩ cmd=NotFound"
                return
            else:
                if _L:
                    self._dbg_seq += f" ↩ ¦{cmd}¦=resolved"
            if not cmd.motion_required:
                set_mode(self.view, NORMAL)
        self._dbg_seq += f" ¦{cmd}¦cmd→_h" # ToDo
        _log.key(self._dbg_seq)
        self._handle_command(cmd, self.do_eval)

    def _handle_text(self) -> bool:
        cmdS = self.cmdS
        cmdT = self.cmdT
        cmd  = cmdT
        if isinstance(cmd, IncompleteMapping):
            if _L:
                self._dbg_txt += f" ↩+ ¦{cmd}¦cmd=IncompleteMapping"
            return True
        if isinstance(cmd, ViOpenNameSpace  ): # ToDo
            if _L:
                self._dbg_txt += f" ↩+ ¦{cmd}¦cmd=OpenNameSpace"
            return True
        if isinstance(cmd, ViOpenRegister   ): # ToDo
            if _L:
                self._dbg_txt += f" ↩+ ¦{cmd}¦cmd=OpenRegister→set"
            set_capture_register(self.view, True)
            return True
        if isinstance(cmd, Mapping):
            if _L:
                self._dbg_txt += f" ↩+ ¦{cmd}¦cmd=Map→_h ‹‘{cmd.lhs}’ ‘{cmd.rhs}’›"
            self._handle_mapping_text(cmd)
            return True
        if isinstance(cmd, CommandNotFound): # ToDo
            if _L:
                self._dbg_txt += f" ↩− ¦{cmd}¦cmd=NotFound"
            return False # pass to handle sequence
        if (isinstance(cmd, ViOperatorDef) and get_mode(self.view) == OPERATOR_PENDING):
            if _L:
                self._dbg_txt += f" ↩− ¦{cmd}¦cmd=ⓄOperatorDef"
            return False # pass to handle sequence
        if _L:
            self._dbg_txt += f", (disabled)TXT _handle_command" # ToDo
        # self._handle_command(cmd, self.do_eval) # todo handle text command
        if _L:
            self._dbg_txt += f" ↩− ¦{cmdT}¦cmdT=Neither"
        return False # pass to handle sequence

    def _handle_mapping(self, mapping: Mapping) -> None:
        # TODO Review What happens if Mapping + do_eval=False
        if self.do_eval:
            evaluate_mapping(self.view, mapping)

    def _handle_mapping_text(self, mapping: Mapping) -> None:
        # TODO Review What happens if Mapping + do_eval=False
        if self.do_eval:
            evaluate_mapping_text(self.view, mapping)

    def _handle_command(self, command: ViCommandDefBase, do_eval: bool) -> None:
        # Raises:
        #   ValueError: If too many motions.
        #   ValueError: If too many actions.
        #   ValueError: Unexpected command type.
        _is_runnable = is_runnable(self.view)

        if isinstance(command, ViMotionDef):
            if _is_runnable:
                raise ValueError('too many motions')

            set_motion(self.view, command)

            if get_mode(self.view) == OPERATOR_PENDING:
                set_mode(self.view, NORMAL)

        elif isinstance(command, ViOperatorDef):
            if _is_runnable:
                raise ValueError('too many actions')

            set_action(self.view, command)

            if command.motion_required and not is_visual_mode(get_mode(self.view)):
                set_mode(self.view, OPERATOR_PENDING)

        else:
            raise ValueError('unexpected command type')

        if is_interactive(self.view):
            if command.accept_input and command.input_parser and command.input_parser.is_panel():
                command.input_parser.run_command(self.view.window())

        if get_mode(self.view) == OPERATOR_PENDING:
            set_partial_sequence(self.view, '')
            set_partial_text(self.view, '')

        if do_eval:
            evaluate_state(self.view)

    def _handle_command_not_found(self, command) -> bool:
        if isinstance(command, CommandNotFound):
            if get_mode(self.view) == OPERATOR_PENDING:
                set_mode(self.view, NORMAL)

            reset_command_data(self.view)
            ui_bell()

            return True

        return False


def _is_selection_malformed(view, mode) -> bool:
    return mode not in (VISUAL, VISUAL_LINE, VISUAL_BLOCK, SELECT) and view.has_non_empty_selection_region()


def _fix_malformed_selection(view, mode: str) -> str:
    # If a selection was made via the mouse or a built-in ST command the
    # selection may be in an inconsistent state e.g. incorrect mode.
    # https://github.com/NeoVintageous/NeoVintageous/issues/742
    if mode == NORMAL and len(view.sel()) > 1:
        mode = VISUAL
        set_mode(view, mode)
    elif mode != VISUAL and view.has_non_empty_selection_region():
        # Try to fixup a malformed visual state. For example, apparently this
        # can happen when a search is performed via a search panel and "Find
        # All" is pressed. In that case, multiple selections may need fixing.
        view.window().run_command('nv_enter_visual_mode', {'mode': mode})

    # TODO Extract fix malformed selections specific logic from init_view()
    init_view(view)

    return mode
