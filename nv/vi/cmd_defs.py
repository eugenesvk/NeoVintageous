from NeoVintageous.nv.settings    import get_count, get_last_char_search_character, get_last_char_search_command, get_partial_sequence
from NeoVintageous.nv.utils       import InputParser
from NeoVintageous.nv.vi          import seqs
from NeoVintageous.nv.vi.cmd_base import RequireOneCharMixin, ViMotionDef, ViOperatorDef, translate_action, translate_motion
from NeoVintageous.nv.vi.keys     import assign, assign_text
from NeoVintageous.nv.vim         import ACTION_MODES, MOTION_MODES
from NeoVintageous.nv.modes       import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE


@assign(seqs.SEQ['d'], ACTION_MODES)
@assign_text(['DeleteByChars'], ACTION_MODES)
class ViDeleteByChars(ViOperatorDef):
    def init(self):
        self.updates_xpos           = True
        self.scroll_into_view       = True
        self.motion_required        = True
        self.repeatable             = True
        self.command                = 'nv_vi_delete_char'
@assign(seqs.SEQ['d'], (SELECT,))
@assign_text(['DeleteMultipleCursor'], (SELECT,))
class ViDeleteMultipleCursor(ViOperatorDef):
    def init(self):
        self.updates_xpos           = True
        self.scroll_into_view       = True
        self.repeatable             = True
        self.glue_until_normal_mode = True
        self.command                = 'nv_vi_delete_char'


@assign(seqs.SEQ['⇧o'], (NORMAL,))
@assign_text(['InsertLineBefore'], (NORMAL,))
class ViInsertLineBefore(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.glue_until_normal_mode = True
        self.command = 'nv_vi_big_o'


@assign(seqs.SEQ['⇧o'], (VISUAL, VISUAL_LINE, VISUAL_BLOCK))
@assign_text(['FlipSelectionInline','GoToOtherBigEnd'], (VISUAL, VISUAL_LINE, VISUAL_BLOCK))
class ViGoToOtherBigEnd(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_vi_flip_selection'
        self.command_args     = {'same_line_if_visual_block':True,}


@assign(seqs.SEQ['o'], (NORMAL,))
@assign_text(['InsertLineAfter'], (NORMAL,))
class ViInsertLineAfter(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = False
        self.glue_until_normal_mode = True
        self.command = 'nv_vi_o'


@assign(seqs.SEQ['o'], (VISUAL, VISUAL_LINE, VISUAL_BLOCK))
@assign_text(['FlipSelection','GoToOtherEnd'], (VISUAL, VISUAL_LINE, VISUAL_BLOCK), icon='⮀')
class ViGoToOtherEnd(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_vi_flip_selection'


@assign(seqs.SEQ['␡'], ACTION_MODES + (SELECT,))
@assign(seqs.SEQ['x'], ACTION_MODES + (SELECT,))
@assign_text(['RightDeleteChars'], ACTION_MODES + (SELECT,))
class ViRightDeleteChars(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True
        self.repeatable = True
        self.command = 'nv_vi_x'


@assign(seqs.SEQ['s'], ACTION_MODES + (SELECT,))
@assign_text(['SubstituteChar'], ACTION_MODES + (SELECT,))
class ViSubstituteChar(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.glue_until_normal_mode = True
        self.command = 'nv_vi_s'


@assign(seqs.SEQ['y'], ACTION_MODES)
@assign_text(['CopyChar','YankByChars'], ACTION_MODES, icon='🗐▋')
class ViYankByChars(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.motion_required = True
        self.command = 'nv_vi_copy_char'


@assign(seqs.SEQ['y'], (SELECT,))
@assign_text(['CopyCharSel','YankSelectByChars'], (SELECT,))
class ViYankSelectByChars(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_copy_char'


@assign(seqs.LESS_THAN, ACTION_MODES)
@assign_text(['Unindent'], ACTION_MODES, icon='⇚')
class ViUnindent(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.motion_required  = True
        self.repeatable       = True
        self.command          = 'nv_vi_unindent'
@assign(seqs.GREATER_THAN, ACTION_MODES)
@assign_text(['Indent'], ACTION_MODES, icon='⇛')
class ViIndent(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.motion_required  = True
        self.repeatable       = True
        self.command          = 'nv_vi_indent'
@assign(seqs.SEQ['='], ACTION_MODES)
@assign_text(['Reindent'], ACTION_MODES)
class ViReindent(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.motion_required  = True
        self.repeatable       = True
        self.command          = 'nv_vi_reindent'
@assign(seqs.LESS_THAN_LESS_THAN, ACTION_MODES)
@assign_text(['UnindentLine'], ACTION_MODES)
class ViUnindentLine(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.repeatable       = True
        self.command          = 'nv_vi_unindent_line'
@assign(seqs.GREATER_THAN_GREATER_THAN, ACTION_MODES)
@assign_text(['IndentLine'], ACTION_MODES)
class ViIndentLine(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.repeatable       = True
        self.command          = 'nv_vi_indent_line'
@assign(seqs.EQUAL_EQUAL, ACTION_MODES)
@assign_text(['ReindentLine'], ACTION_MODES)
class ViReindentLine(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.repeatable       = True
        self.command          = 'nv_vi_reindent_line'


@assign(seqs.SEQ['c'], ACTION_MODES)
@assign_text(['ChangeByChars'], ACTION_MODES)
class ViChangeByChars(ViOperatorDef):
    def init(self):
        self.updates_xpos           = True
        self.scroll_into_view       = True
        self.motion_required        = True
        self.repeatable             = True
        self.glue_until_normal_mode = True
        self.command                = 'nv_change_char'


@assign(seqs.SEQ['c'], (SELECT,))
@assign_text(['ChangeMultipleCursor'], (SELECT,))
class ViChangeMultipleCursor(ViOperatorDef):
    def init(self):
        self.updates_xpos           = True
        self.scroll_into_view       = True
        self.repeatable             = True
        self.glue_until_normal_mode = True
        self.command                = 'nv_change_char'


@assign(seqs.SEQ['u'], (NORMAL,))
@assign_text(['Undo'], (NORMAL,), icon='⎌')
class ViUndo(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_u'


@assign(seqs.SEQ['u'], (VISUAL, VISUAL_LINE, VISUAL_BLOCK))
@assign_text(['CaseLowerCharVis'], (VISUAL, VISUAL_LINE, VISUAL_BLOCK), icon="𝔸𝕒")
class ViChangeToLowerCaseByCharsVisual(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.repeatable       = True
        self.command          = 'nv_vi_case_lower_char_vis'


@assign(seqs.SEQ['⎈r'], ACTION_MODES)
@assign_text(['Redo'], ACTION_MODES, icon='↷')
class ViRedo(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True
        self.command = 'nv_vi_ctrl_r'


@assign(seqs.SEQ['⇧d'], ACTION_MODES)
@assign_text(['DeleteToEol'], ACTION_MODES)
class ViDeleteToEol(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True
        self.command = 'nv_vi_big_d'


@assign(seqs.SEQ['⇧c'], ACTION_MODES)
@assign_text(['ChangeToEol'], ACTION_MODES)
class ViChangeToEol(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True
        self.glue_until_normal_mode = True
        self.command = 'nv_vi_big_c'


@assign(seqs.G_BIG_U_BIG_U, ACTION_MODES)
@assign(seqs.G_BIG_U_G_BIG_U, ACTION_MODES)
@assign_text(['CaseUpperLine'], ACTION_MODES, icon="𝕒𝔸━")
class ViChangeToUpperCaseByLines(ViOperatorDef):
    def init(self):
        self.updates_xpos    	= True
        self.scroll_into_view	= True
        self.repeatable      	= True
        self.command         	= 'nv_vi_case_upper_line'


@assign(seqs.SEQ['cc'], ACTION_MODES)
@assign_text(['ChangeLine'], ACTION_MODES)
class ViChangeLine(ViOperatorDef):
    def init(self):
        self.updates_xpos           = True
        self.scroll_into_view       = True
        self.repeatable             = True
        self.glue_until_normal_mode = True
        self.command                = 'nv_vi_change_line'


@assign(seqs.SEQ['dd'], ACTION_MODES)
@assign_text(['DeleteLine'], ACTION_MODES, icon='ᵡ━')
class ViDeleteLine(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.repeatable       = True
        self.command          = 'nv_vi_delete_line'


@assign(seqs.SEQ['⇧r'], ACTION_MODES)
@assign_text(['EnterReplaceMode','Ⓡ'], ACTION_MODES, icon='Ⓡ')
class ViEnterReplaceMode(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True
        self.glue_until_normal_mode = True
        self.command = 'nv_enter_replace_mode'


@assign(seqs.GUGU, ACTION_MODES)
@assign(seqs.GUU, ACTION_MODES)
@assign_text(['CaseLowerLine'], ACTION_MODES, icon="𝔸𝕒━")
class ViChangeToLowerCaseByLines(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.repeatable       = True
        self.command          = 'nv_vi_case_lower_line'


@assign(seqs.SEQ['gu'], ACTION_MODES)
@assign_text(['CaseLowerChar'], ACTION_MODES, icon="𝔸𝕒")
class ViChangeToLowerCaseByChars(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.motion_required  = True
        self.repeatable       = True
        self.command          = 'nv_vi_case_lower_char'


@assign(seqs.SEQ['yy'], ACTION_MODES)
@assign(seqs.SEQ['⇧y'], ACTION_MODES)
@assign_text(['CopyLine','YankLine'], ACTION_MODES)
class ViYankLine(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_copy_line'


@assign(seqs.G_TILDE_TILDE, ACTION_MODES)
@assign_text(['CaseInvertLine','InvertCaseByLines'], ACTION_MODES, icon="𝕒⇋𝔸━")
class ViInvertCaseByLines(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.repeatable       = True
        self.command          = 'nv_vi_case_invert_line'


@assign(seqs.SEQ["~"], MOTION_MODES)
@assign_text(['CaseInvertCharVis','ForceInvertCaseByChars'], MOTION_MODES, icon="𝕒⇋𝔸")
class ViForceInvertCaseByChars(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.repeatable       = True
        self.command          = 'nv_vi_case_invert_char_vis'


@assign(seqs.SEQ['⇧s'], ACTION_MODES)
@assign_text(['SubstituteByLines'], ACTION_MODES)
class ViSubstituteByLines(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True
        self.glue_until_normal_mode = True
        self.command = 'nv_vi_big_s'


@assign(seqs.G_TILDE, ACTION_MODES)
@assign_text(['CaseInvertChar'], ACTION_MODES, icon="𝕒⇋𝔸")
class ViInvertCaseByChars(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.motion_required  = True
        self.repeatable       = True
        self.command          = 'nv_vi_case_invert_char'


@assign(seqs.SEQ['g⇧u'], ACTION_MODES)
@assign_text(['CaseUpperChar'], ACTION_MODES, icon="𝕒𝔸")
class ViChangeToUpperCaseByChars(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.motion_required  = True
        self.repeatable       = True
        self.command          = 'nv_vi_case_upper_char'


@assign(seqs.SEQ['⇧j'], ACTION_MODES)
@assign_text(['JoinLines'], ACTION_MODES)
class ViJoinLines(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True
        self.command = 'nv_vi_big_j'


@assign(seqs.SEQ['⎈x'], ACTION_MODES)
@assign_text(['Decrement'], ACTION_MODES, icon='⊖')
class ViDecrement(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True
        self.command = 'nv_vi_modify_numbers'
        self.command_args = {
            'subtract': True
        }


@assign(seqs.SEQ['⎈a'], ACTION_MODES)
@assign_text(['Increment'], ACTION_MODES, icon='⊕')
class ViIncrement(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True
        self.command = 'nv_vi_modify_numbers'


@assign(seqs.SEQ['g⇧j'], ACTION_MODES)
@assign_text(['JoinLinesNoSeparator'], ACTION_MODES)
class ViJoinLinesNoSeparator(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True
        self.command = 'nv_vi_big_j'
        self.command_args = {
            'dont_insert_or_remove_spaces': True
        }


@assign(seqs.SEQ['v'], ACTION_MODES)
@assign_text(['EnterVisualMode','ⓋⓋ'], ACTION_MODES, icon='ⓋⓋ')
class ViEnterVisualMode(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_enter_visual_mode'

@assign_text(['EnterVisualModeF'], ACTION_MODES, icon='ⓋⓋ')
class ViEnterVisualModeF(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
    def translate(self, view):
        return translate_action(view,'nv_enter_visual_mode',{'force':True})

@assign(seqs.Z_ENTER, ACTION_MODES)
@assign_text(['ScrollToScreenTopNonBlank'], ACTION_MODES)
class ViScrollToScreenTopNonBlank(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_z_enter'
        self.command_args = {
            'first_non_blank': True
        }
@assign(seqs.SEQ['zt'], ACTION_MODES)
@assign_text(['ScrollToScreenTop'], ACTION_MODES)
class ViScrollToScreenTop(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_z_enter'


@assign(seqs.Z_MINUS, ACTION_MODES)
@assign_text(['ScrollToScreenBottomNonBlank'], ACTION_MODES)
class ViScrollToScreenBottomNonBlank(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_z_minus'
        self.command_args = {
            'first_non_blank': True
        }


@assign(seqs.SEQ['zb'], ACTION_MODES)
@assign_text(['ScrollToScreenBottom'], ACTION_MODES)
class ViScrollToScreenBottom(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_z_minus'


@assign(seqs.Z_DOT, ACTION_MODES)
@assign_text(['ScrollToScreenCenterNonBlank'], ACTION_MODES)
class ViScrollToScreenCenterNonBlank(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_zz'
        self.command_args = {
            'first_non_blank': True
        }


@assign(seqs.SEQ['zz'], ACTION_MODES)
@assign_text(['ScrollToScreenCenter'], ACTION_MODES)
class ViScrollToScreenCenter(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_zz'



@assign(seqs.SEQ['gq'], ACTION_MODES)
@assign_text(['Reformat'], ACTION_MODES)
class ViReformat(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.motion_required = True
        self.scroll_into_view = True
        self.command = 'nv_vi_gq'


@assign(seqs.GQGQ, (NORMAL,))
@assign(seqs.GQQ, (NORMAL,))
@assign_text(['ReformatLinewise'], (NORMAL,))
class ViReformatLinewise(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_gq'
        self.command_args = {
            'linewise': True
        }


@assign(seqs.SEQ['⇧p']                        , ACTION_MODES + (SELECT,))
@assign_text(['PasteBefore']                  , ACTION_MODES + (SELECT,))
class ViPasteBefore                  (ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.repeatable       = True
        self.command          = 'nv_vi_paste'
        self.command_args     = {'before_cursor':True }
@assign(seqs.SEQ['p']                         , ACTION_MODES + (SELECT,))
@assign_text(['PasteAfter']                   , ACTION_MODES + (SELECT,))
class ViPasteAfter                   (ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.repeatable       = True
        self.command          = 'nv_vi_paste'
        self.command_args     = {'before_cursor':False}
@assign(seqs.SEQ['[⇧p']                       , ACTION_MODES + (SELECT,))
@assign(seqs.SEQ['[p']                        , ACTION_MODES + (SELECT,))
@assign_text(['PasteBeforeAndIndent']         , ACTION_MODES + (SELECT,))
class ViPasteBeforeAndIndent         (ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.repeatable       = True
        self.command          = 'nv_vi_paste'
        self.command_args     = {'before_cursor':True ,'adjust_indent':True}
@assign(seqs.SEQ[']⇧p']                       , ACTION_MODES + (SELECT,))
@assign(seqs.SEQ[']p']                        , ACTION_MODES + (SELECT,))
@assign_text(['PasteAfterAndIndent']          , ACTION_MODES + (SELECT,))
class ViPasteAfterAndIndent          (ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.repeatable       = True
        self.command          = 'nv_vi_paste'
        self.command_args     = {'before_cursor':False,'adjust_indent':True}
@assign(seqs.SEQ['g⇧p']                       , ACTION_MODES + (SELECT,))
@assign_text(['PasteBeforeWithAdjustedCursor'], ACTION_MODES + (SELECT,))
class ViPasteBeforeWithAdjustedCursor(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.repeatable       = True
        self.command          = 'nv_vi_paste'
        self.command_args     = {'before_cursor':True ,'adjust_cursor':True}
@assign(seqs.SEQ['gp']                        , ACTION_MODES + (SELECT,))
@assign_text(['PasteAfterWithAdjustedCursor'] , ACTION_MODES + (SELECT,))
class ViPasteAfterWithAdjustedCursor(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.repeatable       = True
        self.command          = 'nv_vi_paste'
        self.command_args     = {'before_cursor':False,'adjust_cursor':True}


@assign(seqs.SEQ['⇧x'], ACTION_MODES)
@assign_text(['LeftDeleteChar'], ACTION_MODES)
class ViLeftDeleteChar(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True
        self.command = 'nv_vi_big_x'


@assign(seqs.SEQ['⎈⇟'], ACTION_MODES)
@assign(seqs.SEQ['gt'], ACTION_MODES)
@assign(seqs.CTRL_W_GT, ACTION_MODES)
@assign_text(['ActivateNextTab'], ACTION_MODES, icon='⎘')
class ViActivateNextTab(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True

    def translate(self, view):
        return translate_action(view, 'nv_vi_gt', {
            'count': get_count(view, default=0)
        })


@assign(seqs.SEQ['⎈⇞'], ACTION_MODES)
@assign(seqs.SEQ['g⇧t'], ACTION_MODES)
@assign(seqs.CTRL_W_G_BIG_T, ACTION_MODES)
@assign_text(['ActivatePreviousTab'], ACTION_MODES, icon='⎗')
class ViActivatePreviousTab(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_g_big_t'


@assign(seqs.SEQ['⎈w'], (INSERT,))
@assign_text(['DeleteUpToCursor'], (INSERT,))
class ViDeleteUpToCursor(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_delete_word'


@assign(seqs.CTRL_W_B, ACTION_MODES)
@assign(seqs.CTRL_W_CTRL_B, ACTION_MODES)
@assign_text(['MoveCursorToBottomRightWindow'], ACTION_MODES)
class ViMoveCursorToBottomRightWindow(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': 'b'
        }


@assign(seqs.CTRL_W_BIG_H, ACTION_MODES)
@assign_text(['MoveCurrentWindowToFarLeft'], ACTION_MODES)
class ViMoveCurrentWindowToFarLeft(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': 'H'
        }


@assign(seqs.CTRL_W_BIG_J, ACTION_MODES)
@assign_text(['MoveCurrentWindowToVeryTop'], ACTION_MODES)
class ViMoveCurrentWindowToVeryTop(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': 'J'
        }


@assign(seqs.CTRL_W_BIG_K, ACTION_MODES)
@assign_text(['MoveCurrentWindowToVeryBottom'], ACTION_MODES)
class ViMoveCurrentWindowToVeryBottom(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': 'K'
        }


@assign(seqs.SEQ['⎈6'], ACTION_MODES)
@assign(seqs.CTRL_HAT, ACTION_MODES)
@assign_text(['GotoAlternateFile'], ACTION_MODES)
class ViGotoAlternateFile(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command          = 'nv_vi_goto_file_alt'


@assign(seqs.CTRL_W_BIG_L, ACTION_MODES)
@assign_text(['MoveCurrentWindowToFarRight'], ACTION_MODES)
class ViMoveCurrentWindowToFarRight(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': 'L'
        }


@assign(seqs.CTRL_W_C, ACTION_MODES)
@assign_text(['CloseTheCurrentWindow'], ACTION_MODES)
class ViCloseTheCurrentWindow(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': 'c'
        }


@assign(seqs.CTRL_W_EQUAL, ACTION_MODES)
@assign_text(['MakeAllWindowsAlmostEquallyHighAndWide'], ACTION_MODES)
class ViMakeAllWindowsAlmostEquallyHighAndWide(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': '='
        }


@assign(seqs.CTRL_W_GREATER_THAN, ACTION_MODES)
@assign_text(['IncreaseCurrentWindowWidthByN'], ACTION_MODES)
class ViIncreaseCurrentWindowWidthByN(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': '>',
        }


@assign(seqs.CTRL_W_H, ACTION_MODES)
@assign(seqs.CTRL_W_CTRL_H, ACTION_MODES)
@assign(seqs.CTRL_W_LEFT, ACTION_MODES)
@assign(seqs.CTRL_W_BACKSPACE, ACTION_MODES)
@assign_text(['MoveCursorToNthWindowLeftOfCurrentOne'], ACTION_MODES)
class ViMoveCursorToNthWindowLeftOfCurrentOne(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': 'h',
        }


@assign(seqs.CTRL_W_J, ACTION_MODES)
@assign(seqs.CTRL_W_CTRL_J, ACTION_MODES)
@assign(seqs.CTRL_W_DOWN, ACTION_MODES)
@assign_text(['MoveCursorToNthWindowBelowOfCurrentOne'], ACTION_MODES)
class ViMoveCursorToNthWindowBelowOfCurrentOne(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': 'j',
        }


@assign(seqs.CTRL_W_K, ACTION_MODES)
@assign(seqs.CTRL_W_CTRL_K, ACTION_MODES)
@assign(seqs.CTRL_W_UP, ACTION_MODES)
@assign_text(['MoveCursorToNthWindowAboveCurrentOne'], ACTION_MODES)
class ViMoveCursorToNthWindowAboveCurrentOne(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': 'k',
        }


@assign(seqs.CTRL_W_L, ACTION_MODES)
@assign(seqs.CTRL_W_CTRL_L, ACTION_MODES)
@assign(seqs.CTRL_W_RIGHT, ACTION_MODES)
@assign_text(['MoveCursorToNthWindowRightOfCurrentOne'], ACTION_MODES)
class ViMoveCursorToNthWindowRightOfCurrentOne(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': 'l',
        }


@assign(seqs.CTRL_W_LESS_THAN, ACTION_MODES)
@assign_text(['DecreaseCurrentWindowWidthByN'], ACTION_MODES)
class ViDecreaseCurrentWindowWidthByN(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': '<',
        }


@assign(seqs.CTRL_W_MINUS, ACTION_MODES)
@assign_text(['DecreaseCurrentWindowHeightByN'], ACTION_MODES)
class ViDecreaseCurrentWindowHeightByN(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': '-',
        }


@assign(seqs.CTRL_W_N, ACTION_MODES)
@assign(seqs.CTRL_W_CTRL_N, ACTION_MODES)
@assign_text(['CreateNewWindowAndStartEditingAnEmptyFileInIt'], ACTION_MODES)
class ViCreateNewWindowAndStartEditingAnEmptyFileInIt(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': 'n',
        }


@assign(seqs.CTRL_W_O, ACTION_MODES)
@assign(seqs.CTRL_W_CTRL_O, ACTION_MODES)
@assign_text(['MakeTheCurrentWindowTheOnlyOneOnTheScreen'], ACTION_MODES)
class ViMakeTheCurrentWindowTheOnlyOneOnTheScreen(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': 'o'
        }


@assign(seqs.CTRL_W_BAR, ACTION_MODES)
@assign_text(['SetCurrentWindowWidthToNOrWidestPossible'], ACTION_MODES)
class ViSetCurrentWindowWidthToNOrWidestPossible(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': '|',
        }


@assign(seqs.CTRL_W_PLUS, ACTION_MODES)
@assign_text(['IncreaseCurrentWindowHeightByN'], ACTION_MODES)
class ViIncreaseCurrentWindowHeightByN(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': '+',
        }


@assign(seqs.CTRL_W_Q, ACTION_MODES)
@assign(seqs.CTRL_W_CTRL_Q, ACTION_MODES)
@assign_text(['QuitTheCurrentWindow'], ACTION_MODES)
class ViQuitTheCurrentWindow(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': 'q'
        }


@assign(seqs.CTRL_W_S, ACTION_MODES)
@assign(seqs.CTRL_W_BIG_S, ACTION_MODES)
@assign(seqs.CTRL_W_CTRL_S, ACTION_MODES)
@assign_text(['SplitTheCurrentWindowInTwo'], ACTION_MODES)
class ViSplitTheCurrentWindowInTwo(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': 's',
        }


@assign(seqs.CTRL_W_T, ACTION_MODES)
@assign(seqs.CTRL_W_CTRL_T, ACTION_MODES)
@assign_text(['MoveCursorToTopLeftWindow'], ACTION_MODES)
class ViMoveCursorToTopLeftWindow(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': 't'
        }


@assign(seqs.CTRL_W_W, ACTION_MODES)
@assign(seqs.CTRL_W_CTRL_W, ACTION_MODES)
@assign_text(['MoveCursorToNeighbour'], ACTION_MODES)
class ViMoveCursorToNeighbour(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True

    def translate(self, view):
        return translate_action(view, 'nv_vi_window_control', {
            'action': 'w',
            'count': get_count(view, default=0)
        })


@assign(seqs.CTRL_W_UNDERSCORE, ACTION_MODES)
@assign(seqs.CTRL_W_CTRL_UNDERSCORE, ACTION_MODES)
@assign_text(['SetCurrentGroupHeightOrHighestPossible'], ACTION_MODES)
class ViSetCurrentGroupHeightOrHighestPossible(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': '_',
        }


@assign(seqs.CTRL_W_V, ACTION_MODES)
@assign(seqs.CTRL_W_CTRL_V, ACTION_MODES)
@assign_text(['SplitTheCurrentWindowInTwoVertically'], ACTION_MODES)
class ViSplitTheCurrentWindowInTwoVertically(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': 'v',
        }


@assign(seqs.CTRL_W_BIG_W, ACTION_MODES)
@assign_text(['MoveCursorToPrevNeighbour'], ACTION_MODES)
class ViMoveCursorToPrevNeighbour(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True

    def translate(self, view):
        return translate_action(view, 'nv_vi_window_control', {
            'action': 'W',
            'count': get_count(view, default=0)
        })


@assign(seqs.CTRL_W_X, ACTION_MODES)
@assign(seqs.CTRL_W_CTRL_X, ACTION_MODES)
@assign_text(['ExchangeCurrentWindowWithNextOrPreviousNthWindow'], ACTION_MODES)
class ViExchangeCurrentWindowWithNextOrPreviousNthWindow(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': 'x',
        }


@assign(seqs.SEQ['⇧v'], ACTION_MODES)
@assign_text(['EnterVisualLineMode','━'], ACTION_MODES, icon='━')
class ViEnterVisualLineMode(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_enter_visual_line_mode'


@assign(seqs.SEQ['gv'], ACTION_MODES)
@assign_text(['RestoreVisualSelections'], ACTION_MODES)
class ViRestoreVisualSelections(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_gv'


@assign(seqs.SEQ['gx'], ACTION_MODES)
@assign_text(['OpenURL'], ACTION_MODES)
class ViNetrwGx(ViOperatorDef):
    def init(self):
        self.command = 'nv_vi_open_url'


@assign(seqs.SEQ['⎈o'], ACTION_MODES)
@assign_text(['JumpBack'], ACTION_MODES, icon='⎗̡')
class ViJumpBack(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_jump_back'


@assign(seqs.SEQ['⎈i'], ACTION_MODES)
@assign(seqs.SEQ['⭾'], ACTION_MODES)
@assign_text(['JumpForward'], ACTION_MODES, icon='⎘̡')
class ViJumpForward(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_jump_forward'


@assign(seqs.SEQ['.'], ACTION_MODES)
@assign_text(['Repeat'], ACTION_MODES, icon='∞')
class ViRepeat(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_dot'


@assign(seqs.SEQ['⎈y'], ACTION_MODES)
@assign_text(['ScrollByLinesUp'], ACTION_MODES)
class ViScrollByLinesUp(ViMotionDef):
    def init(self):
        self.command = 'nv_vi_scroll_up'


@assign(seqs.SEQ['⇧u'], (VISUAL, VISUAL_LINE, VISUAL_BLOCK))
@assign_text(['CaseUpperCharVis'], (VISUAL, VISUAL_LINE, VISUAL_BLOCK), icon="𝕒𝔸")
class ViChangeToUpperCaseByCharsVisual(ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.repeatable       = True
        self.command          = 'nv_vi_case_upper_char_vis'


@assign(seqs.SEQ['⎈e'], ACTION_MODES)
@assign_text(['ScrollByLinesDown'], ACTION_MODES)
class ViScrollByLinesDown(ViMotionDef):
    def init(self):
        self.command = 'nv_vi_ctrl_e'


@assign(seqs.SEQ['⇧2'], ACTION_MODES)
@assign_text(['OpenMacrosForRepeating'], ACTION_MODES)
class ViOpenMacrosForRepeating(RequireOneCharMixin, ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, view):
        return translate_action(view,'nv_vi_repeat_macro',{'name':self.inp})


@assign(seqs.SEQ['q'], ACTION_MODES)
@assign_text(['ToggleMacroRecorder'], ACTION_MODES, icon='⏺')
class ViToggleMacroRecorder(RequireOneCharMixin, ViOperatorDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
    def translate(self, view):
        return translate_action(view, 'nv_vi_toggle_macro_record',{'name':self.inp})


@assign(seqs.SEQ['⎈v'], ACTION_MODES)
@assign_text(['EnterVisualBlockMode','▋'], ACTION_MODES, icon='▋')
class ViEnterVisualBlockMode(ViOperatorDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_enter_visual_block_mode'


@assign(seqs.SEQ['ga'], ACTION_MODES)
@assign_text(['ShowAsciiValueOfChar'], ACTION_MODES)
class ViShowAsciiValueOfChar(ViOperatorDef):
    def init(self):
        self.command = 'nv_vi_ga'


@assign(seqs.CTRL_W_GF, ACTION_MODES)
@assign(seqs.SEQ['gf'], ACTION_MODES)
@assign_text(['GoToFile','Vigf'], ACTION_MODES)
class Vigf(ViOperatorDef):
    def init(self):
        self.command      = 'nv_vi_go_to_file'
        self.command_args = {'action':'f'}


@assign(seqs.SEQ['gf'], (NORMAL,))
@assign(seqs.SEQ['g⇧f'], (NORMAL,))
@assign(seqs.CTRL_W_G_BIG_F, ACTION_MODES)
@assign_text(['GoToFileLine','VigF'], ACTION_MODES)
class VigF(ViOperatorDef):
    def init(self):
        self.command      = 'nv_vi_go_to_file'
        self.command_args = {'action':'F'}


@assign(seqs.SEQ['i'], (NORMAL, SELECT))
@assign(seqs.SEQ['⎀'], (NORMAL, SELECT))
@assign_text(['EnterInsertMode','ⓘ'], (NORMAL, SELECT), icon='ⓘ')
class ViEnterInsertMode(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.glue_until_normal_mode = True
        self.command = 'nv_enter_insert_mode'


@assign(seqs.SEQ['v'], (SELECT, ))
@assign(seqs.SEQ['⎋'], ACTION_MODES)
@assign(seqs.SEQ['⎈c'], ACTION_MODES + (INSERT, SELECT))
@assign(seqs.SEQ['⎈['], ACTION_MODES + (INSERT, SELECT))
@assign_text(['EnterNormalMode','Ⓝ'], ACTION_MODES + (INSERT, SELECT), icon='Ⓝ')
class ViEnterNormalMode(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_enter_normal_mode'


@assign(seqs.CTRL_RIGHT_SQUARE_BRACKET, ACTION_MODES)
@assign_text(['JumpToDefinition'], ACTION_MODES)
class ViJumpToDefinition(ViOperatorDef):
    def init(self):
        self.command = 'nv_vi_ctrl_right_square_bracket'


@assign(seqs.CTRL_W_CTRL_RIGHT_SQUARE_BRACKET, ACTION_MODES)
@assign(seqs.CTRL_W_RIGHT_SQUARE_BRACKET, ACTION_MODES)
@assign_text(['SplitAndJumpToDefinition'], ACTION_MODES)
class ViSplitAndJumpToDefinition(ViOperatorDef):
    def init(self):
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': ']'
        }


@assign(seqs.CTRL_W_HAT, ACTION_MODES)
@assign(seqs.CTRL_W_CTRL_6, ACTION_MODES)
@assign_text(['SplitAndEditAlternate'], ACTION_MODES)
class ViSplitAndEditAlternate(ViOperatorDef):
    def init(self):
        self.command = 'nv_vi_window_control'
        self.command_args = {
            'action': '^'
        }


@assign(seqs.SEQ['a'], (NORMAL,))
@assign_text(['InsertAfterChar'], (NORMAL,))
class ViInsertAfterChar(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.glue_until_normal_mode = True
        self.command = 'nv_vi_a'


@assign(seqs.SEQ['⇧a'], ACTION_MODES)
@assign_text(['InsertAtEol'], ACTION_MODES)
class ViInsertAtEol(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.glue_until_normal_mode = True
        self.command = 'nv_vi_big_a'


@assign(seqs.SEQ['⇧i'], ACTION_MODES + (SELECT,))
@assign_text(['InsertAtBol'], ACTION_MODES + (SELECT,))
class ViInsertAtBol(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.glue_until_normal_mode = True
        self.command = 'nv_vi_big_i'


@assign(seqs.SEQ[':'], ACTION_MODES)
@assign(seqs.CTRL_W_COLON, ACTION_MODES)
@assign_text(['EnterCommandLineMode','Ⓒ'], ACTION_MODES, icon='Ⓒ')
class ViEnterCommandLineMode(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_cmdline'


@assign(seqs.SEQ['⎈g'], ACTION_MODES)
@assign_text(['ShowFileStatus'], ACTION_MODES)
class ViShowFileStatus(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command          = 'nv_vi_file_status'


@assign(seqs.SEQ['⇧z⇧z'], (NORMAL,))
@assign_text(['CloseFile'], (NORMAL,))
class ViCloseFile(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command          = 'nv_vi_close_file'
@assign(seqs.SEQ['⇧z⇧q'], (NORMAL,))
@assign_text(['CloseFileNoSave'], (NORMAL,))
class ViExitEditor(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command          = 'nv_vi_close_file_no_save'


@assign(seqs.SEQ['g⇧d'], ACTION_MODES)
@assign_text(['GotoSymbolInProject'], ACTION_MODES)
class ViGotoSymbolInProject(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_go_to_symbol'
        self.command_args = {
            'globally': True
        }


@assign(seqs.SEQ['gd'], MOTION_MODES)
@assign_text(['GotoSymbolInFile'], MOTION_MODES)
class ViGotoSymbolInFile(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True
        self.command = 'nv_vi_go_to_symbol'
        self.command_args = {
            'globally': False
        }


@assign(seqs.SEQ['⎇▶'], MOTION_MODES)
@assign(seqs.SEQ['l'], MOTION_MODES)
@assign(seqs.SEQ['▶'], MOTION_MODES)
@assign(seqs.SEQ['␠'], MOTION_MODES)
@assign_text(['MoveRightByChars'], MOTION_MODES)
class ViMoveRightByChars(ViMotionDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_move_char_right'


@assign(seqs.SEQ['⇧⏎'], MOTION_MODES)
@assign_text(['ShiftEnterMotion'], MOTION_MODES)
class ViShiftEnterMotion(ViMotionDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_shift_enter'


@assign(seqs.SEQ['b'], MOTION_MODES)
@assign(seqs.SEQ['⇧◀'], MOTION_MODES)
@assign_text(['MoveByWordsBackward'], MOTION_MODES, icon="⤝ω")
class ViMoveByWordsBackward(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.command          = 'nv_vi_move_word_prev'
@assign(seqs.SEQ['⇧▶'], MOTION_MODES)
@assign(seqs.SEQ['w'], MOTION_MODES)
@assign_text(['MoveByWords'], MOTION_MODES, icon="ω⤞")
class ViMoveByWords(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.command          = 'nv_vi_move_word_next'

@assign(seqs.SEQ['⇧b'], MOTION_MODES)
@assign(seqs.SEQ['⎈◀'], MOTION_MODES)
@assign_text(['MoveByBigWordsBackward'], MOTION_MODES, icon="⤝W")
class ViMoveByBigWordsBackward(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.command          = 'nv_vi_move_bigword_prev'
@assign(seqs.SEQ['⇧w'], MOTION_MODES)
@assign(seqs.SEQ['⎈▶'], MOTION_MODES)
@assign_text(['MoveByBigWords'], MOTION_MODES, icon="W⤞")
class ViMoveByBigWords(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.command          = 'nv_vi_move_bigword_next'

@assign(seqs.SEQ['ge'], MOTION_MODES)
@assign_text(['MoveByWordEndsBackward'], MOTION_MODES, icon="⭰ω")
class ViMoveByWordEndsBackward(ViMotionDef):
    def init(self):
        self.updates_xpos    	= True
        self.scroll_into_view	= True
    def translate(self, view):
        return translate_motion(view, 'nv_vi_move_wordend_prev',{'nosep':False})
@assign(seqs.SEQ['e'], MOTION_MODES)
@assign_text(['MoveByWordEnds'], MOTION_MODES, icon="ω⭲")
class ViMoveByWordEnds(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
    def translate(self, view):
        return translate_motion(view, 'nv_vi_move_wordend_next',{'nosep':False})
@assign_text(['MoveByWordEndsBackwardNoSep'], MOTION_MODES, icon="⭰ω")
class ViMoveByWordEndsBackwardNoSep(ViMotionDef):
    def init(self):
        self.updates_xpos       = True
        self.scroll_into_view   = True
    def translate(self, view):
        return translate_motion(view, 'nv_vi_move_wordend_prev',{'nosep':True })
@assign_text(['MoveByWordEndsNoSep'], MOTION_MODES, icon="ω⭲")
class ViMoveByWordEndsNoSep(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
    def translate(self, view):
        return translate_motion(view, 'nv_vi_move_wordend_next',{'nosep':True })

@assign(seqs.SEQ['g⇧e'], MOTION_MODES)
@assign_text(['MoveByBigWordEndsBackward'], MOTION_MODES, icon="⭰W")
class ViMoveByBigWordEndsBackward(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.command          = 'nv_vi_move_bigwordend_prev'
@assign(seqs.SEQ['⇧e'], MOTION_MODES)
@assign_text(['MoveByBigWordEnds'], MOTION_MODES)
class ViMoveByBigWordEnds(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.command          = 'nv_vi_move_bigwordend_next'


@assign(seqs.SEQ['⇧h'], MOTION_MODES)
@assign_text(['GotoScreenTop'], MOTION_MODES)
class ViGotoScreenTop(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
    def translate(self, view):
        return translate_motion(view, 'nv_vi_goto_screen_top',{'count':get_count(view,default=0)})
@assign(seqs.SEQ['⇧l'], MOTION_MODES)
@assign_text(['GotoScreenBottom'], MOTION_MODES)
class ViGotoScreenBottom(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
    def translate(self, view):
        return translate_motion(view, 'nv_vi_goto_screen_bottom',{'count':get_count(view,default=0)})


@assign(seqs.G_SEMICOLON, MOTION_MODES)
@assign_text(['GotoOlderChange'], MOTION_MODES)
class ViGotoOlderChange(ViMotionDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_goto_changelist'
        self.command_args = {
            'forward': False
        }


@assign(seqs.G_COMMA, MOTION_MODES)
@assign_text(['GotoNewerChange'], MOTION_MODES)
class ViGotoNewerChange(ViMotionDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_goto_changelist'


@assign(seqs.SEQ['⇧m'], MOTION_MODES)
@assign_text(['GotoScreenMiddle'], MOTION_MODES)
class ViGotoScreenMiddle(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.command          = 'nv_vi_move_screen_middle'


@assign(seqs.SEQ['⎈d'], MOTION_MODES)
@assign_text(['MoveHalfScreenDown'], MOTION_MODES, icon='⤈')
class ViMoveHalfScreenDown(ViMotionDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = False

    def translate(self, view):
        return translate_motion(view, 'nv_vi_ctrl_d', {
            'count': get_count(view, default=0)
        })


@assign(seqs.SEQ['⎈u'], MOTION_MODES + (INSERT,))
@assign_text(['MoveHalfScreenUp'], MOTION_MODES + (INSERT,), icon='⤉')
class ViMoveHalfScreenUp(ViMotionDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, view):
        return translate_motion(view, 'nv_vi_ctrl_u', {
            'count': get_count(view, default=0)
        })


@assign(seqs.SEQ['⎈f'], MOTION_MODES)
@assign(seqs.SEQ['⇟'], MOTION_MODES)
@assign(seqs.SEQ['⇧▼'], MOTION_MODES)
@assign_text(['MoveScreenDown'], MOTION_MODES, icon='⇟')
class ViMoveScreenDown(ViMotionDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_ctrl_f'


@assign(seqs.SEQ['⎈b'], MOTION_MODES)
@assign(seqs.SEQ['⇞'], MOTION_MODES)
@assign(seqs.SEQ['⇧▲'], MOTION_MODES)
@assign_text(['MoveScreenUp'], MOTION_MODES, icon='⇞')
class ViMoveScreenUp(ViMotionDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_ctrl_b'


@assign(seqs.SEQ['`'], MOTION_MODES)
@assign_text(['GotoExactMarkXpos'], MOTION_MODES, icon='☰🖈')
class ViGotoExactMarkXpos(RequireOneCharMixin, ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
    def translate(self, view):
        return translate_motion(view,'nv_vi_jump_to_mark'           ,{'character':self.inp})
@assign(seqs.SEQ["'"], MOTION_MODES)
@assign_text(['GotoMark'], MOTION_MODES, icon='☰🖈𝕒')
class ViGotoMark(RequireOneCharMixin, ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
    def translate(self, view):
        return translate_motion(view, 'nv_vi_jump_to_mark_non_blank',{'character':self.inp})


@assign(seqs.SEQ['$'], MOTION_MODES)
@assign(seqs.SEQ['⇥'], MOTION_MODES)
@assign_text(['MoveToEol'], MOTION_MODES)
class ViMoveToEol(ViMotionDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_dollar'


@assign(seqs.SEQ['⎈m'], MOTION_MODES)
@assign(seqs.SEQ['⏎'], MOTION_MODES)
@assign(seqs.SEQ['+'], MOTION_MODES)
@assign_text(['MotionEnter'], MOTION_MODES, icon='⭣␤')
class ViMotionEnter(ViMotionDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_enter'


@assign(seqs.SEQ['='], MOTION_MODES)
@assign_text(['MoveBackOneLine'], MOTION_MODES)
class ViMoveBackOneLine(ViMotionDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_move_line_back'


@assign(seqs.SEQ['g⇧-'], MOTION_MODES)
@assign_text(['MoveToSoftEol'], MOTION_MODES)
class ViMoveToSoftEol(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.command          = 'nv_vi_move_to_soft_eol'


@assign(seqs.G_DOWN, MOTION_MODES)
@assign(seqs.SEQ['gj'], MOTION_MODES)
@assign_text(['MoveByScreenLineDown'], MOTION_MODES, icon='↪▼')
class ViMoveByScreenLineDown(ViMotionDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_move_screen_line_down'


@assign(seqs.G_UP, MOTION_MODES)
@assign(seqs.SEQ['gk'], MOTION_MODES)
@assign_text(['MoveByScreenLineUp'], MOTION_MODES, icon='↪▲')
class ViMoveByScreenLineUp(ViMotionDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_move_screen_line_up'


@assign(seqs.SEQ['⇧['], MOTION_MODES)
@assign_text(['MoveByBlockUp'], MOTION_MODES, icon='🢔¶')
class ViMoveByBlockUp(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.command          = 'nv_vi_move_paragraph_prev'


@assign(seqs.SEQ[";"], MOTION_MODES)
@assign_text(['RepeatCharSearchForward'], MOTION_MODES)
class ViRepeatCharSearchForward(ViMotionDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True

    # TODO Refactor settings dependencies into the command being called
    def translate(self, view):
        last_search_cmd = get_last_char_search_command(view)
        if 'sneak' in last_search_cmd:
            return translate_motion(view, 'nv_sneak', {
                'forward': last_search_cmd == 'sneak_s',
                'save': False
            })

        forward = last_search_cmd in ('vi_t', 'vi_f')
        inclusive = last_search_cmd in ('vi_f', 'vi_big_f')
        skipping = last_search_cmd in ('vi_t', 'vi_big_t')
        motion = 'nv_vi_find_in_line' if forward else 'nv_vi_reverse_find_in_line'

        return translate_motion(view, motion, {
            'char': get_last_char_search_character(view),
            'inclusive': inclusive,
            'skipping': skipping,
            'save': False
        })


@assign(seqs.SEQ["}"], MOTION_MODES)
@assign_text(['MoveByBlockDown'], MOTION_MODES, icon='¶🢖')
class ViMoveByBlockDown(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.command          = 'nv_vi_move_paragraph_next'


@assign(seqs.SEQ['⇧9'], MOTION_MODES)
@assign_text(['MoveBySentenceUp'], MOTION_MODES)
class ViMoveBySentenceUp(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
    def translate(self, view):
        return translate_motion(view,'nv_vi_move_sentence_prev',{'stop_nl':True})
@assign(seqs.SEQ['⇧0'], MOTION_MODES)
@assign_text(['MoveBySentenceDown'], MOTION_MODES)
class ViMoveBySentenceDown(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
    def translate(self, view):
        return translate_motion(view,'nv_vi_move_sentence_next',{'stop_nl':True})
@assign_text(['MoveBySentenceUpNoNl'], MOTION_MODES)
class ViMoveBySentenceUpNoNl(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
    def translate(self, view):
        return translate_motion(view,'nv_vi_move_sentence_prev',{'stop_nl':False})
@assign_text(['MoveBySentenceDownNoNl'], MOTION_MODES)
class ViMoveBySentenceDownNoNl(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
    def translate(self, view):
        return translate_motion(view,'nv_vi_move_sentence_next',{'stop_nl':False})


@assign(seqs.SEQ['[c'], ACTION_MODES)
@assign_text(['MoveChangePrev','BackwardToStartOfChange'], ACTION_MODES)
class ViBackwardToStartOfChange(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_move_change_prev'
@assign(seqs.SEQ[']c'], ACTION_MODES)
@assign_text(['MoveChangeNext','ForwardToStartOfChange'], ACTION_MODES)
class ViForwardToStartOfChange(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_move_change_next'


@assign(seqs.SEQ['[s'], ACTION_MODES)
@assign_text(['MoveMisspellingPrev','PrevMisppelledWord'], ACTION_MODES)
class ViPrevMisppelledWord(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_move_misspelling_prev'
@assign(seqs.SEQ[']s'], ACTION_MODES)
@assign_text(['MoveMisspellingNext','NextMispelledWord'], ACTION_MODES)
class ViNextMispelledWord(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_move_misspelling_next'


@assign_text(['GotoTargetPrev'], MOTION_MODES, icon="🢔🎯")
class ViGotoTargetPrev(RequireOneCharMixin, ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
    def translate(self, view):
        return translate_motion(view,'nv_target_prev',{'target':self.inp})
@assign_text(['GotoTargetNext'], MOTION_MODES, icon="🎯🢖")
class ViGotoTargetNext(RequireOneCharMixin, ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
    def translate(self, view):
        return translate_motion(view,'nv_target_next',{'target':self.inp})

@assign(seqs.SEQ['[⇧['], MOTION_MODES)
@assign_text(['GotoOpeningBrace'], MOTION_MODES)
class ViGotoOpeningBrace(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True
        self.command = 'nv_target_prev'
        self.command_args = {'target':'{'}
@assign(seqs.SEQ[']⇧]'], MOTION_MODES)
@assign_text(['GotoClosingBrace'], MOTION_MODES)
class ViGotoClosingBrace(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True
        self.command = 'nv_target_next'
        self.command_args = {'target':'}'}
@assign(seqs.SEQ['[⇧9'], MOTION_MODES)
@assign_text(['GotoOpeningParen'], MOTION_MODES)
class ViGotoOpeningParen(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True
        self.command = 'nv_target_prev'
        self.command_args = {'target':'('}
@assign(seqs.SEQ[']⇧0'], MOTION_MODES)
@assign_text(['GotoClosingParen'], MOTION_MODES)
class ViGotoClosingParen(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True
        self.command = 'nv_target_next'
        self.command_args = {'target':')'}


@assign(seqs.SEQ['%'], MOTION_MODES)
@assign_text(['Percent'], MOTION_MODES)
class ViPercent(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
    def translate(self, view):
        return translate_motion(view,'nv_vi_percent'
            ,{'count':get_count(view,default=0)})
@assign_text(['MoveToBracketMatch'], MOTION_MODES)
class ViMatchBracket(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.command          = 'nv_vi_move_to_bracket_match'
@assign_text(['MoveToFilePercent'], MOTION_MODES)
class ViMoveToFilePercent(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
    def translate(self, view):
        return translate_motion(view,'nv_vi_move_to_file_percent'
            ,{'count':get_count(view,default=0)})


@assign(seqs.SEQ['⧵'], MOTION_MODES)
@assign(seqs.SEQ[','], MOTION_MODES)
@assign_text(['RepeatCharSearchBackward'], MOTION_MODES)
class ViRepeatCharSearchBackward(ViMotionDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True

    # TODO Refactor settings dependencies into the command being called
    def translate(self, view):
        last_search_cmd = get_last_char_search_command(view)
        if 'sneak' in last_search_cmd:
            return translate_motion(view, 'nv_sneak', {
                'forward': last_search_cmd == 'sneak_big_s',
                'save': False
            })

        forward = last_search_cmd in ('vi_t', 'vi_f')
        inclusive = last_search_cmd in ('vi_f', 'vi_big_f')
        skipping = last_search_cmd in ('vi_t', 'vi_big_t')
        motion = 'nv_vi_find_in_line' if not forward else 'nv_vi_reverse_find_in_line'

        return translate_motion(view, motion, {
            'char': get_last_char_search_character(view),
            'inclusive': inclusive,
            'skipping': skipping,
            'save': False
        })


@assign(seqs.BAR, MOTION_MODES)
@assign_text(['MoveByLineCols'], MOTION_MODES)
class ViMoveByLineCols(ViMotionDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_move_column'


@assign(seqs.SEQ['⎇◀'], MOTION_MODES)
@assign(seqs.SEQ['␈'], MOTION_MODES)
@assign(seqs.SEQ['⎈␈'], MOTION_MODES)
@assign(seqs.SEQ['⎈h'], MOTION_MODES)
@assign(seqs.SEQ['h'], MOTION_MODES)
@assign(seqs.SEQ['◀'], MOTION_MODES)
@assign_text(['MoveLeftByChars'], MOTION_MODES, icon="◀")
class ViMoveLeftByChars(ViMotionDef):
    def init(self):
        self.updates_xpos = True
        self.scroll_into_view = True
        self.command = 'nv_vi_move_char_left'


@assign(seqs.SEQ['⎈▼'], MOTION_MODES)
@assign(seqs.SEQ['⎈j'], MOTION_MODES)
@assign(seqs.SEQ['⎈n'], MOTION_MODES + (INSERT,))
@assign(seqs.SEQ['▼'], MOTION_MODES)
@assign(seqs.SEQ['j'], MOTION_MODES)
@assign_text(['MoveDownByLines'], MOTION_MODES + (INSERT,), icon="▼")
class ViMoveDownByLines(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_move_line_down'


@assign(seqs.SEQ['⎈p'], MOTION_MODES)
@assign(seqs.SEQ['⎈▲'], MOTION_MODES)
@assign(seqs.SEQ['k'], MOTION_MODES)
@assign(seqs.SEQ['▲'], MOTION_MODES)
@assign_text(['MoveUpByLines'], MOTION_MODES, icon="▲")
class ViMoveUpByLines(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.command = 'nv_vi_move_line_up'


@assign(seqs.SEQ["^"], MOTION_MODES)
@assign(seqs.SEQ['⇤'], MOTION_MODES)
@assign_text(['MoveToBol'], MOTION_MODES, icon="⇤")
class ViMoveToBol(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True
        self.command = 'nv_vi_move_to_bol'


@assign(seqs.SEQ["_"], MOTION_MODES)
@assign_text(['MoveToSoftBol'], MOTION_MODES)
class ViMoveToSoftBol(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True
        self.command = 'nv_vi_move_to_soft_bol'


@assign(seqs.SEQ['🔢0'], MOTION_MODES)
@assign(seqs.ZERO, MOTION_MODES)
@assign_text(['MoveToHardBol'], MOTION_MODES)
class ViMoveToHardBol(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True
        self.command = 'nv_vi_move_to_hard_bol'


@assign(seqs.SEQ['gn'], MOTION_MODES)
@assign_text(['SearchLastUsedPattern'], MOTION_MODES)
class ViSearchLastUsedPattern(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True
        self.command = 'nv_vi_search'


@assign(seqs.SEQ['g⇧n'], MOTION_MODES)
@assign_text(['SearchLastUsedPatternReverse'], MOTION_MODES)
class ViSearchLastUsedPatternReverse(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True
        self.command = 'nv_vi_search'
        self.command_args = {
            'forward': False
        }


@assign(seqs.SEQ['n'], MOTION_MODES)
@assign_text(['RepeatSearchForward'], MOTION_MODES)
class ViRepeatSearchForward(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True
        self.command = 'nv_vi_repeat_buffer_search'
        self.command_args = {
            'reverse': False
        }


@assign(seqs.SEQ['⇧n'], MOTION_MODES)
@assign_text(['RepeatSearchBackward'], MOTION_MODES)
class ViRepeatSearchBackward(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True
        self.command = 'nv_vi_repeat_buffer_search'
        self.command_args = {
            'reverse': True
        }


@assign(seqs.SEQ['#'], MOTION_MODES)
@assign_text(['ReverseFindWord'], MOTION_MODES)
class ViReverseFindWord(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_vi_find_word_rev'
@assign(seqs.SEQ['*'], MOTION_MODES)
@assign_text(['FindWord'], MOTION_MODES)
class ViFindWord(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_vi_find_word'
@assign(seqs.SEQ['g⇧3'], MOTION_MODES)
@assign_text(['ReverseFindStr'], MOTION_MODES)
class ViReverseFindStr(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_vi_find_word_rev'
        self.command_args     = {'word_bound':False}
@assign(seqs.SEQ['g⇧8'], MOTION_MODES)
@assign_text(['FindStr'], MOTION_MODES)
class ViFindStr(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_vi_find_word'
        self.command_args     = {'word_bound':False}


@assign(seqs.SEQ['⇧z'], MOTION_MODES)
@assign(seqs.SEQ['⎈k'], MOTION_MODES)
@assign(seqs.SEQ['⎈w'], MOTION_MODES)
@assign(seqs.CTRL_W_G, MOTION_MODES)
@assign(seqs.SEQ['⎈x'], (INSERT,))
@assign(seqs.SEQ['g'], MOTION_MODES)
@assign(seqs.SEQ['['], MOTION_MODES)
@assign(seqs.SEQ[']'], MOTION_MODES)
@assign(seqs.SEQ['z'], MOTION_MODES)
@assign(seqs.SEQ['zu'], MOTION_MODES)
@assign(seqs.SEQ['⧵'], (SELECT,))
@assign(seqs.SEQ['⧵⧵'], (SELECT,))
@assign_text(['OpenNameSpace'], MOTION_MODES + (SELECT,INSERT))
class ViOpenNameSpace(ViMotionDef):  # TODO This should not be a motion.

    def translate(self, view):
        return {}


@assign(seqs.SEQ['"'], MOTION_MODES)
@assign_text(['OpenRegister'], MOTION_MODES, icon="®")
class ViOpenRegister(ViMotionDef):
    def translate(self, view):
        return {}

@assign_text(['ClearRegisters'], MOTION_MODES, icon="ᵡ®")
class ViClearRegisters(ViMotionDef):
    def init(self):
        self.command = 'nv_vi_clear_registers'
@assign_text(['ClearRegister'], ACTION_MODES, icon='ᵡ®?')
class ViClearRegister(RequireOneCharMixin, ViOperatorDef):
    def translate(self, view):
        return translate_action(view,'nv_vi_clear_register',{'register':self.inp})


@assign(seqs.CTRL_HOME, MOTION_MODES)
@assign(seqs.SEQ['gg'], MOTION_MODES)
@assign_text(['GotoBof'], MOTION_MODES, icon='⇱')
class ViGotoBof(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True

    def translate(self, view):
        return translate_motion(view,'nv_vi_goto_line_or_bof',{'count':get_count(view,default=0)})


@assign(seqs.SEQ['⇧g'], MOTION_MODES)
@assign_text(['GotoEof'], MOTION_MODES, icon='⇲')
class ViGotoEof(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True

    def translate(self, view):
        return translate_motion(view, 'nv_vi_goto_line_or_eof',{'count':get_count(view,default=0)})


@assign(seqs.SEQ['r'], ACTION_MODES)
@assign_text(['ReplaceCharacters'], ACTION_MODES)
class ViReplaceCharacters(RequireOneCharMixin, ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.repeatable       = True
    def translate(self, view):
        return translate_action(view, 'nv_vi_replace_char',{'char':self.inp})


@assign(seqs.SEQ['m'], ACTION_MODES)
@assign_text(['SetMark'], ACTION_MODES, icon='🖈Z')
class ViSetMark(RequireOneCharMixin, ViOperatorDef):
    def init(self):
        self.scroll_into_view = True

    def translate(self, view):
        return translate_action(view, 'nv_vi_m', {
            'character': self.inp
        })


@assign(seqs.SEQ['f'], MOTION_MODES)
@assign_text(['SearchCharForward'], MOTION_MODES, icon='🔎')
class ViSearchCharForward(RequireOneCharMixin, ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True

    def translate(self, view):
        return translate_motion(view, 'nv_vi_find_in_line', {
            'char': self.inp,
            'inclusive': True
        })


@assign(seqs.SEQ['t'], MOTION_MODES)
@assign_text(['SearchCharForwardTill'], MOTION_MODES, icon='🔎₋₁')
class ViSearchCharForwardTill(RequireOneCharMixin, ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True

    def translate(self, view):
        return translate_motion(view, 'nv_vi_find_in_line', {
            'char': self.inp,
            'inclusive': False
        })


@assign(seqs.SEQ['a'], (OPERATOR_PENDING, VISUAL, VISUAL_LINE, VISUAL_BLOCK))
@assign_text(['ATextObject'], (OPERATOR_PENDING, VISUAL, VISUAL_LINE, VISUAL_BLOCK))
class ViATextObject(RequireOneCharMixin, ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True

    def translate(self, view):
        return translate_motion(view, 'nv_vi_select_text_object', {
            'text_object': self.inp,
            'inclusive': True
        })


@assign(seqs.SEQ['i'], (OPERATOR_PENDING, VISUAL, VISUAL_LINE, VISUAL_BLOCK))
@assign_text(['ITextObject'], (OPERATOR_PENDING, VISUAL, VISUAL_LINE, VISUAL_BLOCK))
class ViITextObject(RequireOneCharMixin, ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True

    def translate(self, view):
        return translate_motion(view, 'nv_vi_select_text_object', {
            'text_object': self.inp,
            'inclusive': False
        })


@assign(seqs.SEQ['⇧f'], MOTION_MODES)
@assign_text(['SearchCharBackward'], MOTION_MODES, icon='🔍')
class ViSearchCharBackward(RequireOneCharMixin, ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True

    def translate(self, view):
        return translate_motion(view, 'nv_vi_reverse_find_in_line', {
            'char': self.inp,
            'inclusive': True
        })


@assign(seqs.SEQ['⇧t'], MOTION_MODES)
@assign_text(['SearchCharBackwardTill'], MOTION_MODES, icon='🔍₋₁')
class ViSearchCharBackwardTill(RequireOneCharMixin, ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True

    def translate(self, view):
        return translate_motion(view, 'nv_vi_reverse_find_in_line', {
            'char': self.inp,
            'inclusive': False
        })


@assign(seqs.SEQ["/"], MOTION_MODES)
@assign_text(['SearchForward'], MOTION_MODES, icon='◎🢖')
class ViSearchForward(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True
        self.input_parser = InputParser(
            InputParser.PANEL,
            command='nv_vi_search_forward',
            param='pattern'
        )

    @property
    def accept_input(self) -> bool:
        if not self.inp:
            return True

        return not self.inp.lower().endswith('<cr>')

    def accept(self, key: str) -> bool:
        self.inp += key

        return True

    def translate(self, view):
        if self.accept_input:
            return translate_motion(view, 'nv_vi_search_forward')

        # We'll end up here, for example, when repeating via '.'.
        return ViSearchForwardImpl(term=self.inp[:-4]).translate(view)


class ViSearchForwardImpl(ViMotionDef):
    def __init__(self, *args, term='', **kwargs):
        super().__init__(*args, **kwargs)
        self.scroll_into_view = True
        self.inp = term
        self.updates_xpos = True

    def translate(self, view):
        return translate_motion(view, 'nv_vi_search_forward_impl', {
            'pattern': self.inp,
        })


@assign(seqs.SEQ['?'], MOTION_MODES)
@assign_text(['SearchBackward'], MOTION_MODES, icon='🢔◎')
class ViSearchBackward(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos = True
        self.input_parser = InputParser(
            InputParser.PANEL,
            command='nv_vi_question_mark',
            param='pattern'
        )

    @property
    def accept_input(self) -> bool:
        if not self.inp:
            return True

        return not self.inp.lower().endswith('<cr>')

    def accept(self, key: str) -> bool:
        self.inp += key

        return True

    def translate(self, view):
        if self.accept_input:
            return translate_motion(view, 'nv_vi_question_mark')

        # We'll end up here, for example, when repeating via '.'.
        return ViSearchBackwardImpl(term=self.inp[:-4]).translate(view)


class ViSearchBackwardImpl(ViMotionDef):
    def __init__(self, *args, term='', **kwargs):
        super().__init__(*args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True
        self.inp = term

    def translate(self, view):
        return translate_motion(view, 'nv_vi_question_mark_impl', {
            'pattern': self.inp,
        })


@assign(seqs.CTRL_X_CTRL_L, (INSERT,))
@assign_text(['InsertLineWithCommonPrefix'], (INSERT,))
class ViInsertLineWithCommonPrefix(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_vi_complete_line'


@assign(seqs.SEQ['gm'], MOTION_MODES)
@assign_text(['MoveHalfScreenHorizontally'], MOTION_MODES)
class ViMoveHalfScreenHorizontally(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.command          = 'nv_vi_move_visline_middle'
@assign(seqs.SEQ['g⇧m'], MOTION_MODES)
@assign_text(['MoveHalfLineHorizontally'], MOTION_MODES)
class ViMoveHalfLineHorizontally(ViMotionDef):
    def init(self):
        self.updates_xpos     = True
        self.scroll_into_view = True
        self.command          = 'nv_vi_move_line_middle'


@assign_text(['VizMotion'], ACTION_MODES)
class VizMotion(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
    def translate(self, view):
        return translate_motion(view, 'nv_vi_z', {'action':get_partial_sequence(view)[1:],})
@assign_text(['VizAction'], ACTION_MODES)
class VizAction(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
    def translate(self, view):
        return translate_action(view, 'nv_vi_z', {'action':get_partial_sequence(view)[1:],})

@assign(seqs.SEQ['zh'], ACTION_MODES)
@assign(seqs.Z_LEFT   , ACTION_MODES)
@assign_text(['ScrollCharLeft'], ACTION_MODES, icon='◀')
class ViScrollCharLeft        (ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_scroll_char_left'
@assign(seqs.SEQ['zl'], ACTION_MODES)
@assign(seqs.Z_RIGHT  , ACTION_MODES)
@assign_text(['ScrollCharRight'], ACTION_MODES, icon='▶')
class ViScrollCharRight      (ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_scroll_char_right'
@assign(seqs.SEQ['z⇧h'], ACTION_MODES)
@assign_text(['ScrollHalfScreenLeft'], ACTION_MODES, icon='🢔½🗔')
class ViScrollHalfScreenLeft (ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_scroll_half_screen_left'
@assign(seqs.SEQ['z⇧l'], ACTION_MODES)
@assign_text(['ScrollHalfScreenRight'], ACTION_MODES, icon='½🗔🢖')
class ViScrollHalfScreenRight(ViMotionDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_scroll_half_screen_right'

@assign(seqs.SEQ['zg'], ACTION_MODES)
@assign_text(['AddSpellWord'], ACTION_MODES, icon='⇝⊕')
class ViAddSpellWord(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_add_spell_word'
@assign(seqs.ZUG      , ACTION_MODES)
@assign(seqs.ZUW      , ACTION_MODES)
@assign_text(['RemoveSpellWord'], ACTION_MODES, icon='⇝⊖')
class ViRemoveSpellWord(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_remove_spell_word'
@assign(seqs.Z_EQUAL  , ACTION_MODES)
@assign_text(['SelectSpellWord'], ACTION_MODES, icon='⇝☰')
class ViSelectSpellWord(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_select_spell_word'


@assign(seqs.SEQ['zc' ], ACTION_MODES)
@assign(seqs.SEQ['z⇧c'], ACTION_MODES)
@assign_text(['Fold'], ACTION_MODES)
class ViFold(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_fold'
@assign(seqs.SEQ['zo' ], ACTION_MODES)
@assign(seqs.SEQ['z⇧o'], ACTION_MODES)
@assign_text(['Unfold'], ACTION_MODES)
class ViUnfold(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_unfold'
@assign(seqs.SEQ['z⇧m'], ACTION_MODES)
@assign_text(['FoldAll'], ACTION_MODES)
class ViFoldAll(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_fold_all'
@assign(seqs.SEQ['z⇧r'], ACTION_MODES)
@assign_text(['UnfoldAll'], ACTION_MODES)
class ViUnfoldAll(ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.command          = 'nv_unfold_all'
