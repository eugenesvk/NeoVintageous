import re
import logging
import sublime  # noqa: E402

from sublime import active_window, PopupFlags

from NeoVintageous.nv import macros
from NeoVintageous.nv import plugin
from NeoVintageous.nv.macros import add_macro_step
from NeoVintageous.nv.polyfill import run_window_command
from NeoVintageous.nv.session import get_session_view_value, set_session_view_value
from NeoVintageous.nv.settings import get_glue_until_normal_mode, get_mode, get_reset_during_init, get_sequence, get_setting, is_interactive, is_processing_notation, set_action_count, set_capture_register, set_mode, set_motion_count, set_partial_sequence, set_partial_text, set_register, set_repeat_data, set_reset_during_init, set_sequence
from NeoVintageous.nv.utils import get_visual_block_sel_b
from NeoVintageous.nv.utils import get_visual_repeat_data, is_view, save_previous_selection, update_xpos
from NeoVintageous.nv.vi import cmd_defs
from NeoVintageous.nv.vi.cmd_base import ViMotionDef, ViOperatorDef
from NeoVintageous.nv.vi.cmd_defs import ViToggleMacroRecorder
from NeoVintageous.nv.modes import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE
from NeoVintageous.nv.modes import Mode as M, mode_names, mode_names_rev, text_to_modes, text_to_mode_alone
from NeoVintageous.nv     import vim # for always fresh config values, defaults + user
from NeoVintageous.nv.vim import clean_view, enter_insert_mode, enter_normal_mode, enter_visual_mode, is_visual_mode, mode_to_name, reset_status_line, run_action, run_motion

from NeoVintageous.nv.rc import cfgU

from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL
_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)
_L = True if _log.isEnabledFor(logging.KEY) else False

DEF = dict(
     enable   	= True
    ,prefix   	= ''
    ,template 	= '''<body id="nv_motion_count"><span>{prefix}{count}</span></body>'''
    ,maxwidth 	= 80
    ,maxheight	= 30
)
import copy
CFG = copy.deepcopy(DEF) # copy defaults to be able to reset values on config reload
def reload_with_user_data_kdl() -> None:
    if hasattr(cfgU,'kdl') and (nest := cfgU.kdl.get('indicator',None))\
        and                    (cfg  :=     nest.get('count'    ,None)): # skip on initial import when Plugin API isn't ready, so no settings are loaded
        global CFG
        _log.debug("@registers: Parsing config indicator/count")
        for cfg_key in CFG:
            if (node := cfg.get(cfg_key,None)): # prefix "⌗" node/arg pair
                if (args := node.args):
                    tag_val = args[0] #(t)"⌗" if (t) exists (though shouldn't)
                    # val = tag_val.value if hasattr(tag_val,'value') else tag_val # ignore tag
                    if hasattr(tag_val,'value'):
                        val = tag_val.value # ignore tag
                        _log.warn("node ‘%s’ has unrecognized tag in argument ‘%s’"
                            ,      node.name,                               tag_val)
                    else:
                        val = tag_val
                    CFG[node.name] = val
                    # print(f"indicator count from argument ‘{tag_val}’")
                elif not args:
                    _log.warn("node ‘%s’ is missing arguments in its child ‘%s’"
                        ,         cfg_key,                               node.name)
                if len(args) > 1:
                    _log.warn("node ‘%s’ has extra arguments in its child ‘%s’, only the 1st was used ‘%s’"
                        ,         cfg_key,                              node.name,         {', '.join(args)})
        node = cfg
        for i,key in enumerate(prop_d := node.props): # prefix="⌗", alternative notation to child node/arg pairs
            tag_val = prop_d[key] #prefix=(t)"⌗" if (t) exists (though shouldn't)
            # val = tag_val.value if hasattr(tag_val,'value') else tag_val # ignore tag
            if hasattr(tag_val,'value'):
                val = tag_val.value # ignore tag
                _log.warn("node ‘%s’ has unrecognized tag in property ‘%s=%s’"
                    ,             node.name,                         key,tag_val)
            else:
                val = tag_val
            if key in CFG:
                CFG[key] = val
                # print(f"indicator count from property ‘{key}={val}’")
            else:
                _log.error("node ‘%s’ has unrecognized property ‘%s=%s’"
                    ,             node.name,                   key,tag_val)
    else:
        CFG = copy.deepcopy(DEF) # copy defaults to be able to reset values on config reload

def get_popup_html(sym) -> str:
    return CFG['template'].format_map(dict(prefix=CFG['prefix'],count=sym))
def show_popup_count(view:sublime.View, sym:str, point:int=-1) -> None:
    view.show_popup(
      content     	= get_popup_html(sym)               	# str
      , flags     	= PopupFlags.HIDE_ON_CHARACTER_EVENT	#
      , location  	= point                             	# Point -1
      , max_width 	= CFG['maxwidth']                   	# DIP
      , max_height	= CFG['maxheight']                  	# DIP
    )

re_flags = 0
re_flags |= re.MULTILINE | re.IGNORECASE
re_cmd_count_p = r"<k([0-9])>"
re_cmd_count   = re.compile(re_cmd_count_p, flags=re_flags)
def update_status_line(view) -> None:
    mode_txt  = get_mode(view) # mode_insert
    mode_enum = mode_names_rev.get(mode_txt,None) # Mode.Insert
    if mode_enum in vim.CFGM and vim.CFGM[mode_enum] is not None:
        mode_name = vim.CFGM[mode_enum]
    else:
        mode_name = mode_to_name(mode_txt)
    if mode_name:
        view.set_status(vim.CFG['idmode'], f"{vim.CFG['prefix']}{mode_name}{vim.CFG['suffix']}")

    seq_txt = get_sequence(view)
    view.set_status(vim.CFG['idseq'], seq_txt)
    _log.key("set ‘idseq’ status to ‘%s’",seq_txt)

    if CFG['enable'] and (match := re_cmd_count.findall(seq_txt)): # show popup
        count_s = ''.join(match)
        show_popup_count(view, count_s)


def must_collect_input(view, motion: ViMotionDef, action: ViOperatorDef) -> bool:
    _log.key("must_collect_input? mtn‘%s’⎀?%s‘%s’ act‘%s’⎀?%s‘%s’"
        ,motion,motion.accept_input if motion else '_',motion.inp if motion else '_'
        ,action,action.accept_input if action else '_',action.inp if action else '_'
        )
    if motion and action:
        if motion.accept_input:
            return True

        return (action.accept_input and action.input_parser is not None and action.input_parser.is_after_motion())

    # Special case: `q` should stop the macro recorder if it's running and
    # not request further input from the user.
    if (isinstance(action, ViToggleMacroRecorder) and macros.is_recording()):
        return False

    if (action and action.accept_input and action.input_parser and action.input_parser.is_immediate()):
        return True

    if motion:
        return motion.accept_input

    return False


def _should_scroll_into_view(motion: ViMotionDef, action: ViOperatorDef) -> bool:
    if motion and motion.scroll_into_view:
        return True

    if action and action.scroll_into_view:
        return True

    return False


def _must_update_xpos(motion: ViMotionDef, action: ViOperatorDef) -> bool:
    if motion and motion.updates_xpos:
        return True

    if action and action.updates_xpos:
        return True

    return False


def _scroll_into_view(view, mode: str) -> None:
    sels = view.sel()
    if len(sels) < 1:
        return

    if mode == VISUAL_BLOCK:
        sel = get_visual_block_sel_b(view)
    else:
        # Show the *last* cursor on screen. There is currently no way to
        # identify the "active" cursor of a multiple cursor selection.
        sel = sels[-1]

    target_pt = sel.b

    # In VISUAL mode we need to make sure that any newline at the end of
    # the selection is NOT included in the target, because otherwise an
    # extra line after the target line will also be scrolled into view.
    if is_visual_mode(mode):
        if sel.b > sel.a:
            if view.substr(sel.b - 1) == '\n':
                target_pt = max(0, target_pt - 1)
                # Use the start point of the target line to avoid
                # horizontal scrolling. For example, this can happen in
                # VISUAL LINE mode when the EOL is off-screen.
                target_pt = max(0, view.line(target_pt).a)

    view.show(target_pt, False)


def _scroll_into_active_view() -> None:
    window = active_window()
    if window:
        view = window.active_view()
        if view:
            _scroll_into_view(view, get_mode(view))


def _create_definition(view, name: str):
    cmd = get_session_view_value(view, name)
    if cmd:
        cls = getattr(cmd_defs, cmd['name'], None)

        if cls is None:
            cls = plugin.classes.get(cmd['name'], None)

            if cls is None:
                raise ValueError('unknown %s: %s' % (name, cmd))

        return cls.from_json(cmd['data'])


def get_action(view):
    return _create_definition(view, 'action')


def set_action(view, value) -> None:
    serialized = value.serialize() if value else None
    set_session_view_value(view, 'action', serialized)


def get_motion(view):
    return _create_definition(view, 'motion')


def set_motion(view, value) -> None:
    serialized = value.serialize() if value else None
    set_session_view_value(view, 'motion', serialized)


def reset_command_data(view) -> None:
    # Resets all temp data needed to build a command or partial command.
    motion = get_motion(view)
    action = get_action(view)

    if _must_update_xpos(motion, action):
        update_xpos(view)

    if _should_scroll_into_view(motion, action):
        # Intentionally using the active view because the previous command
        # may have switched views and view would be the previous one.
        _scroll_into_active_view()

    action and action.reset()
    set_action(view, None)
    motion and motion.reset()
    set_motion(view, None)
    set_action_count(view, '')
    set_motion_count(view, '')
    set_sequence(view, '')
    set_partial_sequence(view, '')
    set_partial_text(view, '')
    set_register(view, '"')
    set_capture_register(view, False)
    reset_status_line(view, get_mode(view))


def is_runnable(view) -> bool:
    # Returns:
    #   True if motion and/or action is in a runnable state, False otherwise.
    # Raises:
    #   ValueError: Invlid mode.
    action = get_action(view)
    motion = get_motion(view)

    if must_collect_input(view, motion, action):
        return False

    mode = get_mode(view)

    if action and motion:
        if mode != NORMAL:
            raise ValueError('invalid mode')

        return True

    if (action and (not action.motion_required or is_visual_mode(mode))):
        if mode == OPERATOR_PENDING:
            raise ValueError('action has invalid mode')

        return True

    if motion:
        if mode == OPERATOR_PENDING:
            raise ValueError('motion has invalid mode')

        return True

    return False


def evaluate_state(view) -> None:
    _log.debug('evaluating...')
    if not is_runnable(view):
        _log.debug('not runnable!')
        return

    action = get_action(view)
    motion = get_motion(view)

    if action and motion: # Evaluate action with motion: runs the action with the motion as an argument. The motion's mode is set to INTERNAL_NORMAL and is run by the action internally to make the selection it operates on. For example the motion commands can be used after an operator command, to have the command operate on the text that was moved over.
        action_cmd = action.translate(view)
        motion_cmd = motion.translate(view)
        _log.debug('action: %s', action_cmd)
        _log.debug('motion: %s', motion_cmd)

        set_mode(view, INTERNAL_NORMAL)
        if 'mode' in action_cmd['action_args']:
            action_cmd         ['action_args']['mode'] = INTERNAL_NORMAL
        if 'mode' in motion_cmd['motion_args']:
            motion_cmd         ['motion_args']['mode'] = INTERNAL_NORMAL

        args = action_cmd['action_args']
        _log.debug("action_args ¦%s¦", args)
        args['count'] = 1
        args['motion'] = motion_cmd # Let the action run the motion within its edit object so that we don't need to worry about grouping edits to the buffer.

        if get_glue_until_normal_mode(view) and not is_processing_notation(view):
            run_window_command('mark_undo_groups_for_gluing')

        add_macro_step    (view, action_cmd['action'], args)
        run_window_command(      action_cmd['action'], args)

        if is_interactive(view) and get_action(view).repeatable:
            set_repeat_data(view, ('vi', str(get_sequence(view)), get_mode(view), None))

        reset_command_data(view)

        return  # Nothing more to do.

    if motion: # Evaluate motion: Run it.
        motion_cmd = motion.translate(view)
        _log.debug('motion: %s', motion_cmd)
        add_macro_step(view, motion_cmd['motion'], motion_cmd['motion_args'])
        run_motion(view, motion_cmd)

    if action:
        action_cmd = action.translate(view)
        _log.debug('action: %s', action_cmd)
        if get_mode(view) == NORMAL:
            set_mode(view, INTERNAL_NORMAL)
            if 'mode' in action_cmd['action_args']:
                action_cmd['action_args']['mode'] = INTERNAL_NORMAL
        elif is_visual_mode(get_mode(view)): # Special-case exclusion: saving the previous selection would overwrite the previous selection needed e.g. gv in a VISUAL mode needs to expand or contract to previous selection.
            if action_cmd['action'] != 'nv_vi_gv':
                save_previous_selection(view, get_mode(view))

        if get_glue_until_normal_mode(view) and not is_processing_notation(view): # Some commands, like 'i' or 'a', open a series of edits that need to be grouped together unless we are gluing a larger sequence through nv_process_notation. For example, aFOOBAR<Esc> should be grouped atomically, but not inside a sequence like iXXX<Esc>llaYYY<Esc>, where we want to group the whole sequence instead.
            run_window_command('mark_undo_groups_for_gluing')

        sequence           = get_sequence          (view)
        visual_repeat_data = get_visual_repeat_data(view, get_mode(view))
        action             = get_action            (view)

        add_macro_step(view, action_cmd['action'], action_cmd['action_args'])

        run_action(active_window(), action_cmd)

        if not (is_processing_notation(view) and get_glue_until_normal_mode(view)) and action.repeatable:
            set_repeat_data(view, ('vi', sequence, get_mode(view), visual_repeat_data))

    if get_mode(view) == INTERNAL_NORMAL:
        set_mode(view, NORMAL)

    reset_command_data(view)


def _should_reset_mode(view, mode: str) -> bool:
    return mode == UNKNOWN or get_setting(view, 'reset_mode_when_switching_tabs')


def init_view(view) -> None:
    # If the view not a regular vim capable view (e.g. console, widget, panel),
    # skip the state initialisation and perform a clean routine on the view.
    # TODO is a clean routine really necessary on non-vim capable views?
    if not is_view(view):
        clean_view(view)
        return

    if not get_reset_during_init(view):
        # Probably exiting from an input panel, like when using '/'. Don't reset
        # the global state, as it may contain data needed to complete the
        # command that's being built.
        set_reset_during_init(view, True)
        return

    mode = get_mode(view)

    if not _should_reset_mode(view, mode):
        return

    # Fix malformed selection: if we have no selections, add one.
    if len(view.sel()) == 0:
        view.sel().add(0)

    default_mode = get_setting(view, 'default_mode')

    if default_mode and\
       default_mode != 'normal':
        if default_mode == 'insert':
            if mode in (NORMAL, UNKNOWN):
                enter_insert_mode(view, mode)
        elif default_mode == 'visual':
            if mode in (NORMAL, UNKNOWN):
                enter_normal_mode(view, mode)
                enter_visual_mode(view, mode)
    elif mode in (VISUAL, VISUAL_LINE, VISUAL_BLOCK): # Visual modes are not reset (to normal mode), because actions like pressing the super key or opening a command-palette/overlay will cause the active view to lose focus and when focus is received again it triggers the on_activated() event, this in turn initialises the view' state, which would reset the visual mode to normal mode, therefore, for example, any command run from the command palette that expects to operate on a visual selection wouldn't work because the visual selection is reset to normal mode before the command has time to run. See https://github.com/NeoVintageous/NeoVintageous/issues/547
        pass
    elif mode in (INSERT, REPLACE): # NOTE that the mode is not passed as an argument because it causes the cursor to move back one point from it's current position, for example when pressing i<Esc>i<Esc>i<Esc> the cursor moves one point each time, which is expected, but not expected when initialising state. But not passing the mode may also be causing some other hidden bugs too.
        view.window().run_command('nv_enter_normal_mode', {'from_init': True})
    elif mode != VISUAL and view.has_non_empty_selection_region(): # Try to fixup a malformed visual state. For example, apparently this can happen when a search is performed via a search panel and "Find All" is pressed. In that case, multiple selections may need fixing.
        view.window().run_command('nv_enter_visual_mode', {'mode': mode})
    else: # This may be run when we're coming from cmdline mode.
        mode = VISUAL if view.has_non_empty_selection_region() else mode
        view.window().run_command('nv_enter_normal_mode', {'mode': mode, 'from_init': True})

    reset_command_data(view)
