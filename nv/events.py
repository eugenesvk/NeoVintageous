from sublime import OP_EQUAL
from sublime import OP_NOT_EQUAL
from sublime import version
from sublime_plugin import EventListener

from NeoVintageous.nv.modeline import do_modeline
from NeoVintageous.nv.options import get_option
from NeoVintageous.nv.registers import set_alternate_file_register
from NeoVintageous.nv.session import session_on_close
from NeoVintageous.nv.session import session_on_exit
from NeoVintageous.nv.settings import get_mode
from NeoVintageous.nv.settings import get_setting
from NeoVintageous.nv.state import init_view
from NeoVintageous.nv.utils import fix_eol_cursor
from NeoVintageous.nv.utils import is_view
from NeoVintageous.nv.utils import update_xpos
from NeoVintageous.nv.modes import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE
from NeoVintageous.nv.vim import enter_normal_mode
from NeoVintageous.nv.vim import mode_to_char

__all__ = ['NeoVintageousEvents']


def _check_query_context_value(value: bool, operator: int, operand: bool, match_all: bool) -> bool:
    if operator == OP_EQUAL:
        if operand is True:
            return value
        elif operand is False:
            return not value
    elif operator is OP_NOT_EQUAL:
        if operand is True:
            return not value
        elif operand is False:
            return value

    return False


def _is_command_mode(view, operator: int = OP_EQUAL, operand: bool = True, match_all: bool = False) -> bool:
    return _check_query_context_value(
        (view.settings().get('command_mode') and is_view(view)),
        operator,
        operand,
        match_all
    )


def _is_insert_mode(view, operator: int, operand: bool, match_all: bool) -> bool:
    # TODO This currently returns true for all non-normal modes e.g. Replace
    # mode. Fixing this will break things, for example <Esc> in replace mode
    # would break, a few things need to be reworked to fix this.
    return _check_query_context_value(
        (not view.settings().get('command_mode') and is_view(view)),
        operator,
        operand,
        match_all
    )


def _command_or_insert(view, operator: int, operand: bool, match_all: bool) -> bool:
    return _check_query_context_value(
        is_view(view),
        operator,
        operand,
        match_all
    )


def _winaltkeys(view, operator: int, operand: str, match_all: bool) -> bool:
    # ALT+X is used to access menu entries X (underlined). This option resolves this conflicts with the use of the ALT key for mappings and entering special characters
    # Val 	ALT menu keys      	ALT+X NV map
    # no  	Off                	On (no auto handling)
    # yes 	On                 	Off
    # menu	On for ‘efghinpstv’	Off for the same keys
    winaltkeys = get_option(view, 'winaltkeys')
    if   winaltkeys == 'menu':
        return (operand not in tuple('efghinpstv') or not view.window().is_menu_visible()) #and _is_command_mode(view)
    elif winaltkeys == 'yes':
        return False
    else:
        return True #_is_command_mode(view)


def _handle_key(view, operator: int, operand: str, match_all: bool) -> bool:
    handle_keys = get_setting(view, 'handle_keys')
    if handle_keys:
        try: # Check if the key (no mode prefix; all modes) should be handled
            return bool(handle_keys[operand]) # <C-c>
        except KeyError:
            cur_mode_char = mode_to_char(get_mode(view)) # Check if the key should be handled only for a specific mode. The format is "{mode}_{key}" e.g. "n_<C-w>", "v_<C-w>" meaning NORMAL, VISUAL respectively. No prefix implies all modes. See mode_to_char() for a list of valid mode prefixes
            if cur_mode_char:
                try:
                    return bool(handle_keys[f"{cur_mode_char}_{operand}"])
                except KeyError:
                    pass
    if 'c-' in operand.lower()\
    or 'd-' in operand.lower(): # by default ignore all ⎈ or ◆ combos
        return False
    else:
        return True # and handle everything else


_OVERLAY_CONTROL_ELEMENTS = (
    'command_palette:input',
    'goto_anything:input',
    'quick_panel:input'
)

if int(version()) >= 4050:
    def _overlay_control(view, *args):
        return view.element() in _OVERLAY_CONTROL_ELEMENTS
else:
    # Not supported in ST < 4050: the view.element() api is available.
    def _overlay_control(view, *args):
        return None


_query_contexts = {
    'nv_command_or_insert'  : _command_or_insert,
    'nv_handle_key'         : _handle_key,
    'nv_overlay_control'    : _overlay_control,
    'nv_winaltkeys'         : _winaltkeys,
    'vi_command_mode_aware' : _is_command_mode,
    'vi_insert_mode_aware'  : _is_insert_mode,
}  # type: dict


class NeoVintageousEvents(EventListener):
    _last_deactivated_file_name = None

    def on_query_context(self, view, key: str, operator: int, operand, match_all: bool):
        # Called when determining to trigger a key binding with the given context key
        #→ operand: str|bool      e.g.: key=nv_handle_key operator=0 operand=<C-c>
        #← bool  If the context is   known
        #  None  If the context is unknown
        try:
            return _query_contexts[key](view, operator, operand, match_all)
        except KeyError:
            pass

    def on_text_command(self, view, command: str, args: dict):
        # Called when a text command is issued.
        #
        # The listener may return a (command, arguments) tuple to rewrite the
        # command, or None to run the command unmodified.

        if command == 'drag_select':

            # Updates the mode based on mouse events. For example, a double
            # click will select a word and enter VISUAL mode. A triple click
            # will select a line and enter VISUAL LINE mode.
            #
            # The command is rewritten by returning a chain of commands that
            # executes the original drag_select command followed by entering the
            # correct mode.

            mode = get_mode(view)

            if mode in (VISUAL, VISUAL_LINE, VISUAL_BLOCK):
                if (args.get('extend') or (args.get('by') == 'words') or args.get('additive')):
                    return
                elif args.get('by') == 'lines':
                    # Triple click: enter VISUAL LINE.
                    return ('nv_run_cmds', {'commands': [
                        ['drag_select', args],
                        ['nv_enter_visual_line_mode', {'mode': mode}]
                    ]})
                elif not args.get('extend'):
                    # Single click: enter NORMAL.
                    return ('nv_run_cmds', {'commands': [
                        ['drag_select', args],
                        ['nv_enter_normal_mode', {'mode': mode}]
                    ]})

            elif mode == NORMAL:
                # TODO Dragging the mouse does not seem to fire a different event than simply clicking. This makes it hard to update the xpos. See https://github.com/SublimeTextIssues/Core/issues/2117.  # noqa: E501
                if args.get('extend') or (args.get('by') == 'words'):
                    # Double click: enter VISUAL.
                    return ('nv_run_cmds', {'commands': [
                        ['drag_select', args],
                        ['nv_enter_visual_mode', {'mode': mode}]
                    ]})

    def on_post_text_command(self, view, command, args):
        # This fixes issues where the xpos is not updated after a mouse click
        # moves the cursor position. These issues look like they could be
        # compounded by Sublime Text issues (see on_post_save() and the
        # fix_eol_cursor utility). The xpos only needs to be updated on single
        # mouse click. See https://github.com/SublimeTextIssues/Core/issues/2117.
        if command == 'drag_select':
            if set(args) == {'event'}:
                if set(args['event']) == {'x', 'y', 'button'}:
                    if args['event']['button'] == 1:
                        update_xpos(view)

    def on_load(self, view):
        if is_view(view) and get_option(view, 'modeline'):
            do_modeline(view)

    def on_post_save(self, view):
        if is_view(view):
            # Ensure the carets are within valid bounds. For instance, this is a
            # concern when 'trim_trailing_white_space_on_save' is set to true.
            fix_eol_cursor(view, get_mode(view))

    def on_close(self, view):
        session_on_close(view)

    def on_activated(self, view):
        if is_view(view):
            # This mirrors Vim behaviour. We can't put this functionality in the
            # on_deactivated event because that event is triggered when the
            # mouse right button is clicked in a view.
            _clear_inactive_views_visual_selections(view)

            if self._last_deactivated_file_name:
                # The alternate file register is only set to the deactivating
                # view if the activating one is a normal view. Otherwise the
                # alternate file could be the currently active view.
                set_alternate_file_register(self._last_deactivated_file_name)  # type: ignore[unreachable]

        # Initialise view.
        init_view(view)

    def on_deactivated(self, view):
        self._last_deactivated_file_name = view.file_name()

    # The on_exit() API was added in build 4050.
    if int(version()) >= 4050:
        def on_exit(self):
            session_on_exit()


def _clear_inactive_views_visual_selections(view) -> None:
    window = view.window()
    if window:
        active_group = window.active_group()
        for group in range(window.num_groups()):
            if group != active_group:
                other_view = window.active_view_in_group(group)
                if other_view and other_view != view:
                    sel = other_view.sel()
                    if len(sel) > 0 and any([not s.empty() for s in sel]):
                        enter_normal_mode(other_view, get_mode(other_view))
