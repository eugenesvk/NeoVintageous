# A port of https://github.com/tpope/vim-unimpaired.
from sublime_plugin import TextCommand

from NeoVintageous.nv.options  import set_option, set_window_ui_element_visible, toggle_option
from NeoVintageous.nv.plugin   import register, register_text
from NeoVintageous.nv.polyfill import set_selection, view_find, view_rfind
from NeoVintageous.nv.utils    import InputParser, regions_transformer, resolve_normal_target, resolve_visual_line_target, resolve_visual_target, translate_char
from NeoVintageous.nv.vi       import seqs
from NeoVintageous.nv.vi.cmd_base import ViOperatorDef, translate_action
from NeoVintageous.nv.modes    import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE
from NeoVintageous.nv.window   import window_buffer_control, window_tab_control
from NeoVintageous.nv.cfg_parse import clean_name, get_tag_val_warn
from NeoVintageous.nv           import cfg as nvcfg

from NeoVintageous.nv.rc import cfgU

import logging
from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL
_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)

__all__ = ['nv_unimpaired_command']


DEF = {
    'option' : { # aliases are mapped to _OPTIONS
        'a': 'menu',  # non standard
        't': 'sidebar',  # non standard
        'm': 'minimap',  # non standard
        'e': 'statusbar',  # non standard
        'w': 'wrap', # word_wrap
        'h': 'hlsearch', # highlight found search results
        'l': 'list', # draw_white_space
        'b': 'background',
        'c': 'cursorline',
        'u': 'cursorcolumn',
        'n': 'number', # line_numbers
        'r': 'relativenumber', # relative_line_numbers
        's': 'spell',
        'i': 'ignorecase',
        'd': 'diff',
        'v': 'virtualedit',
        'x': 'crosshairs'
    },
}
import copy
CFG = copy.deepcopy(DEF) # copy defaults to be able to reset values on config reload


def reload_with_user_data_kdl() -> None:
    if hasattr(cfgU,'kdl') and (nest := cfgU.kdl.get('plugin'  ,None))\
        and                    (cfg  :=     nest.get('unimpaired',None)): # skip on initial import when Plugin API isn't ready, so no settings are loaded
        global CFG
        _log.debug("@plugin unimpaired: Parsing config")
        for node_parent in cfg.nodes: # 'alias'
            # 0. Parse node       args: clear
            # 1. Parse node child args: {m menu;}
            # 2. Parse node properties:  m=menu

            if (cfg_key:=node_parent.name) == 'option':
                # _log.debug(f"@plugin unimpaired: Parsing config {cfg_key}")
                args = [a for a in node_parent.getArgs((...,...))] if nvcfg.KDLV == 2 else node_parent.args
                if args: # 0. clear
                    tag_val = args[0] #(t)‘’ if (t) exists (though shouldn't)
                    (tag,val) = get_tag_val_warn(tag_val=tag_val,logger=_log,node_name=cfg_key)
                    if val == 'clear':
                        CFG[cfg_key].clear() # clear all existing aliases
                        _log.debug('CFG arg cleared @%s ‘%s’={}',cfg.name,cfg_key)
                    else:
                        _log.warn("node ‘%s’ has unrecognized value in argument ‘%s’, expecting one of: %s"
                            ,       node.name,                              tag_val,'clear')
                if len(args) > 1:
                    _log.warn("node ‘%s’ has extra arguments, only the 1st was used ‘%s’"
                        ,        cfg_key,                                {', '.join(args)})

                for node in node_parent.nodes: # 1. m menu key_node value_arg pairs
                    key = node.name
                    args = [a for a in node.getArgs((...,...))] if nvcfg.KDLV == 2 else node.args
                    if args:
                        tag_val = args[0] #(t)‘’ if (t) exists (though shouldn't)
                        # val = tag_val.value if hasattr(tag_val,'value') else tag_val # ignore tag
                        if hasattr(tag_val,'value'):
                            val = clean_name(tag_val.value) # ignore tag
                            _log.warn("node ‘%s’ has unrecognized tag in argument ‘%s’"
                                ,      node.name,                               tag_val)
                        else:
                            val = clean_name(tag_val)
                        if  val == None:
                            CFG[cfg_key].pop(key,None)
                        elif val in _OPTIONS:
                            CFG[cfg_key][key] = val # menu
                            _log.debug('CFG set to arg @%s ‘%s’=‘%s’'
                                ,                   cfg_key,key,val)
                        else:
                            _log.warn("node ‘%s’ has unrecognized value in argument ‘%s’, expecting one of: null %s"
                                ,       node.name,                              tag_val,' '.join(_OPTIONS.keys()))
                    elif not args:
                        _log.warn("node ‘%s’ is missing arguments in its child ‘%s’"
                            ,           cfg_key ,                          node.name)
                    if len(args) > 1:
                        _log.warn("node ‘%s’ has extra arguments in its child ‘%s’, only the 1st was used ‘%s’"
                            ,           cfg_key ,                         node.name   ,       {', '.join(args)})
                node = node_parent

                nprops = node.getProps((...,...)) if nvcfg.KDLV == 2 else node.props.items()
                for key,tag_val in nprops: # 2. m=menu key=value pairs
                    if hasattr(tag_val,'value'): #‘=(t)‘’ if (t) exists (though shouldn't)
                        val = clean_name(tag_val.value) # ignore tag
                        _log.warn("node ‘%s’ has unrecognized tag  property ‘%s=%s’"
                            ,       node.name,                              key,tag_val)
                    else:
                        val = clean_name(tag_val)
                    # val = tag_val.value if hasattr(tag_val,'value') else tag_val
                    if  val == None:
                        CFG[cfg_key].pop(key,None)
                    elif val in _OPTIONS:
                        CFG[cfg_key][key] = val # menu
                        _log.debug('CFG set to prop @%s %s=%s'
                            ,                   cfg_key,key,val)
                    else:
                        _log.warn("node ‘%s’ has unrecognized value in property ‘%s=%s’, expecting one of: null %s"
                            ,       node.name,                                  key,tag_val,' '.join(_OPTIONS.keys()))
                # elif not node.props:
                    # _log.warn("node ‘%s’ is missing missing key=value properties",cfg_key)
    else:
        CFG = copy.deepcopy(DEF) # copy defaults to be able to reset values on config reload



@register(seqs.SEQ['[l'], (NORMAL, VISUAL))
@register_text(['UnimpairedContextPrev'], (NORMAL, VISUAL))
class UnimpairedContextPrev(ViOperatorDef):
    def init(self):
        self.command      = 'nv_unimpaired'
        self.command_args = {'action':'context_previous'}
@register(seqs.SEQ[']l'], (NORMAL, VISUAL))
@register_text(['UnimpairedContextNext'],seqs.SEQ[']l'], (NORMAL, VISUAL))
class UnimpairedContextNext(ViOperatorDef):
    def init(self):
        self.command     	= 'nv_unimpaired'
        self.command_args	= {'action':'context_next'}


@register(seqs.SEQ['[n'], (NORMAL, VISUAL, VISUAL_LINE))
@register_text(['UnimpairedGotoPrevConflictMarker'], (NORMAL, VISUAL, VISUAL_LINE))
class UnimpairedGotoPrevConflictMarker(ViOperatorDef):
    def init(self):
        self.updates_xpos    	= True
        self.scroll_into_view	= True
        self.command         	= 'nv_unimpaired'
        self.command_args    	= {'action':'goto_prev_conflict_marker'}
@register(seqs.SEQ[']n'], (NORMAL, VISUAL, VISUAL_LINE))
@register_text(['UnimpairedGotoNextConflictMarker'],seqs.SEQ[']n'], (NORMAL, VISUAL, VISUAL_LINE))
class UnimpairedGotoNextConflictMarker(ViOperatorDef):
    def init(self):
        self.updates_xpos    	= True
        self.scroll_into_view	= True
        self.command         	= 'nv_unimpaired'
        self.command_args    	= {'action':'goto_next_conflict_marker'}


@register(seqs.SEQ['[␠'], (NORMAL,))
@register_text(['UnimpairedBlankUp'], (NORMAL,))
class UnimpairedBlankUp(ViOperatorDef):
    def init(self):
        self.command     	= 'nv_unimpaired'
        self.command_args	= {'action':'blank_up'}
@register(seqs.SEQ[']␠'], (NORMAL,))
@register_text(['UnimpairedBlankDown'],seqs.SEQ[']␠'], (NORMAL,))
class UnimpairedBlankDown(ViOperatorDef):
    def init(self):
        self.command     	= 'nv_unimpaired'
        self.command_args	= {'action':'blank_down'}


@register(seqs.SEQ['[b'], (NORMAL,))
@register_text(['UnimpairedBufPrev'], (NORMAL,))
class UnimpairedBufPrev(ViOperatorDef):
    def init(self):
        self.command     	= 'nv_unimpaired'
        self.command_args	= {'action':'bprevious'}
@register(seqs.SEQ[']b'], (NORMAL,))
@register_text(['UnimpairedBufNext'],seqs.SEQ[']b'], (NORMAL,))
class UnimpairedBufNext(ViOperatorDef):
    def init(self):
        self.command     	= 'nv_unimpaired'
        self.command_args	= {'action':'bnext'}
@register(seqs.SEQ['[⇧b'], (NORMAL,))
@register_text(['UnimpairedBufFirst'], (NORMAL,))
class UnimpairedBufFirst(ViOperatorDef):
    def init(self):
        self.command     	= 'nv_unimpaired'
        self.command_args	= {'action':'bfirst'}
@register(seqs.SEQ[']⇧b'], (NORMAL,))
@register_text(['UnimpairedBufLast'],seqs.SEQ[']⇧b'], (NORMAL,))
class UnimpairedBufLast(ViOperatorDef):
    def init(self):
        self.command     	= 'nv_unimpaired'
        self.command_args	= {'action':'blast'}


@register(seqs.SEQ['[t'], (NORMAL,))
@register_text(['UnimpairedTabpPevious'], (NORMAL,))
class UnimpairedTabPrev(ViOperatorDef):
    def init(self):
        self.command     	= 'nv_unimpaired'
        self.command_args	= {'action':'tabprevious'}
@register(seqs.SEQ[']t'], (NORMAL,))
@register_text(['UnimpairedTabNext'],seqs.SEQ[']t'], (NORMAL,))
class UnimpairedTabNext(ViOperatorDef):
    def init(self):
        self.command     	= 'nv_unimpaired'
        self.command_args	= {'action':'tabnext'}
@register(seqs.SEQ['[⇧t'], (NORMAL,))
@register_text(['UnimpairedTabFirst'], (NORMAL,))
class UnimpairedTabFirst(ViOperatorDef):
    def init(self):
        self.command     	= 'nv_unimpaired'
        self.command_args	= {'action':'tabfirst'}
@register(seqs.SEQ[']⇧t'], (NORMAL,))
@register_text(['UnimpairedTabLast'],seqs.SEQ[']⇧t'], (NORMAL,))
class UnimpairedTabLast(ViOperatorDef):
    def init(self):
        self.command     	= 'nv_unimpaired'
        self.command_args	= {'action':'tablast'}


@register(seqs.SEQ['[e'], (NORMAL,))
@register_text(['UnimpairedMoveUp'], (NORMAL,))
class UnimpairedMoveUp(ViOperatorDef):
    def init(self):
        self.command     	= 'nv_unimpaired'
        self.command_args	= {'action':'move_up'}
@register(seqs.SEQ[']e'], (NORMAL,))
@register_text(['UnimpairedMoveDown'],seqs.SEQ[']e'], (NORMAL,))
class UnimpairedMoveDown(ViOperatorDef):
    def init(self):
        self.command     	= 'nv_unimpaired'
        self.command_args	= {'action':'move_down'}


class OptionMixin(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True
        self.input_parser = InputParser(InputParser.IMMEDIATE)

    @property
    def accept_input(self) -> bool:
        return self.inp == ''

    def accept(self, key: str) -> bool:
        self.inp += translate_char(key)

        return True


@register(seqs.SEQ['co'], (NORMAL,))
@register(seqs.SEQ['yo'], (NORMAL,))
@register_text(['UnimpairedToggle'], (NORMAL,))
class UnimpairedToggle(OptionMixin):
    def translate(self, view):
        return translate_action(view, 'nv_unimpaired', {
            'action': 'toggle_option',
            'name': self.inp
        })


@register(seqs.SEQ['[o'], (NORMAL,))
@register_text(['UnimpairedToggleOn'], (NORMAL,))
class UnimpairedToggleOn(OptionMixin):
    def translate(self, view):
        return translate_action(view, 'nv_unimpaired', {
            'action': 'enable_option',
            'name': self.inp
        })


@register(seqs.SEQ[']o'], (NORMAL,))
@register_text(['UnimpairedToggleOff'],seqs.SEQ[']o'], (NORMAL,))
class UnimpairedToggleOff(OptionMixin):
    def translate(self, view):
        return translate_action(view, 'nv_unimpaired', {
            'action': 'disable_option',
            'name': self.inp
        })


_CONFLICT_MARKER_REGEX = '^(<<<<<<< |=======$|>>>>>>> )'


def _goto_prev_conflict_marker(view, mode: str, count: int) -> None:
    def f(view, s):
        for i in range(0, count):
            match = view_rfind(view, _CONFLICT_MARKER_REGEX, s.b)
            if not match:
                break

            target = match.begin()

            _resolve_conflict_marker_target(view, mode, s, target)

        return s

    regions_transformer(view, f)


def _goto_next_conflict_marker(view, mode, count: int) -> None:
    def f(view, s):
        for i in range(0, count):
            match = view_find(view, _CONFLICT_MARKER_REGEX, s.b + 1)
            if not match:
                break

            target = match.begin()

            _resolve_conflict_marker_target(view, mode, s, target)

        return s

    regions_transformer(view, f)


def _resolve_conflict_marker_target(view, mode: str, s, target: int) -> None:
    if mode == NORMAL:
        resolve_normal_target(s, target)
    elif mode == VISUAL:
        resolve_visual_target(s, target)
    elif mode == VISUAL_LINE:
        resolve_visual_line_target(view, s, target)
    elif mode == INTERNAL_NORMAL:
        resolve_normal_target(s, target)


# Go to the previous [count] lint error.
def _context_previous(window, count: int) -> None:
    window.run_command('sublime_linter_goto_error', {
        'direction': 'previous',
        'count': count
    })


# Go to the next [count] lint error.
def _context_next(window, count: int) -> None:
    window.run_command('sublime_linter_goto_error', {
        'direction': 'next',
        'count': count
    })


# Exchange the current line with [count] lines below it.
def _move_down(view, count: int) -> None:
    for i in range(count):
        view.run_command('swap_line_down')


# Exchange the current line with [count] lines above it.
def _move_up(view, count: int) -> None:
    for i in range(count):
        view.run_command('swap_line_up')


# Add [count] blank lines below the cursor.
def _blank_down(view, edit, count: int) -> None:
    end_point = view.size()
    new_sels = []
    for sel in view.sel():
        line = view.line(sel)

        if line.empty():
            new_sels.append(line.b)
        else:
            new_sels.append(view.find('[^\\s]', line.begin()).begin())

        view.insert(
            edit,
            line.end() + 1 if line.end() < end_point else end_point,
            '\n' * count
        )

    if new_sels:
        set_selection(view, new_sels)


# Add [count] blank lines above the cursor.
def _blank_up(view, edit, count: int) -> None:
    new_sels = []
    for sel in view.sel():
        line = view.line(sel)
        if line.empty():
            new_sels.append(line.b + count)
        else:
            new_sels.append(view.find('[^\\s]', line.begin()).begin() + count)

        view.insert(
            edit,
            line.begin() - 1 if line.begin() > 0 else 0,
            '\n' * count
        )

    if new_sels:
        set_selection(view, new_sels)


def _set_bool_option(view, key: str, flag: bool = None) -> None:
    settings = view.settings()
    value = settings.get(key)

    if flag is None:
        settings.set(key, not value)
    elif flag:
        if not value:
            settings.set(key, True)
    else:
        if value:
            settings.set(key, False)


def _do_toggle_option(view, name: str, flag: bool = None) -> None:
    if flag is None:
        toggle_option(view, name)
    else:
        set_option(view, name, flag)


def _list_option(view, flag: bool) -> None:
    _do_toggle_option(view, 'list', flag)


def _hlsearch_option(view, flag: bool) -> None:
    _do_toggle_option(view, 'hlsearch', flag)


def _ignorecase_option(view, flag: bool) -> None:
    _do_toggle_option(view, 'ignorecase', flag)


def _menu_option(view, flag: bool = None) -> None:
    set_window_ui_element_visible('menu', flag, view.window())


def _minimap_option(view, flag: bool = None) -> None:
    set_window_ui_element_visible('minimap', flag, view.window())


def _sidebar_option(view, flag: bool = None) -> None:
    set_window_ui_element_visible('sidebar', flag, view.window())


def _statusbar_option(view, flag: bool = None) -> None:
    set_window_ui_element_visible('status_bar', flag, view.window())


# Used by the _toggle_option() function.
# * None: means the option is not implemented.
# * str: means the option is a boolean option.
# * tuple: means the many str.
# * function: means it is a complex option.
_OPTIONS = {
    'background': None,
    'crosshairs': None,
    'cursorcolumn': None,
    'cursorline': ('highlight_line', 'highlight_gutter'),
    'diff': None,
    'hlsearch': _hlsearch_option,
    'ignorecase': _ignorecase_option,
    'list': _list_option,
    'menu': _menu_option,  # non standard i.e. not in the original Unimpaired plugin
    'minimap': _minimap_option,  # non standard i.e. not in the original Unimpaired plugin
    'number': 'line_numbers',
    'relativenumber': 'relative_line_numbers',
    'sidebar': _sidebar_option,  # non standard i.e. not in the original Unimpaired plugin
    'spell': 'spell_check',
    'statusbar': _statusbar_option,  # non standard i.e. not in the original Unimpaired plugin
    'virtualedit': None,
    'wrap': 'word_wrap'
}


def _toggle_option(view, key, value=None) -> None:
    if key in CFG['option']:
        key = CFG['option'][key]

    if key not in _OPTIONS:
        raise ValueError('unknown option')

    option = _OPTIONS[key]
    if not option:
        raise ValueError('option is not implemented')

    if   isinstance(option, str  ):
        _set_bool_option    (view, option, value)
    elif isinstance(option, tuple):
        for opt in option:
            _set_bool_option(view, opt   , value)
    elif callable(option):
        option              (view,         value)
    else:
        raise ValueError('unknown option type')


class nv_unimpaired_command(TextCommand):
    def run(self, edit, action, mode=None, count=1, register=None, **kwargs):
        if   action == 'move_down':
            _move_down                (self.view         ,             count)
        elif action == 'move_up':
            _move_up                  (self.view         ,             count)
        elif action == 'blank_down':
            _blank_down               (self.view         , edit,       count)
        elif action == 'blank_up':
            _blank_up                 (self.view         , edit,       count)
        elif action in ('bnext', 'bprevious', 'bfirst', 'blast'):
            window_buffer_control     (self.view.window(), action[1:], count)
        elif action in ('tabnext', 'tabprevious', 'tabfirst', 'tablast'):
            window_tab_control        (self.view.window(), action[3:], count)
        elif action == 'goto_next_conflict_marker':
            _goto_next_conflict_marker(self.view         , mode,       count)
        elif action == 'goto_prev_conflict_marker':
            _goto_prev_conflict_marker(self.view         , mode,       count)
        elif action == 'context_next':
            _context_next             (self.view.window(),             count)
        elif action == 'context_previous':
            _context_previous         (self.view.window(),             count)
        elif action == 'toggle_option':
            _toggle_option            (self.view         , kwargs.get('name')       )
        elif action == 'enable_option':
            _toggle_option            (self.view         , kwargs.get('name'), True )
        elif action == 'disable_option':
            _toggle_option            (self.view         , kwargs.get('name'), False)
        else:
            raise ValueError('unknown action')
