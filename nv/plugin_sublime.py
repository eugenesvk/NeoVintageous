# A plugin to support functionality specific to Sublime Text.

from NeoVintageous.nv.plugin import register, register_text
from NeoVintageous.nv.settings import set_reset_during_init
from NeoVintageous.nv.vi import seqs
from NeoVintageous.nv.vi.cmd_base import ViOperatorDef
from NeoVintageous.nv.vi.cmd_base import translate_builtin_action
from NeoVintageous.nv.vim import ACTION_MODES
from NeoVintageous.nv.modes import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE


__all__ = []  # type: list


@register(seqs.CTRL_ALT_P, ACTION_MODES)
@register_text(['StQuickSwitchProject'],seqs.CTRL_ALT_P, ACTION_MODES)
class StQuickSwitchProject(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.builtin = True
        self.command = 'prompt_select_workspace'


@register(seqs.SEQ['⎈0'], ACTION_MODES)
@register_text(['StFocusSideBar'], ACTION_MODES)
class StFocusSideBar(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.builtin = True
        self.command = 'focus_side_bar'


@register(seqs.SEQ['⎈1'], ACTION_MODES, group=0)
@register(seqs.SEQ['⎈2'], ACTION_MODES, group=1)
@register(seqs.SEQ['⎈3'], ACTION_MODES, group=2)
@register(seqs.SEQ['⎈4'], ACTION_MODES, group=3)
@register(seqs.SEQ['⎈5'], ACTION_MODES, group=4)
@register(seqs.SEQ['⎈7'], ACTION_MODES, group=6)
@register(seqs.SEQ['⎈8'], ACTION_MODES, group=7)
@register(seqs.SEQ['⎈9'], ACTION_MODES, group=8)
@register_text(['StFocusGroup0'], ACTION_MODES, group=0)
@register_text(['StFocusGroup1'], ACTION_MODES, group=1)
@register_text(['StFocusGroup2'], ACTION_MODES, group=2)
@register_text(['StFocusGroup3'], ACTION_MODES, group=3)
@register_text(['StFocusGroup4'], ACTION_MODES, group=4)
@register_text(['StFocusGroup6'], ACTION_MODES, group=6)
@register_text(['StFocusGroup7'], ACTION_MODES, group=7)
@register_text(['StFocusGroup8'], ACTION_MODES, group=8)
class StFocusGroup(ViOperatorDef):
    def __init__(self, *args, group=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._serializable.append('_group')
        self._group = group
        self.updates_xpos = True
        self.scroll_into_view = True
        self.builtin = True

    def translate(self, view):
        return translate_builtin_action('focus_group', {
            'group': self._group
        })


@register(seqs.CTRL_K_CTRL_B, ACTION_MODES)
@register_text(['StToggleSideBar'],seqs.CTRL_K_CTRL_B, ACTION_MODES)
class StToggleSideBar(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.builtin = True
        self.command = 'toggle_side_bar'


@register(seqs.COMMAND_P, ACTION_MODES)
@register(seqs.SEQ['⎈p'], ACTION_MODES)
@register_text(['StGotoAnything'], ACTION_MODES)
class StGotoAnything(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.builtin = True
        self.command = 'show_overlay'
        self.command_args = {
            'overlay': 'goto',
            'show_files': True
        }


@register(seqs.COMMAND_BIG_B, ACTION_MODES)
@register(seqs.CTRL_BIG_B, ACTION_MODES)
@register_text(['StBuildWith'],seqs.CTRL_BIG_B, ACTION_MODES)
class StBuildWith(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.builtin = True
        self.command = 'build'
        self.command_args = {
            'select': True
        }


@register(seqs.COMMAND_BIG_F, ACTION_MODES)
@register(seqs.CTRL_BIG_F, ACTION_MODES)
@register_text(['StFindInFiles'],seqs.CTRL_BIG_F, ACTION_MODES)
class StFindInFiles(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.builtin = True
        self.command = 'show_panel'
        self.command_args = {
            'panel': 'find_in_files'
        }


@register(seqs.COMMAND_BIG_P, ACTION_MODES + (INSERT,))
@register(seqs.CTRL_BIG_P, ACTION_MODES + (INSERT,))
@register_text(['StCommandPalette'],seqs.CTRL_BIG_P, ACTION_MODES + (INSERT,))
class StCommandPalette(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.builtin = True

    def translate(self, view):
        set_reset_during_init(view, False)

        return translate_builtin_action('show_overlay', {
            'overlay': 'command_palette'
        })


@register(seqs.SEQ['⇧F3'], ACTION_MODES)
@register_text(['StFindPrev'], ACTION_MODES)
class StFindPrev(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.builtin          = True
        self.command          = 'find_prev'
@register(seqs.SEQ['F3'], ACTION_MODES)
@register_text(['StFindNext'], ACTION_MODES)
class StFindNext(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.builtin          = True
        self.command          = 'find_next'


@register(seqs.SEQ['F6'], ACTION_MODES)
@register_text(['StToggleSpellCheck'], ACTION_MODES)
class StToggleSpellCheck(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.builtin = True
        self.command = 'toggle_setting'
        self.command_args = {
            'setting': 'spell_check'
        }


@register(seqs.SEQ['F7'], ACTION_MODES)
@register_text(['StBuild'], ACTION_MODES)
class StBuild(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.builtin = True
        self.command = 'build'


@register(seqs.SEQ['F9'], ACTION_MODES)
@register_text(['StSortLines'], ACTION_MODES)
class StSortLines(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'sort_lines'
        self.builtin = True
        self.command_args = {
            'case_sensitive': False
        }


@register(seqs.SEQ['F11'], ACTION_MODES)
@register_text(['StToggleFullScreen'], ACTION_MODES)
class StToggleFullScreen(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.builtin = True
        self.command = 'toggle_full_screen'


@register(seqs.SEQ['F12'], ACTION_MODES)
@register_text(['StGotoDefinition'], ACTION_MODES)
class StGotoDefinition(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.builtin = True
        self.command = 'goto_definition'


@register(seqs.SEQ['⎈F12'], ACTION_MODES)
@register_text(['StGotoSymbol'], ACTION_MODES)
class StGotoSymbol(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.builtin = True
        self.command = 'show_overlay'
        self.command_args = {
            'overlay': 'goto',
            'text': '@'
        }


@register(seqs.SEQ['⇧F4'], ACTION_MODES)
@register_text(['StResultPrev','StPrevResult'], ACTION_MODES)
class StPrevResult(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.builtin          = True
        self.command          = 'prev_result'
@register(seqs.SEQ['F4'], ACTION_MODES)
@register_text(['StResultNext','StNextResult'], ACTION_MODES)
class StNextResult(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.builtin          = True
        self.command          = 'next_result'


@register(seqs.SEQ['⇧F11'], ACTION_MODES)
@register_text(['StToggleDistractionFree'], ACTION_MODES)
class StToggleDistractionFree(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.builtin = True
        self.command = 'toggle_distraction_free'


@register(seqs.SEQ['⇧F2'], ACTION_MODES)
@register_text(['StPrevBookmark'], ACTION_MODES)
class StPrevBookmark(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.builtin          = True
        self.command          = 'prev_bookmark'
@register(seqs.SEQ['F2'], ACTION_MODES)
@register_text(['StNextBookmark'], ACTION_MODES)
class StNextBookmark(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.builtin          = True
        self.command          = 'next_bookmark'
@register(seqs.SEQ['⎈F2'], ACTION_MODES)
@register_text(['StToggleBookmark'], ACTION_MODES)
class StToggleBookmark(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.builtin          = True
        self.command          = 'toggle_bookmark'
@register(seqs.SEQ['⇧⎈F2'], ACTION_MODES)
@register_text(['StClearBookmarks'], ACTION_MODES)
class StClearBookmarks(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.builtin          = True
        self.command          = 'clear_bookmarks'


@register(seqs.SEQ['⇧⎈F12'], ACTION_MODES)
@register_text(['StGotoSymbolInProject'], ACTION_MODES)
class StGotoSymbolInProject(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.builtin = True
        self.command = 'goto_symbol_in_project'
