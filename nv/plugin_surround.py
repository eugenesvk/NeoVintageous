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

# A port of https://github.com/tpope/vim-surround.

import re
import logging

from sublime import Region
from sublime_plugin import TextCommand

from NeoVintageous.nv.plugin import register
from NeoVintageous.nv.polyfill import view_find
from NeoVintageous.nv.utils import InputParser
from NeoVintageous.nv.utils import translate_char
from NeoVintageous.nv.vi import seqs
from NeoVintageous.nv.vi.cmd_base import ViOperatorDef
from NeoVintageous.nv.vi.cmd_base import translate_action
from NeoVintageous.nv.vi.search import reverse_search
from NeoVintageous.nv.vi.text_objects import get_text_object_region
from NeoVintageous.nv.modes import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE
from NeoVintageous.nv.vim import enter_normal_mode
from NeoVintageous.nv.vim import run_motion

from NeoVintageous.nv.rc import cfgU

from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL
_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)

__all__ = ['nv_surround_command']


class nv_surround_command(TextCommand):
    def run(self, edit, action, **kwargs):
        if action == 'cs':
            _do_replace(self.view, edit, **kwargs)
        elif action == 'ds':
            _do_delete(self.view, edit, **kwargs)
        elif action == 'ys':
            _do_add(self.view, edit, **kwargs)


@register(seqs.SEQ['ys'], (NORMAL,))
class Surroundys(ViOperatorDef):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True
        self.repeatable = True
        self.motion_required = True
        self.input_parser = InputParser(InputParser.AFTER_MOTION)

    @property
    def accept_input(self) -> bool:
        if not self.inp:
            return True

        # Function
        if self.inp[0] in ('f', 'F') or self.inp.lower().startswith('<c-f>'):
            return self.inp[-1] != '\n'

        # Tag
        if self.inp[0] in ('t', '<'):
            return _should_tag_accept_input(self.inp)

        return False

    def accept(self, key: str) -> bool:
        self.inp += translate_char(key)

        return True

    def translate(self, view):
        return translate_action(view, 'nv_surround', {
            'action': 'ys',
            'replacement': self.inp
        })


@register(seqs.YSS, (NORMAL,))
class Surroundyss(Surroundys):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.motion_required = False
        self.input_parser = InputParser(InputParser.IMMEDIATE)

    def translate(self, view):
        return translate_action(view, 'nv_surround', {
            'action': 'ys',
            'motion': {
                'motion': 'nv_vi_select_text_object',
                'motion_args': {
                    'mode': INTERNAL_NORMAL,
                    'count': 1,
                    'inclusive': False,
                    'text_object': 'l'
                }
            },
            'replacement': self.inp
        })


@register(seqs.SEQ['⇧s'], (VISUAL, VISUAL_LINE, VISUAL_BLOCK))
class SurroundS(Surroundys):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.motion_required = False
        self.input_parser = InputParser(InputParser.IMMEDIATE)


@register(seqs.SEQ['ds'], (NORMAL, OPERATOR_PENDING))
class Surroundds(ViOperatorDef):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True
        self.repeatable = True
        self.input_parser = InputParser(InputParser.IMMEDIATE)

    # TODO Fix ds should not accept input
    @property
    def accept_input(self) -> bool:
        single = len(self.inp) == 1
        tag = re.match('<.*?>', self.inp)

        return not (single or tag)

    def accept(self, key: str) -> bool:
        self.inp += translate_char(key)

        return True

    def translate(self, view):
        return translate_action(view, 'nv_surround', {
            'action': 'ds',
            'target': self.inp
        })


@register(seqs.SEQ['cs'], (NORMAL, OPERATOR_PENDING))
class Surroundcs(ViOperatorDef):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True
        self.repeatable = True
        self.input_parser = InputParser(InputParser.IMMEDIATE)

    @property
    def accept_input(self) -> bool:
        if not self.inp:
            return True

        # Requires at least two characters, a target and a replacement.
        if len(self.inp) < 2:
            return True

        # Tag
        if self.inp[1] in ('t', '<'):
            return _should_tag_accept_input(self.inp[1:])

        return False

    def accept(self, key: str) -> bool:
        self.inp += translate_char(key)

        return True

    def translate(self, view):
        return translate_action(view, 'nv_surround', {
            'action': 'cs',
            'target': self.inp[0],
            'replacement': self.inp[1:]
        })


_PUNCTUATION_MARKS = {
    '(': ('(', ')'),
    ')': ('(', ')'),
    '{': ('{', '}'),
    '}': ('{', '}'),
    '[': ('[', ']'),
    ']': ('[', ']'),
    '<': ('<', '>'),
    '>': ('<', '>'),
}
_PUNCTUTION_MARK_ALIASES = {
    'b': ')',
    'B': '}',
    'r': ']',
    'a': '>',
}
_APPEND_SPACE_TO_CHARS = '({['
_STEADY_CURSOR = dict()
for key in (_STEADY_CURSOR_KEY := ['add','replace','delete']):
    _STEADY_CURSOR[key] = True
VALID_TARGETS  = 'ra@' # Delete targets
VALID_TARGETS += '\'"`b()B{}[]<>t.,-_;:#~*\\/|+=&$' # targets for plugin github.com/wellle/targets.vim
#IilpsWw plugin targets excluded

def reload_with_user_data_kdl() -> None:
    if hasattr(cfgU,'cfg_kdl') and (cfg := cfgU.cfg_kdl.get('surround',None)): # skip on initial import when Plugin API isn't ready, so not settings are loaded
        global _PUNCTUATION_MARKS, _PUNCTUTION_MARK_ALIASES, _APPEND_SPACE_TO_CHARS, _STEADY_CURSOR, VALID_TARGETS
        if (node := cfg.get('punctuationmarks'  ,None)): # ‘=‘’ “=“” key-value pairs
            # _log.debug(f"@plugin surround: Parsing config punctuationmarks")
            for i,key in enumerate(prop_d := node.props): #‘=‘’
                tag_val = prop_d[key] #‘=(t)‘’ if (t) exists (though shouldn't)
                val = tag_val.value if hasattr(tag_val,'value') else tag_val
                if len(v_split := re.split(R'\s+',val)) > 1:
                    _PUNCTUATION_MARKS[key] = (v_split[0],v_split[1]) # `'   '
                elif (_len := len(val)) == 2:
                    _PUNCTUATION_MARKS[key] = (val[0]    ,val[1])     # ‘    ’
                else:
                    _log.warn(f"node ‘{node.name}’ ‘{key}’ should have an argument of length 2, not ‘{_len}’")
            if not node.props:
                _log.warn(f"node ‘{node.name}’ is missing key=value properties")
        if (node := cfg.get('punctuationalias'  ,None)): # clear g=‘ key-value pairs
            # _log.debug(f"@plugin surround: Parsing config punctuationalias")
            if 'clear' in node.args:
                _PUNCTUTION_MARK_ALIASES.clear()
            for i,key in enumerate(prop_d := node.props): #d="("
                tag_val = prop_d[key] #d=(t)( if (t) exists (though shouldn't)
                val = tag_val.value if hasattr(tag_val,'value') else tag_val
                _PUNCTUTION_MARK_ALIASES[key] = val
            if not node.props:
                _log.warn(f"node ‘{node.name}’ is missing key=value properties")
        if (node := cfg.get('appendspacetochars',None)): # )}]
            # _log.debug(f"@plugin surround: Parsing config appendspacetochars")
            if (args := node.args):
                _APPEND_SPACE_TO_CHARS = args[0]
            if not args:
                _log.warn(f"node ‘{node.name}’ is missing arguments")
            if len(args) > 1:
                _log.warn(f"node ‘{node.name}’ has extra arguments, only the 1st was used ‘{', '.join(args)}’")
        if (node := cfg.get('steadycursor',None)): # add=true replace=true delete=true
            # _log.debug(f"@plugin surround: Parsing config steadycursor")
            for i,key in enumerate(prop_d := node.props):
                tag_val = prop_d[key] #add=(t)true if (t) exists (though shouldn't)
                val = tag_val.value if hasattr(tag_val,'value') else tag_val
                if key in _STEADY_CURSOR_KEY:
                    _STEADY_CURSOR[key] = val
            if not node.props:
                _log.warn(f"node ‘{node.name}’ is missing key=value properties")
        VALID_TARGETS += "".join(((val:=_PUNCTUATION_MARKS[k])[0]+val[1]) for k in _PUNCTUATION_MARKS) # add marks
        VALID_TARGETS += "".join(_PUNCTUTION_MARK_ALIASES.keys()) # add aliases

# def reload_with_user_data() -> None:
#     if hasattr(cfgU,'surround') and (cfg := cfgU.surround): # skip on initial import when Plugin API isn't ready, so not settings are loaded
#         global _PUNCTUATION_MARKS, _PUNCTUTION_MARK_ALIASES, _APPEND_SPACE_TO_CHARS
#         if (_key := 'punctuation marks') in cfg:
#             for key,value in cfg[_key].items():
#                 if not (_len := len(value)) == 2:
#                     _log.warn(f"‘punctuation marks’ values should have 2 values, not ‘{_len}’ in ‘{value}’")
#                     continue
#                 _PUNCTUATION_MARKS[key] = (value[0], value[1])
#         if (_key := 'punctuation alias') in cfg:
#             _PUNCTUTION_MARK_ALIASES.clear()
#             for key,value in cfg[_key].items():
#                 _PUNCTUTION_MARK_ALIASES[key] = value
#         if (_key := 'append space to chars') in cfg:
#             _APPEND_SPACE_TO_CHARS = cfg[_key]

# Expand target punctuation marks:
  # (){}[]<> represent themselves/their counterparts
  # bBra     aliases for )}]>     )}mirror Vim; ]> are arbitrary and subject to change
  # '"`      quote marks and their counterparts are the same
def _expand_targets(target: str) -> tuple:
    target = _resolve_target_aliases(target) # 'a' to '>'

    return _PUNCTUATION_MARKS.get(target, (target, target)) # '>' to a tuple of (< , >) or self


def _resolve_target_aliases(target: str) -> str:
    return _PUNCTUTION_MARK_ALIASES.get(target, target) # 'a' to '>' or self

# If either ), }, ], or > is used, the text is wrapped in the appropriate pair
# of characters. Similar behavior can be found with (, {, and [ (but not <),
# which append an additional space to the inside. Like with the targets above,
# b, B, r, and a are aliases for ), }, ], and >.
def _expand_replacements(target: str) -> tuple:
    # Function replacement
    if target[0] == 'f':
        return (target[1:].strip() + '(', ')')
    if target[0] == 'F':
        return (target[1:].strip() + '( ', ' )')
    if target.lower().startswith('<c-f>'):
        return ('(' + target[5:].strip() + ' ', ')')

    # Tag replacement
    if target[0] in ('t', '<') and len(target) >= 3:
        append = prefix = ''

        if target.lower().startswith('<c-t>'):
            target = '<' + target[5:]
            append = prefix = '\n'

        # Attributes are stripped in the closing tag. The first character if
        # "t", which is an alias for "<", is replaced too.
        if target[-1] == '\n':
            target = target[0:-1] + '>'

        replacement_a = '<' + target[1:] + append
        replacement_b = prefix + '</' + target[1:].strip()[:-1].strip().split(' ', 1)[0] + '>'

        return (replacement_a, replacement_b)

    # Pair replacement
    target = _resolve_target_aliases(target)
    append_addition_space = True if target in _APPEND_SPACE_TO_CHARS else False
    begin, end = _expand_targets(target)
    if append_addition_space:
        begin = begin + ' '
        end   =         ' ' + end

    return (begin, end)


from sublime import Region
def _rsynced_regions_transformer(view, f, _res_view_sel_reverse:list=[]) -> None:
    sels = reversed(list(view.sel())) # end→beg not to adjust for ∑inserts

    view_sel = view.sel()
    for i,sel in enumerate(sels):
        view_sel.subtract(sel)

        (new_sel, (edit_count_beg,edit_count_end)) = f(view, sel)
        if not isinstance(new_sel, Region):
            raise TypeError('sublime.Region required')

        if _res_view_sel_reverse: # adjust old cursor pos by count of chars inserted @ beg
            old_sel = _res_view_sel_reverse[i]
            (a,b) = old_sel.to_tuple() # → this region as a tuple (a,b)
            old_sel_adjusted = Region(edit_count_beg+a,edit_count_beg+b)
            view_sel.add(old_sel_adjusted)
        else: # or don't adjust anything and just select the new region
            view_sel.add(new_sel)


def _do_replace(view, edit, mode: str, target: str, replacement: str, count=None, register=None) -> None:
    if not target and replacement:
        return

    if len(target) != 1:
        return

    # Replacements must be 1 character long or at least 3 characters for tags.
    if len(replacement) >= 3:
        if replacement[0] not in ('t', '<') or not replacement[-1] in ('>', '\n'):
            return
    elif len(replacement) != 1:
        return

    # Targets.
    target_open, target_close = _expand_targets(target)

    # Replacements
    replacement_open, replacement_close = _expand_replacements(replacement)

    def _f(view, s):
        if mode == INTERNAL_NORMAL:
            if target == 't':
                target_tag_open, target_tag_close = ('<[^>]+>', '<\\/[^>]+>')
                region_begin = None
                region_end = view.find(target_tag_close, s.b)
                if region_end:
                    region_begin = reverse_search(view, target_tag_open, end=region_end.begin(), start=0)
            else:
                region_begin, region_end = _get_regions_for_target(view, s, target_open)

            if not (region_end and region_begin):
                return s

            replacement_a = replacement_open

            # You may specify attributes here and they will be stripped from the
            # closing tag. If replacing a tag, its attributes are kept in the
            # new tag. End your input with > to discard the those attributes.
            if target == 't' and replacement[-1] == '\n':
                match = re.match('<([^ >]+)(.*)>', view.substr(region_begin))
                if match:
                    if replacement_open[-1] == '\n':
                        replacement_a = replacement_open[:-2] + match.group(2) + '>\n'
                    else:
                        replacement_a = replacement_open[:-1] + match.group(2) + '>'

            # It's important that the regions are replaced in reverse because
            # otherwise the buffer size would be reduced by the number of
            # characters replaced and would result in an off-by-n bugs.
            view.replace(edit, region_end, replacement_close)
            view.replace(edit, region_begin, replacement_a)

            return Region(region_begin.begin())

        return s

    _rsynced_regions_transformer(view, _f)


def _do_delete(view, edit, mode: str, target: str, count=None, register=None) -> None:
    if not target:
        return
    if len(target) != 1:
        return
    if target in 'wWsp': # 'word WORD sentence paragraph' have nothing to delete, so noop
        return
    if target not in VALID_TARGETS:
        return

    # Trim contained whitespace for opening punctuation mark targets.
    should_trim_contained_whitespace = True if target in '({[<' else False

    # Targets.
    target_open, target_close = _expand_targets(target) # 'a' or '>' to ''

    def _f(view, s):
        if mode == INTERNAL_NORMAL:
            if target == 't': # a pair of HTML or XML tags
                # TODO test dst works when cursor position is inside tag begin <a|bc>x -> dst -> |x
                # TODO test dst works when cursor position is inside tag end   <abc>x</a|bc> -> dst -> |x
                region_end = view.find('<\\/.*?>', s.b)
                region_begin = reverse_search(view, '<.*?>', start=0, end=s.b)
            else:
                region_begin, region_end = _get_regions_for_target(view, s, target_open)
                if should_trim_contained_whitespace and (region_begin and region_end):
                    region_begin, region_end = _trim_regions(view, region_begin, region_end)

            if not (region_begin and region_end):
                return (s, (0,0))

            # It's important that the regions are replaced in reverse because
            # otherwise the buffer size would be reduced by the number of
            # characters replaced and would result in an off-by-one bug.
            view.replace(edit, region_end, '')
            view.replace(edit, region_begin, '')
            del_count_end = -1 * region_end.size()
            del_count_beg = -1 * region_begin.size()

            return (Region(region_begin.begin()), (del_count_beg,del_count_end))

        return (s, (0,0))

    _res_view_sel_reverse = list()    # save cursor pos as they might be reset elsewhere
    if _STEADY_CURSOR['delete']:
        sels = reversed(list(view.sel())) # end→beg not to adjust for ∑deletes
        for sel in sels:
            _res_view_sel_reverse.append(sel)

    _rsynced_regions_transformer(view, _f, _res_view_sel_reverse)


def _get_regions_for_target(view, s: Region, target: str) -> tuple:
    text_object = get_text_object_region(view, s, target, inclusive=True)
    if not text_object:
        return (None, None)

    begin = Region(text_object.begin(), text_object.begin() + 1)
    end = Region(text_object.end(), text_object.end() - 1)

    return (begin, end)


def _view_rfind(view, sub: str, start: int, end: int, flags: int = 0):
    match = reverse_search(view, sub, start, end, flags)
    if match is None or match.b == -1:
        return None

    return match


def _trim_regions(view, start: Region, end: Region) -> tuple:
    start_ws = view_find(view, '\\s*.', start_pt=start.end())
    if start_ws and start_ws.size() > 1:
        start = Region(start.begin(), start_ws.end() - 1)

    end_ws = _view_rfind(view, '.\\s*', start=start.end(), end=end.begin())
    if end_ws and end_ws.size() > 1:
        end = Region(end_ws.begin() + 1, end.end())

    return (start, end)


from typing import List, Union
def _do_add(view, edit, mode: str = None, motion=None, replacement: str = '"', count: int = 1, register=None) -> None:
    def _surround(view, edit, s, replacement: str) -> List[int]:
        replacement_open, replacement_close = _expand_replacements(replacement) #< > for >
        if replacement_open.startswith('<'):
            ins_count_end = view.insert(edit, s.b, replacement_close)
            ins_count_beg = view.insert(edit, s.a, replacement_open)
            return (ins_count_beg,ins_count_end)

        if mode == VISUAL_LINE:
            replacement_open = replacement_open + '\n'
            replacement_close = replacement_close + '\n'

        ins_count_end = view.insert(edit, s.end(), replacement_close)
        ins_count_beg = view.insert(edit, s.begin(), replacement_open)
        return (ins_count_beg,ins_count_end) # count actual # of inserted chars to be able to calculate old cursor position

    def f(view, s):
        if mode == INTERNAL_NORMAL:
            (ins_count_end,ins_count_beg) = _surround(view, edit, s, replacement)
            return (Region(s.begin()), (ins_count_end,ins_count_beg))
        elif mode in (VISUAL, VISUAL_LINE, VISUAL_BLOCK):
            (ins_count_end,ins_count_beg) = _surround(view, edit, s, replacement)
            return (Region(s.begin()), (ins_count_end,ins_count_beg))
        return s

    if not motion and not view.has_non_empty_selection_region():
        enter_normal_mode(view, mode)
        raise ValueError('motion required')

    _res_view_sel_reverse = list()    # save cursor pos as they are reset in run_motion
    if _STEADY_CURSOR['add']:
        sels = reversed(list(view.sel())) # end→beg not to adjust for ∑inserts
        for sel in sels:
            _res_view_sel_reverse.append(sel)

    if mode == INTERNAL_NORMAL:
        run_motion(view, motion) # add a Word object to selection (moving to Word's end)
        #eg {'motion':'nv_vi_select_text_object','motion_args':{'count':1,'inclusive':False,'mode':'mode_internal_normal','text_object':'w'}}

    if replacement:
        _rsynced_regions_transformer(view, f, _res_view_sel_reverse)

    enter_normal_mode(view, mode)


def _should_tag_accept_input(inp: str) -> bool:
    if inp.lower().startswith('<c-t>'):
        return not re.match('<[Cc]-t>.*?[\n>]', inp)

    return not inp[-1] in ('>', '\n')
