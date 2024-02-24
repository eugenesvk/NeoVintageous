import logging

from NeoVintageous.nv.settings import get_mode, get_sequence, get_partial_sequence, set_interactive, set_mode, set_repeat_data, get_register, get_capture_register, get_count, get_action_count,  get_motion_count
from NeoVintageous.nv.state    import evaluate_state, get_action, get_motion, is_runnable, must_collect_input, reset_command_data
from NeoVintageous.nv.ui       import ui_bell
from NeoVintageous.nv.utils    import gluing_undo_groups, translate_char
from NeoVintageous.nv.vi.keys  import tokenize_keys, map_cmd2textcmd
from NeoVintageous.nv.modes    import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE
from NeoVintageous.nv.vim      import enter_normal_mode, run_motion
from NeoVintageous.nv.vi.cmd_base import CommandNotFound, ViCommandDefBase, ViMotionDef, ViOperatorDef
from NeoVintageous.nv.vi.cmd_defs import ViRedo,ViUndo,ViRepeat


from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL
_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)
if _log.hasHandlers(): # clear existing handlers, including sublime's
    logging.getLogger(__name__).handlers.clear()
    # _log.addHandler(stream_handler)
_L = True if _log.isEnabledFor(logging.KEY) else False


_cmd_exclude = []
for cmd in [ViRedo,ViUndo,ViRepeat]:
    for txt in map_cmd2textcmd[cmd]: #['Redo','RedoAlias']
        _cmd_exclude.append(txt.lower()) # ['Redo','RedoAlias','Undo','Repeat']
_log.debug('_cmd_exclude ‘%s’', _cmd_exclude)

from typing  import Union
class ProcessCmdTextHandler():
    def __init__(self, view, text_cmd:str, count:int, cont:bool=False):
        self.view     = view
        self.window   = self.view.window()
        self.text_cmd = text_cmd
        self.count    = count
        self.cont     = cont # force continuation for sequences that come after text commands, not after sequences, so they aren't processed in one batch, thus state set within HProcNotation isn't checked before processing the first key


    def handle(self) -> None:
        text_cmd = self.text_cmd # EnterInsertMode
        count    = self.count
        cont     = self.cont
        initial_mode = get_mode(self.view)
        _log.keyt('processing cmd txt ‘%s’ #%s act=‘%s’ seq‘%s’ seqP‘%s’'
            ,                   text_cmd,count,get_action(self.view),get_sequence(self.view),get_partial_sequence(self.view))

        set_interactive(self.view, False) # Disable interactive prompts. For example, supress interactive input collecting for the command-line and search: :ls<CR> and /foo<CR>
        leading_motions = [] # run any motions coming before the first action. We don't keep these in the undo stack, but they will still be repeated via '.'. This ensures that undoing will leave the caret where the  first editing action started. For example, 'lldl' would skip 'll' in the undo history, but store the full sequence for '.' to use
        key_cont = None

        cmd_reg = {} # store i,key that set the register so that we can skip it in iter² (!but index should be adjusted for leading_motions that modifies keys)
        if not self.cont and\
           not get_action(self.view): # 1st command or no action, so execute it
            _log.keyt("  ‘%s’ lead‘%s’ mot‘%s’ act‘%s’ reg‘%s’%s seq‘%s’ seqP‘%s’ nv_feed_text_cmd(HFeedTextCmd) doEval→False @TXT",text_cmd,leading_motions,get_motion(self.view),get_action(self.view),get_register(self.view),get_capture_register(self.view),get_sequence(self.view),get_partial_sequence(self.view))
            _reg_pre = get_capture_register(self.view)
            self.window.run_command('nv_feed_text_cmd',{'text_cmd':text_cmd,'do_eval':False,'count':count})
            if not _reg_pre == get_capture_register(self.view):
                _log.keyy("    ‘%s’ #%s set the register, remember to skip it!",text_cmd,0)
                cmd_reg[0] = text_cmd














            if get_action(self.view): # The last key press has caused an action to be primed. That means there are no more leading motions. Break out of here
                setReg = True
                if not get_register(self.view) == '"': # don't clean reg/seq if register non-standard? #todo: test workaround for register cleared up when it shouldn't in nnoremap X dd
                    setReg = False
                _log.keyt("    ~break, get_action exists mot‘%s’⋅#%s act‘%s’⋅#%s reg‘%s’%s, reset state seq‘’, reg_%s m%s ⋅#%s seq‘%s’ seqP‘%s’",get_motion(self.view),get_motion_count(self.view), get_action(self.view),get_action_count(self.view), get_register(self.view),get_capture_register(self.view),setReg, get_mode(self.view), get_count(self.view),get_sequence(self.view),get_partial_sequence(self.view))
                reset_command_data(self.view,setReg=setReg,setACount=False)
                if  get_mode(self.view) == OPERATOR_PENDING:
                    set_mode(self.view, NORMAL)
                # break
            elif is_runnable(self.view): # Run any primed motion
                leading_motions.append(get_sequence(self.view))
                _log.keyt("    running primed motion ‘%s’, reset state seq‘’",leading_motions)
                evaluate_state    (self.view)
                reset_command_data(self.view)
            else:
                _log.keyt("    evaluate_state")
                evaluate_state    (self.view)

        if must_collect_input(self.view, get_motion(self.view), get_action(self.view)): # State is requesting more input, so this is the last command in the sequence and it needs more input
            if self.cont:
                _log.keyt("  ↩− _collect→feed_text lead‘%s’ mot‘%s’ act‘%s’ reg‘%s’%s seq‘%s’ seqP‘%s’ nv_feed_text_cmd(HFeedTextCmd) doEval→True @TXT",leading_motions,get_motion(self.view),get_action(self.view),get_register(self.view),get_capture_register(self.view),get_sequence(self.view),get_partial_sequence(self.view))
                self.window.run_command('nv_feed_text_cmd',{'text_cmd':text_cmd,'do_eval':True,'count':count})

            else:
                _log.keyt("  ↩− _collect_input")
                self._collect_input()
            return

        reg_i_offset = 0
        if leading_motions:# Strip the already run commands
            leading_motions_len = len(leading_motions)
            text_cmd_len        = len(text_cmd) if isinstance(text_cmd,list) else 1
            if ((leading_motions_len == text_cmd_len) and\
                (not must_collect_input(self.view,get_motion(self.view),get_action(self.view)))):  # noqa: E501
                set_interactive(self.view, True)
                _log.keyt("  ↩ leading_motions ‘%s’, not collect",leading_motions)
                return

            text_cmd_next = text_cmd[leading_motions_len:] # todo: use ↓ for iteration if this handler is converted to accept a list of commands
            reg_i_offset = leading_motions_len # todo: use for index match if this accepts a list of commands

        if not (get_motion(self.view) and\
           not  get_action(self.view)):
            with gluing_undo_groups(self.view):
                try:













                    if   get_mode(self.view) in (INSERT, REPLACE):
                        _log.keyt("  key sequence notation handler would insert chars here, but we still do commands!")
                    _log.keyt("  ²—‘%s’ lead‘%s’ mot‘%s’ act‘%s’ reg‘%s’%s seq‘%s’ seqP‘%s’ nv_feed_text_cmd(HFeedTextCmd) doEval→None @TXT",text_cmd,leading_motions,get_motion(self.view),get_action(self.view),get_register(self.view),get_capture_register(self.view),get_sequence(self.view),get_partial_sequence(self.view))
                    if 0 in cmd_reg and cmd_reg[0] == text_cmd:
                        _log.key("    ‘%s’ #%s (%s) set the register, skip it!",text_cmd,0,0)
                    else:
                        self.window.run_command('nv_feed_text_cmd',{'text_cmd':text_cmd,'count':count})
                    if not must_collect_input(self.view, get_motion(self.view), get_action(self.view)):
                        return







                finally:
                    set_interactive(self.view, True) # !!!todo likely ↓ bugs since not sure repeat data handlex text commands
                    if text_cmd not in _cmd_exclude: # Ensure we set the full command for "." to use, but don't store "." alone.
                        set_repeat_data(self.view, ('native',(text_cmd),initial_mode,None))

        # We'll reach this point if we have a command that requests input whose input parser isn't satistied. For example, `/foo`. Note that `/foo<CR>`, on the contrary, would have satisfied the parser.
        action = get_action(self.view)
        motion = get_motion(self.view)
        _log.debug('unsatisfied parser action = %s, motion=%s', action, motion)

        if (action and motion): # We have a parser an a motion that can collect data. Collect data interactively.
            motion_data = motion.translate(self.view) or None
            if motion_data is None:
                _log.keyt("    running motion ‘%s’, reset state seq‘’",motion_data)
                reset_command_data(self.view)
                ui_bell()
                return
            run_motion(self.window, motion_data)
            return

        self._collect_input()

    def _collect_input(self) -> None:
        try:
            motion = get_motion(self.view)
            action = get_action(self.view)

            command = None

            if motion and action:
                if motion.accept_input:
                    command = motion
                else:
                    command = action
            else:
                command = action or motion

            _log.keyt("_collect_input mot‘%s’⎀?%s‘%s’ act‘%s’⎀?%s‘%s’  inParse=%s  isInter=%s"
                ,motion,motion.accept_input if motion else '_',motion.inp if motion else '_'
                ,action,action.accept_input if action else '_',action.inp if action else '_'
                ,command.input_parser, command.input_parser.is_interactive())
            if command.input_parser and command.input_parser.is_interactive():
                _log.keyt("_collect_input interactive ‘%s’",command.inp)
                command.input_parser.run_interactive_command(self.window, command.inp)

        except IndexError:
            _log.debug('could not find a command to collect more user input')
            ui_bell()
        finally:
            set_interactive(self.view, True)
