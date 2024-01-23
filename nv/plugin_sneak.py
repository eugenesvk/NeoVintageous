# A Port of https://github.com/justinmk/vim-sneak.

import os

from sublime import IGNORECASE
from sublime import LITERAL
from sublime_plugin import TextCommand

from NeoVintageous.nv.options import get_option
from NeoVintageous.nv.plugin import register, register_text
from NeoVintageous.nv.polyfill import set_selection
from NeoVintageous.nv.polyfill import view_find_all_in_range
from NeoVintageous.nv.polyfill import view_rfind_all
from NeoVintageous.nv.search import add_search_highlighting
from NeoVintageous.nv.search import clear_search_highlighting
from NeoVintageous.nv.search import is_smartcase_pattern
from NeoVintageous.nv.settings import get_internal_setting
from NeoVintageous.nv.settings import get_setting
from NeoVintageous.nv.settings import set_internal_setting
from NeoVintageous.nv.settings import set_last_char_search_command
from NeoVintageous.nv.ui import ui_bell
from NeoVintageous.nv.utils import InputParser
from NeoVintageous.nv.utils import get_insertion_point_at_b
from NeoVintageous.nv.utils import resolve_visual_line_target
from NeoVintageous.nv.utils import resolve_visual_target
from NeoVintageous.nv.utils import translate_char
from NeoVintageous.nv.vi import seqs
from NeoVintageous.nv.vi.cmd_base import ViMotionDef
from NeoVintageous.nv.vi.cmd_base import translate_motion
from NeoVintageous.nv.modes import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE


__all__ = ['nv_sneak_command']


def _get_env(name: str, default) -> str:
    seq = os.getenv(name)
    return seq if seq else default


_SNEAK_S = _get_env('NEOVINTAGEOUS_SNEAK_MAP_S', seqs.SEQ['s'])
_SNEAK_BIG_S = _get_env('NEOVINTAGEOUS_SNEAK_MAP_BIG_S', seqs.SEQ['⇧s'])
_SNEAK_Z = _get_env('NEOVINTAGEOUS_SNEAK_MAP_Z', seqs.SEQ['z'])
_SNEAK_BIG_Z = _get_env('NEOVINTAGEOUS_SNEAK_MAP_BIG_Z', seqs.SEQ['⇧z'])


class SneakInputMotion(ViMotionDef):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True
        self.input_parser = InputParser(InputParser.IMMEDIATE)

    @property
    def accept_input(self):
        return len(self.inp) < 2 and self.inp != '\n'

    def accept(self, key: str):
        self.inp += translate_char(key)

        return True


# @register(seqs.SEQ['s'], (NORMAL, VISUAL, VISUAL_LINE))
# @register(seqs.SEQ['z'], (OPERATOR_PENDING,))
@register(_SNEAK_S, (NORMAL, VISUAL, VISUAL_LINE))
@register(_SNEAK_Z, (OPERATOR_PENDING,))
@register_text(['Sneak'], (NORMAL, VISUAL, VISUAL_LINE, OPERATOR_PENDING))
class Sneaks(SneakInputMotion):
    def translate(self, view):
        return translate_motion(view, 'nv_sneak', {
            'search': self.inp.rstrip()
        })


# @register(seqs.SEQ['⇧s'], (NORMAL,))
# @register(seqs.SEQ['⇧z'], (VISUAL, VISUAL_LINE, OPERATOR_PENDING))
@register(_SNEAK_BIG_S, (NORMAL,))
@register(_SNEAK_BIG_Z, (VISUAL, VISUAL_LINE, OPERATOR_PENDING))
@register_text(['SneakBack'], (NORMAL, VISUAL, VISUAL_LINE, OPERATOR_PENDING))
class SneakS(SneakInputMotion):
    def translate(self, view):
        return translate_motion(view, 'nv_sneak', {
            'search': self.inp.rstrip(),
            'forward': False
        })


def _get_last_sneak_search(view) -> str:
    return get_internal_setting(view.window(), 'last_sneak_search')


def _set_last_sneak_search(view, command: str, search: str) -> None:
    set_last_char_search_command(view, command)
    set_internal_setting(view.window(), 'last_sneak_search', search)


def _get_search_flags(view, search: str) -> int:
    flags = LITERAL

    if search and get_setting(view, 'sneak_use_ic_scs') == 1:
        if get_option(view, 'ignorecase') and not is_smartcase_pattern(view, search):
            flags |= IGNORECASE

    return flags


class nv_sneak_command(TextCommand):
    def run(self, edit, mode, count, search=None, forward=True, save=True):
        if len(self.view.sel()) != 1:
            ui_bell('sneak does not support multiple cursors')
            return

        if not search:
            search = _get_last_sneak_search(self.view)
            if not search:
                ui_bell('no previous sneak search')
                return

        clear_search_highlighting(self.view)

        flags = _get_search_flags(self.view, search)
        s = self.view.sel()[0]
        start_pt = get_insertion_point_at_b(s)

        if forward:
            occurrences = view_find_all_in_range(self.view, search, start_pt + 1, self.view.size(), flags)
        else:
            occurrences = list(view_rfind_all(self.view, search, start_pt, flags))

        occurrences = occurrences[count - 1:]

        if not occurrences:
            ui_bell('not found: %s' % search)
            return

        target = occurrences[0].a

        if mode == NORMAL:
            s.a = s.b = target
        elif mode == VISUAL:
            resolve_visual_target(s, target)
        elif mode == VISUAL_LINE:
            resolve_visual_line_target(self.view, s, target)
        elif mode == INTERNAL_NORMAL:
            s.b = target
        else:
            return

        set_selection(self.view, s)
        add_search_highlighting(self.view, occurrences)

        if save:
            _set_last_sneak_search(self.view, 'sneak_s' if forward else 'sneak_big_s', search)
