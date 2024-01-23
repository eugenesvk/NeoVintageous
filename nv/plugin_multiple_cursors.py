# A port of https://github.com/terryma/vim-multiple-cursors.

from NeoVintageous.nv.plugin import register, register_text
from NeoVintageous.nv.vi import seqs
from NeoVintageous.nv.vi.cmd_base import ViOperatorDef
from NeoVintageous.nv.vim import ACTION_MODES
from NeoVintageous.nv.modes import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE


__all__ = []  # type: list


@register(seqs.SEQ['⎈n'], ACTION_MODES)
@register(seqs.SEQ['gh'], ACTION_MODES)
@register_text(['MultipleCursorsStart'], ACTION_MODES)
class MultipleCursorsStart(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_enter_select_mode'


@register(seqs.SEQ['⇧j'], (SELECT,))
@register(seqs.SEQ['⭾'], (SELECT,))
@register(seqs.SEQ['⎋'], (SELECT,))
@register_text(['MultipleCursorsExit'], (SELECT,))
class MultipleCursorsExit(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True
        self.command = 'nv_vi_select_big_j'


@register(seqs.SEQ['⎈n'], (SELECT,))
@register(seqs.SEQ['j'], (SELECT,))
@register(seqs.SEQ['n'], (SELECT,))
@register_text(['MultipleCursorsAdd'], (SELECT,))
class MultipleCursorsAdd(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_select_j'


@register(seqs.ALT_N, (SELECT,))
@register(seqs.SEQ['⧵⧵⇧a'], (SELECT,))
@register(seqs.SEQ['⇧a'], (SELECT,)) # DEPRECATED; use \\A instead and change A to append
@register_text(['MultipleCursorsAddAll'], (SELECT,))
class MultipleCursorsAddAll(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_big_a'


@register(seqs.SEQ['⎈p'], (SELECT,))
@register(seqs.SEQ['k'], (SELECT,))
@register(seqs.SEQ['⇧n'], (SELECT,))
@register(seqs.SEQ['⇧q'], (SELECT,))
@register_text(['MultipleCursorsRemove'], (SELECT,))
class MultipleCursorsRemove(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_select_k'


@register(seqs.SEQ['⎈x'], (SELECT,))
@register(seqs.SEQ['l'], (SELECT,))
@register(seqs.SEQ['q'], (SELECT,))
@register_text(['MultipleCursorsSkip'], (SELECT,))
class MultipleCursorsSkip(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'find_under_expand_skip'


@register(seqs.SEQ['g⇧h'], ACTION_MODES)
@register_text(['MultipleCursorsAll'], ACTION_MODES)
class MultipleCursorsAll(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_g_big_h'
