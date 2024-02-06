import logging

from NeoVintageous.nv.settings import get_mode, get_sequence, set_interactive, set_mode, set_repeat_data
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
        initial_mode = get_mode(self.view)
        cont = self.cont
        # if not commands:
        #     _log.error(" couldn't find command ‘%s’ in a list of text commands",cmdT)
        #     return
        # commands = map_cmd2textcmd.get(cmdT,None)
        # cmd = commands[0] # EnterInsertMode
        _log.key('processing cmd txt ‘%s’ #%s act=‘%s’'
            ,                   text_cmd,count,get_action(self.view))

        set_interactive(self.view, False) # Disable interactive prompts. For example, supress interactive input collecting for the command-line and search: :ls<CR> and /foo<CR>
        leading_motions = '' # run any motions coming before the first action. We don't keep these in the undo stack, but they will still be repeated via '.'. This ensures that undoing will leave the caret where the  first editing action started. For example, 'lldl' would skip 'll' in the undo history, but store the full sequence for '.' to use
        # First, run any motions coming before the first action. We don't keep these in the undo stack, but they will still be repeated via '.'. This ensures that undoing will leave the caret where the  first editing action started. For example, 'lldl' would skip 'll' in the undo history, but store the full sequence for '.' to use.
        leading_motions = ''
        key_cont = None

        if not self.cont and\
           not get_action(self.view): # 1st command or no action, so execute it
            _log.key("  ‘%s’ lead‘%s’ nv_feed_text_cmd(HFeedTextCmd) doEval→False @ HProcessCmdText",text_cmd,leading_motions)
            self.window.run_command('nv_feed_text_cmd',{'text_cmd':text_cmd,'do_eval':False,'count':count})

            if get_action(self.view): # The last key press has caused an action to be primed. That means there are no more leading motions. Break out of here
                reset_command_data(self.view)
                if  get_mode(self.view) == OPERATOR_PENDING:
                    set_mode(self.view, NORMAL)
                _log.key("    ~break, get_action exists")
                # break
            elif is_runnable(self.view): # Run any primed motion
                leading_motions += get_sequence(self.view)
                _log.key("    running primed motion ‘%s’",leading_motions)
                evaluate_state    (self.view)
                reset_command_data(self.view)
            else:
                _log.key("    evaluate_state")
                evaluate_state    (self.view)

        if must_collect_input(self.view, get_motion(self.view), get_action(self.view)): # State is requesting more input, so this is the last command in the sequence and it needs more input
            if self.cont:
                _log.key("  ↩− _collect→feed_key ‘%s’¦‘%s’ lead‘%s’ nv_feed_text_cmd(HFeedTextCmd) doEval→True @HProcessCmdText",key_cont,keys,leading_motions)
                self.window.run_command('nv_feed_text_cmd',{'text_cmd':text_cmd,'do_eval':True,'count':count})
            else:
                _log.key("  ↩− _collect_input")
                self._collect_input()
            return

        if not (get_motion(self.view) and\
           not  get_action(self.view)):
            with gluing_undo_groups(self.view):
                try:
                    if   get_mode(self.view) in (INSERT, REPLACE):
                        _log.key("  key sequence notation handler would insert chars here, but we still do commands!")
                    _log.key("  ‘%s’ lead‘%s’ nv_feed_text_cmd(HFeedTextCmd) doEval→None @HProcessCmdText",text_cmd,leading_motions)
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

            _log.key("_collect_input mot‘%s’⎀?%s‘%s’ act‘%s’⎀?%s‘%s’  inParse=%s  isInter=%s"
                ,motion,motion.accept_input if motion else '_',motion.inp if motion else '_'
                ,action,action.accept_input if action else '_',action.inp if action else '_'
                ,command.input_parser, command.input_parser.is_interactive())
            if command.input_parser and command.input_parser.is_interactive():
                _log.key("_collect_input interactive ‘%s’",command.inp)
                command.input_parser.run_interactive_command(self.window, command.inp)

        except IndexError:
            _log.debug('could not find a command to collect more user input')
            ui_bell()
        finally:
            set_interactive(self.view, True)


class ProcessNotationHandler():

    def __init__(self, view, keys: str, repeat_count: int, check_user_mappings: bool, cont:bool=False):
        self.view                = view
        self.window              = self.view.window()
        self.keys                = keys
        self.repeat_count        = repeat_count
        self.check_user_mappings = check_user_mappings
        self.cont                = cont # force continuation for sequences that come after text commands, not after sequences, so they aren't processed in one batch, thus state set within HProcNotation isn't checked before processing the first key

    def handle(self) -> None:
        keys = self.keys
        repeat_count = self.repeat_count
        check_user_mappings = self.check_user_mappings
        initial_mode = get_mode(self.view)

        _log.info('processing notation ‘%s’ #%s usrMap=%s act=‘%s’',
            keys,repeat_count,check_user_mappings,get_action(self.view))

        set_interactive(self.view, False) # Disable interactive prompts. For example, supress interactive input collecting for the command-line and search: :ls<CR> and /foo<CR>.

        # First, run any motions coming before the first action. We don't keep these in the undo stack, but they will still be repeated via '.'. This ensures that undoing will leave the caret where the  first editing action started. For example, 'lldl' would skip 'll' in the undo history, but store the full sequence for '.' to use.
        leading_motions = ''
        if _L: # preiterate to know the full count of keys for logging 1/5, 2/5, ...
            keys_iter = []
            for key in tokenize_keys(keys):
                keys_iter.append(key)
            key_count = len(keys_iter)
        else: # or just use a generator when we don't care about logs
            keys_iter = tokenize_keys(keys)
            key_count = '_'
        key_cont = None
        for i,key in enumerate(keys_iter):
            _log.key("  —%s¦%s—‘%s’¦‘%s’ lead‘%s’ nv_feed_key(HFeedKey) doEval→False @ HProcessNotation",i+1,key_count,key,keys,leading_motions)
            if self.cont and get_action(self.view): # check if we need to break early on continuation sequence before processing the "1st" key that's not really the 1st
                _log.key("    break early, get_action exists")
                key_cont = key
                break
            self.window.run_command('nv_feed_key',{'key':key,'do_eval':False,
                'repeat_count':repeat_count,'check_user_mappings':check_user_mappings})

            if get_action(self.view): # The last key press has caused an action to be primed. That means there are no more leading motions. Break out of here
                reset_command_data(self.view)
                if  get_mode(self.view) == OPERATOR_PENDING:
                    set_mode(self.view, NORMAL)
                _log.key("    break, get_action exists")
                break
            elif is_runnable(self.view): # Run any primed motion
                leading_motions += get_sequence(self.view)
                _log.key("    running primed motion ‘%s’",leading_motions)
                evaluate_state    (self.view)
                reset_command_data(self.view)
            else:
                _log.key("    evaluate_state")
                evaluate_state    (self.view)

        if must_collect_input(self.view, get_motion(self.view), get_action(self.view)): # State is requesting more input, so this is the last command in the sequence and it needs more input
            if self.cont:
                _log.key("  ↩− _collect→feed_key ‘%s’¦‘%s’ lead‘%s’ nv_feed_key(HFeedKey) doEval→True @ HProcessNotation",key_cont,keys,leading_motions)
                self.window.run_command('nv_feed_key',{'key':key_cont,'do_eval':True,
                'repeat_count':repeat_count,'check_user_mappings':check_user_mappings})
            else:
                _log.key("  ↩− _collect_input")
                self._collect_input()
            return

        if leading_motions:# Strip the already run commands
            if ((len(leading_motions) == len(keys)) and (not must_collect_input(self.view, get_motion(self.view), get_action(self.view)))):  # noqa: E501
                set_interactive(self.view, True)
                _log.key("  ↩ leading_motions, not collect")
                return
            leading_motions_len =     len(list(tokenize_keys(leading_motions)))
            keys                = ''.join(list(tokenize_keys(keys))[leading_motions_len:])

        if not (get_motion(self.view) and not get_action(self.view)):
            with gluing_undo_groups(self.view):
                try:
                    if _L: # preiterate to know the full count of keys for logging 1/5, 2/5
                        keys_iter = []
                        for key in tokenize_keys(keys):
                            keys_iter.append(key)
                        key_count = len(keys_iter)
                    else: # or just use a generator when we don't care about logs
                        keys_iter = tokenize_keys(keys)
                        key_count = '_'
                    for i,key in enumerate(keys_iter):
                        if key.lower() == '<esc>':
                            _log.key("⎋")
                            enter_normal_mode(self.window) # XXX: We should pass a mode here?
                            continue
                        elif get_mode(self.view) not in (INSERT, REPLACE):
                            _log.key("  —%s¦%s—‘%s’¦‘%s’ nv_feed_key(HFeedKey) doEval→None @ HProcessNotation",i+1,key_count,key,keys)
                            self.window.run_command('nv_feed_key',{'key':key,
                                'repeat_count':repeat_count,'check_user_mappings':check_user_mappings})
                        else:
                            _log.key("  —%s¦%s—‘%s’¦‘%s’ insert chars @ HProcessNotation",i+1,key_count,key,keys)
                            self.window.run_command('insert',{'characters':translate_char(key)})
                    if not must_collect_input(self.view, get_motion(self.view), get_action(self.view)):
                        return
                finally:
                    set_interactive(self.view, True)
                    # Ensure we set the full command for "." to use, but don't store "." alone.
                    if (leading_motions + keys) not in ('.', 'u', '<C-r>'):
                        set_repeat_data(self.view, ('vi', (leading_motions + keys), initial_mode, None))

        # We'll reach this point if we have a command that requests input whose input parser isn't satistied. For example, `/foo`. Note that `/foo<CR>`, on the contrary, would have satisfied the parser.
        action = get_action(self.view)
        motion = get_motion(self.view)
        _log.debug('unsatisfied parser action = %s, motion=%s', action, motion)

        if (action and motion): # We have a parser an a motion that can collect data. Collect data interactively.
            motion_data = motion.translate(self.view) or None
            if motion_data is None:
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

            _log.key("_collect_input mot‘%s’⎀?%s‘%s’ act‘%s’⎀?%s‘%s’  inParse=%s  isInter=%s"
                ,motion,motion.accept_input if motion else '_',motion.inp if motion else '_'
                ,action,action.accept_input if action else '_',action.inp if action else '_'
                ,command.input_parser, command.input_parser.is_interactive())
            if command.input_parser and command.input_parser.is_interactive():
                _log.key("_collect_input interactive ‘%s’",command.inp)
                command.input_parser.run_interactive_command(self.window, command.inp)

        except IndexError:
            _log.debug('could not find a command to collect more user input')
            ui_bell()
        finally:
            set_interactive(self.view, True)
