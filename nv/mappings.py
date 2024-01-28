import logging
import re
import traceback

from typing import Union

from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL
from NeoVintageous.nv import plugin
from NeoVintageous.nv.settings import get_mode
from NeoVintageous.nv.settings import get_partial_sequence, get_partial_text
from NeoVintageous.nv.settings import is_plugin_enabled
from NeoVintageous.nv.utils import get_file_type
from NeoVintageous.nv.variables import expand_keys
from NeoVintageous.nv.vi import keys
from NeoVintageous.nv.vi.cmd_base import CommandNotFound
from NeoVintageous.nv.vi.keys import to_bare_command_name
from NeoVintageous.nv.vi.keys import tokenize_keys, map_cmd2textcmd, map_textcmd2cmd
from NeoVintageous.nv.plugin  import map_cmd2textcmd as map_cmd2textcmdP, map_textcmd2cmd as map_textcmd2cmdP
from NeoVintageous.nv.modes import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE
from NeoVintageous.nv.modes import mode_names, mode_names_rev, mode_full_to_abbrev, mode_group_sort
from NeoVintageous.nv.log import addLoggingLevel, stream_handler

_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)
if _log.hasHandlers(): # clear existing handlers, including sublime's
    logging.getLogger().handlers.clear()
    _log.addHandler(stream_handler)

_mappings = {
    INSERT: {},
    NORMAL: {},
    OPERATOR_PENDING: {},
    SELECT: {},
    VISUAL_BLOCK: {},
    VISUAL_LINE: {},
    VISUAL: {}
}  # type: dict

_mappings_text = { # stores text_commands like ‘enter_insert_mode’ as opposed to ‘gin’
    INSERT          	: {},
    NORMAL          	: {},
    OPERATOR_PENDING	: {},
    SELECT          	: {},
    VISUAL_BLOCK    	: {},
    VISUAL_LINE     	: {},
    VISUAL          	: {}
}  # type: dict


class Mapping:

    def __init__(self, lhs: str, rhs: Union[str, list]):
        self.lhs = lhs
        self.rhs = rhs


class IncompleteMapping:
    pass


def _has_partial_matches(view, mode: str, lhs: str) -> bool:
    for map_lhs, map_rhs in _mappings[mode].items():
        if isinstance(map_rhs, str):
            if map_lhs.startswith(lhs):
                return True
        else:
            file_type = get_file_type(view)
            if file_type and file_type in map_rhs:
                if map_lhs.startswith(lhs):
                    return True
            elif '' in map_rhs:
                if map_lhs.startswith(lhs):
                    return True

    return False


def _has_partial_matches_text(view, mode: str, lhs: str) -> bool:
    for map_lhs, map_rhs in _mappings_text[mode].items():
        if isinstance(map_rhs, str):
            if map_lhs.startswith(lhs):
                return True
        else:
            file_type = get_file_type(view)
            if file_type and file_type in map_rhs:
                if map_lhs.startswith(lhs):
                    return True
            elif '' in map_rhs:
                if map_lhs.startswith(lhs):
                    return True

    return False


def _find_full_match(view, mode: str, lhs: str):
    rhs = _mappings[mode].get(lhs)
    if rhs:
        if isinstance(rhs, str):
            return rhs

        try:
            return _mappings[mode][lhs][get_file_type(view)]
        except KeyError:
            try:
                return _mappings[mode][lhs]['']
            except KeyError:
                pass

def _find_full_match_text(view, mode: str, lhs: str):
    rhs = _mappings_text[mode].get(lhs)
    if rhs:
        if isinstance(rhs, (str, list)):
            return rhs
        try:
            return _mappings_text[mode][lhs][get_file_type(view)]
        except KeyError:
            try:
                return _mappings_text[mode][lhs]['']
            except KeyError:
                pass


def _normalise_lhs(lhs: str) -> str:
    try:
        return ''.join(tokenize_keys(expand_keys(lhs)))
    except ValueError:
        traceback.print_exc()
        return lhs


import NeoVintageous.dep.kdl as kdl
import NeoVintageous.nv.cfg_parse
def mappings_add(mode:Union[str,list], lhs: str, rhs: str) -> None:
    # nnoremap FileType go gd :LspSymbolDefinition<CR>
    _log.map(" @mappings_add mode=%s lhs=%s rhs=%s"
        ,                      mode,    lhs,   rhs)
    modes = [mode] if isinstance(mode, str) else mode
    key = _normalise_lhs(lhs)
    # tag = None
    if NeoVintageous.nv.cfg_parse._dump_to_kdl:
        props = dict()
        (mode_l_sort,m_enum) = mode_group_sort(modes)
        mode_s = "".join(mode_l_sort) # Ⓝⓘ
        # if (cmd_sublime := rhs[1:]).startswith('"command"'): # Sublime commands
        #     # tag = "subl" # reserve this tag for parsed commands, not raw ones?
        #     cmd_subl = parse_user_sublime_cmdline(window, cmd_sublime)
        #     if not cmd_subl:
        #         _log.error(f"invalid Sublime command ‘{cmd_sublime}’")
        #     else:
        #         window.run_command(command['command'], command['args'])

    if re.match('^FileType$', lhs):
        if (parsed := re.match('^([^ ]+) ([^ ]+)\\s+', rhs)):
            file_types = parsed.group(1)
            key_s      = parsed.group(2)
            key        = _normalise_lhs(key_s)
            cmd_s      = rhs[len(parsed.group(0)):]
            if NeoVintageous.nv.cfg_parse._dump_to_kdl:
                cmd_txt = cmd_s
                for mode in modes: # find the first matching default key #todo: might be wrong if diff modes have diff defaults for the same command?
                    if (cmd_cls := keys.mappings[mode].get(cmd_s)): # ‘b’ → <...ViMoveByWordsBackward>
                        T = type(cmd_cls)
                        cmd_txt = map_cmd2textcmd[T][0] # ViMoveByWordsBackward → MoveByWordsBackward
                        props['def'] = cmd_s # save ‘b’ default vim key to props ‘def’
                        break
                if '"' in cmd_txt: # create a raw string to avoid escaping quotes
                    arg = kdl.RawString(tag=None,value=cmd_txt)
                else:
                    arg = kdl.   String(tag=None,value=cmd_txt)
                props['file'] = file_types
                node_key = kdl.Node(tag=mode_s, name=key, args=[arg], props=props)
                NeoVintageous.nv.cfg_parse._NVRC_KDL.nodes.append(node_key)
            for file_type in file_types.split(','):
                for mode in modes:
                    if not (match := _mappings[mode].get(key)):
                        _mappings[mode][key] = {}
                    elif isinstance(match, str):
                        _mappings[mode][key] = {'': match}
                    _mappings    [mode][key][file_type] = cmd_s
                    #                   gd   go           :LspSymbolDefinition<CR>
            return
    if NeoVintageous.nv.cfg_parse._dump_to_kdl:
        cmd_s   = rhs
        cmd_txt = cmd_s
        cmd_cls = None         # find the first matching default key in the same mode
        _cmd2textcmd = None # store either keys or plugin dict depending on which one matched
        if (cmd_cls_key  := keys  .mappings[mode].get(cmd_s)): # ‘b’  → <...ViMoveByWordsBackward>
            cmd_cls = cmd_cls_key
            _cmd2textcmd = map_cmd2textcmd
        if (cmd_cls_plug := plugin.mappings[mode].get(cmd_s)): # ‘gh’ → <...MultipleCursorsStart>
            cmd_cls = cmd_cls_plug
            _cmd2textcmd = map_cmd2textcmdP
        if not cmd_cls:
            for mode in modes: # find the first matching default key
                if (cmd_cls_key  := keys  .mappings[mode].get(cmd_s)):
                    cmd_cls = cmd_cls_key
                    _cmd2textcmd = map_cmd2textcmd
                    break
                if (cmd_cls_plug := plugin.mappings[mode].get(cmd_s)):
                    cmd_cls = cmd_cls_plug
                    _cmd2textcmd = map_cmd2textcmdP
                    break
        if cmd_cls: # found a match
            T = type(cmd_cls)
            cmd_txt = _cmd2textcmd[T][0] # ViMoveByWordsBackward → MoveByWordsBackward
            props['def'] = cmd_s # save ‘b’ default vim key to props ‘def’
        if '"' in cmd_txt: # create a raw string to avoid escaping quotes
            arg = kdl.RawString(tag=None,value=cmd_txt)
        else:
            arg = kdl.   String(tag=None,value=cmd_txt)
        node_key = kdl.Node(tag=mode_s, name=key, args=[arg], props=props)
        NeoVintageous.nv.cfg_parse._NVRC_KDL.nodes.append(node_key)

    for mode in modes:
        _mappings[mode][key] = rhs

def mappings_add_text(mode:str, key:str, cmd:Union[str,list], prop:dict={}) -> None:
    #           mode_normal     W        MoveByBigWords       {file:['txt','rs']}
    key_norm = _normalise_lhs(key)
    old_cmd_ftype = _mappings_text[mode].get(key_norm)
    _log.map(" map+txt ¦%s¦ ‹¦%s ≈ %s¦⟶¦%s¦› @file¦%s¦ oldcmd¦%s¦"
      ,                mode, key,key_norm,cmd,prop.get('file',''),old_cmd_ftype)
    if (file_types := prop.get('file')):
        for file_type in file_types:
            if not old_cmd_ftype:
                _mappings_text[mode][key_norm]            = {}
            elif (isinstance(old_cmd_ftype,str ) or\
                  isinstance(old_cmd_ftype,list)):
                _mappings_text[mode][key_norm]            = {'':old_cmd_ftype}
            _mappings_text    [mode][key_norm][file_type] = cmd
        return
    if           (isinstance(old_cmd_ftype,dict)): # don't overwrite existing filetype commands
        _mappings_text        [mode][key_norm][''       ] = cmd
    else:                                          # ok to overwrite old commands
        _mappings_text        [mode][key_norm]            = cmd


def mappings_remove(mode: str, lhs: str) -> None:
    del _mappings[mode][_normalise_lhs(lhs)]
    del _mappings_text[mode][_normalise_lhs(lhs)]


def clear_mappings() -> None:
    for mode in _mappings:
        _mappings[mode] = {}
    for mode in _mappings_text:
        _mappings_text[mode] = {}


def mappings_can_resolve(view, key: str) -> bool:
    mode = get_mode(view)
    sequence = get_partial_sequence(view) + key

    if _find_full_match(view, mode, sequence):
        return True

    if _has_partial_matches(view, mode, sequence):
        return True

    return False

def mappings_can_resolve_text(view, key: str) -> bool:
    mode = get_mode         (view)
    cmd  = get_partial_text (view) + key
    if _find_full_match_text(view, mode, cmd):
        return True
    # if _has_partial_matches(view, mode, cmd): # todo not needed?
        # return True
    return False


def _seq_to_mapping(view, seq: str):
    mode = get_mode(view)
    full_match = _find_full_match(view, mode, seq)
    if full_match:
        return Mapping(seq, full_match)

def _text_cmd_to_mapping(view, _text_cmd: str):
    mode = get_mode(view)
    full_match = _find_full_match_text(view, mode, _text_cmd)
    if full_match:
        return Mapping(_text_cmd, full_match)


def _text_to_command(view, text: str):
    """ Convert textual command (MoveByLineCols) into command function (ViMoveByLineCols)
        ←  view	View	.
         text  	str 	Text command, eg, 'MoveByLineCols'
        → ViCommandDefBase | CommandNotFound
    """
    cmd_plugin  = plugin.map_textcmd2cmd.get(text)
    cmd_keys    =   keys.map_textcmd2cmd.get(text)
    _log.map(" cmd_text ‘%s’ → cmd_plugin ‘%s’ cmd_keys = ‘%s’"
        ,               text,       cmd_plugin,         cmd_keys)
    if cmd_plugin and is_plugin_enabled(view, cmd_plugin):
        return cmd_plugin
    if cmd_keys:
        return cmd_keys
    return CommandNotFound()


def _seq_to_command(view, seq: str, mode: str):
    # Return the command definition mapped for seq and mode.
    #
    # Args:
    #   view (View):
    #   seq (str): The command sequence.
    #   mode (str): Forces the use of this mode instead of the global state's.
    #
    # Returns:
    #   ViCommandDefBase
    #   CommandNotFound
    if mode in plugin.mappings:
        plugin_command = plugin.mappings[mode].get(seq)
        if plugin_command:
            if is_plugin_enabled(view, plugin_command):
                return plugin_command

    if mode in keys.mappings:
        command = keys.mappings[mode].get(seq)
        _log.map(" keys_cmd=%s from seq=%s",command,seq)
        if command:
            return command

    return CommandNotFound()


def mappings_resolve(view, sequence: str = None, mode: str = None, check_user_mappings: bool = True):
    # Look at the current global state and return the command mapped to the available sequence.
    #
    # Args:
    #   sequence (str): The command sequence. If a sequence is passed, it is
    #       used instead of the global state's. This is necessary for some
    #       commands that aren't name spaces but act as them (for example,
    #       ys from the surround plugin).
    #   mode (str): If different than None, it will be used instead of the
    #       global state's. This is necessary when we are in operator
    #       pending mode and we receive a new action. By combining the
    #       existing action's name with name of the action just received we
    #       could find a new action.
    #   check_user_mappings (bool):
    #
    # Returns:
    #   Mapping:
    #   IncompleteMapping
    #   CommandNotFound

    # We usually need to look at the partial sequence, but some commands do
    # weird things, like ys, which isn't a namespace but behaves as such.
    _log.map("  inSEQ¦%s¦ part_seq¦%s¦",sequence,get_partial_sequence(view))
    seq = sequence or get_partial_sequence(view)

    command = None

    if check_user_mappings:
        # Resolve the full sequence rather than the "bare" sequence, because the
        # user may have defined some mappings that start with numbers (counts),
        # or " (register character), which are stripped from the bare sequences.
        # See https://github.com/NeoVintageous/NeoVintageous/issues/434.

        # XXX The reason these does not pass the mode, and instead uses the
        # get_mode(), is because implementation of commands like dd are a bit
        # hacky. For example, the dd definition does is not assigned to operator
        # pending mode, the second d is instead caught by the feed key command
        # and resolved by specifying NORMAL mode explicitly, which resolves the
        # delete line command definition. Commands like this can probably be
        # fixed by allowing the definitions to handle the OPERATOR PENDING and
        # let the definition handle any special-cases itself instead of passing
        # off the responsibility to the feed key command.

        command = _seq_to_mapping(view, seq)
        _log.map(" inSEQ user_map _seq_to_mapping¦‘%s’",command)

        if not command:
            if not sequence:
                if _has_partial_matches(view, get_mode(view), seq):
                    return IncompleteMapping()

    if not command:
        command = _seq_to_command(view, to_bare_command_name(seq), mode or get_mode(view))
        _log.map(" inSEQ _seq_to_command¦‘%s’",command)

    _log.map(' @mapRes → lhs‘%s’ rhs‘%s’ m‘%s’ seq=‘%s’ ‘%s’'
        ,command.lhs if hasattr(command, 'lhs') else ''
        ,command.rhs if hasattr(command, 'rhs') else ''
        ,                                mode, sequence, command.__class__.__mro__)

    return command

def mappings_resolve_text(view, text_commands: list = None, mode: str = None, check_user_mappings: bool = True):
    # Check current global state and return the command mapped to the available list of text_commands
    # ←
      # sequence           	list	sequence of text_commands
      # mode               	str 	if passed, use instead of the global state's
      # check_user_mappings	bool	.
    # → Mapping |  CommandNotFound

    # We usually need to look at the partial sequence, but some commands do weird things, like ys, which isn't a namespace but behaves as such.
    _log.map("  inTXT text_commands = ‘%s’  get_partial_text = ‘%s’", text_commands,get_partial_text(view))
    text_cmd = text_commands or get_partial_text(view)
    command = None
    if check_user_mappings:
        command = _text_cmd_to_mapping(view, text_cmd)
        _log.map("  inTXT user_map _text_cmd_to_mapping¦‘%s’",command)
        if not command:
            if not text_cmd:
                if _has_partial_matches_text(view, get_mode(view), text_cmd):
                    return IncompleteMapping()
    if not command:
        command = _text_to_command(view, text_cmd)
        _log.map("  inTXT _text_to_command¦‘%s’",command)
    _log.map(' @MapResText usr‘%s’ → lhs‘%s’ rhs‘%s’ m‘%s’ text_cmd‘%s’ cmd‘%s’'
        ,check_user_mappings
        ,command.lhs if hasattr(command,'lhs') else ''
        ,command.rhs if hasattr(command,'rhs') else ''
        ,                                mode, text_cmd, command.__class__.__mro__)
    return command
