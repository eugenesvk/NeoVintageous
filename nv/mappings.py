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
from NeoVintageous.nv.vi.keys import to_bare_command_name, tokenize_keys
from NeoVintageous.nv.vi.cmd_base import CommandNotFound
from NeoVintageous.nv.modes import Mode as M, M_ANY, INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE
from NeoVintageous.nv.modes import mode_names, mode_names_rev, mode_full_to_abbrev, mode_group_sort, MODE_NAMES_OLD, MODE_HELP

from NeoVintageous.nv.log import addLoggingLevel, stream_handler

_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)
if _log.hasHandlers(): # clear existing handlers, including sublime's
    logging.getLogger(__name__).handlers.clear()
    # _log.addHandler(stream_handler)

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


re_flags = 0
re_flags |= re.MULTILINE | re.IGNORECASE
key_non_lt = r"^<[^<>]+>"
re_key_non_lt = re.compile(key_non_lt, flags=re_flags)
def _has_partial_matches(view, mode: str, lhs: str) -> bool:
    for map_lhs, map_rhs in _mappings[mode].items():
        if isinstance(map_rhs, str):
            if map_lhs.startswith(lhs):
                if   lhs == '<lt>':
                    return True
                elif lhs == '<':
                    if   map_lhs.startswith('<lt>'):
                        return True
                    elif re_key_non_lt.match(map_lhs):
                        continue
                    else:
                        return True
                else:
                    return True
        else:
            file_type = get_file_type(view)
            if file_type and file_type in map_rhs:
                if map_lhs.startswith(lhs):
                    if lhs == '<':
                        if map_lhs.startswith('<lt>'):
                            return True
                        elif re_key_non_lt.match(map_lhs):
                            continue
                        else:
                            return True
                    else:
                        return True
            elif '' in map_rhs:
                if map_lhs.startswith(lhs):
                    if lhs == '<':
                        if map_lhs.startswith('<lt>'):
                            return True
                        elif re_key_non_lt.match(map_lhs):
                            continue
                        else:
                            return True
                    else:
                        return True

    return False

def _has_partial_matches_text(view, mode: str, lhs: str) -> bool:
    for map_lhs, map_rhs in _mappings_text[mode].items():
        if isinstance(map_rhs, str ) or\
           isinstance(map_rhs, list): #bb ['movetoeol']
            if map_lhs.startswith(lhs):
                if lhs == '<':
                    if map_lhs.startswith('<lt>'):
                        return True
                    elif re_key_non_lt.match(map_lhs):
                        continue
                    else:
                        return True
                else:
                    return True
        else:
            file_type = get_file_type(view)
            if file_type and file_type in map_rhs:
                if map_lhs.startswith(lhs):
                    if lhs == '<':
                        if map_lhs.startswith('<lt>'):
                            return True
                        elif re_key_non_lt.match(map_lhs):
                            continue
                        else:
                            return True
                    else:
                        return True
            elif '' in map_rhs:
                if map_lhs.startswith(lhs):
                    if lhs == '<':
                        if map_lhs.startswith('<lt>'):
                            return True
                        elif re_key_non_lt.match(map_lhs):
                            continue
                        else:
                            return True
                    else:
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
    rhs     = _mappings_text[mode].get(lhs)
    if not rhs\
       and lhs == '<':
        lhs     = '<lt>'
        rhs =          _mappings_text[mode].get(lhs)
    if rhs:
        if isinstance(rhs, (str, list)):
            return     rhs
        try:
            return     _mappings_text[mode][lhs][get_file_type(view)]
        except     KeyError:
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


def key2textcmd(key:str,mode:M) -> dict:
  # keys.map_textcmd2cmd[cmd] = cls(*args,**kwargs)
  # keys.map_cmd2textcmd[cls internal command Name] = [textual,command,name(s)] from ↑ (preserves CaSe)

  mode_name = MODE_NAMES_OLD[mode]
  cmd_txt_d = dict(main=None,plugin=None)
  if mode_name not in keys.mappings: # empty modes or _ fillers
    return None
  if (cmd_cls :=   keys.mappings[mode_name].get(key)): # ‘b’ → <...ViMoveByWordsBackward>
    T = type(cmd_cls)
    cmd_txt =   keys.map_cmd2textcmd[T][0] # ViMoveByWordsBackward → MoveByWordsBackward
    cmd_txt_d['main']   = cmd_txt
    # print(f"found cmd in def ¦{cmd_txt}¦ for T=¦{T}¦")
  if (cmd_cls := plugin.mappings[mode_name].get(key)): # ‘gh’ → <...MultipleCursorsStart>
    T = type(cmd_cls)
    cmd_txt = plugin.map_cmd2textcmd[T][0] # MultipleCursorsStart → MultipleCursorsStart
    cmd_txt_d['plugin'] = cmd_txt
    # print(f"found cmd in plug ¦{cmd_txt}¦ for T=¦{T}¦")
  return cmd_txt_d


import NeoVintageous.dep.kdl as kdl
import NeoVintageous.dep.kdl2 as kdl2
import NeoVintageous.nv.cfg_parse
def mappings_add(mode:Union[str,list], lhs: str, rhs: str) -> None:
    # nnoremap FileType go gd :LspSymbolDefinition<CR>
    modes = [mode] if isinstance(mode, str) else mode
    modes_enum = M(0)
    for m in modes:
        modes_enum |= mode_names_rev[m]
    key = _normalise_lhs(lhs)
    _log.map(" @map+ %s lhs¦key=%s ¦ %s rhs=%s"
        ,    modes_enum,lhs,key,        rhs)
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
                cmd_txt_d = dict(main=None,plugin=None)
                if isinstance(mode, str):
                    mode_enum     = mode_names_rev[mode]
                    cmd_txt_d     = key2textcmd(cmd_s, mode_enum)
                else:
                    for mode in modes: # find the first matching default key
                        mode_enum = mode_names_rev[mode]
                        cmd_txt_d = key2textcmd(cmd_s, mode_enum)
                        if cmd_txt_d['main'  ] or \
                           cmd_txt_d['plugin']:
                            break

                def_cmd = None # find the first command that matches FROM key
                for    mode in M_ANY: # TODO: m_enum iteration fails in py3.8
                    if mode & modes_enum:
                        textcmd_d = key2textcmd(key, mode)
                        if (_cmd_txt := textcmd_d['main'  ]): # ‘b’ → <...ViMoveByWordsBackward>
                            def_cmd = _cmd_txt
                            break
                        if (_cmd_txt := textcmd_d['plugin']): # ‘gh’ → <...MultipleCursorsStart>
                            def_cmd = _cmd_txt
                            break

                if _cmd_txt := (cmd_txt_d.get('main'  ) or\
                                cmd_txt_d.get('plugin')): # found a match
                    cmd_txt = _cmd_txt # MoveByWordsBackward
                    props['defk'] = cmd_s # save ‘b’ default vim key to props ‘defk’
                if def_cmd:
                    props['defc'] = def_cmd # save ‘MultipleCursorsSkip’ default command for ‘l’ key to props ‘defc’
                if '"' in cmd_txt: # create a raw string to avoid escaping quotes
                    arg = kdl2.RawString(tag=None,value=cmd_txt)
                else:
                    arg = kdl2.   String(tag=None,value=cmd_txt)
                props['file'] = file_types
                node_key = kdl2.Node(tag=mode_s, name=key, args=[arg], props=props)
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
        cmd_txt_d = dict(main=None,plugin=None)
        if isinstance(mode, str):
            mode_enum     = mode_names_rev[mode]
            cmd_txt_d     = key2textcmd(cmd_s, mode_enum)
        else:
            for mode in modes: # find the first matching default key
                mode_enum = mode_names_rev[mode]
                cmd_txt_d = key2textcmd(cmd_s, mode_enum)
                if cmd_txt_d['main'  ] or \
                   cmd_txt_d['plugin']:
                    break

        def_cmd = None # find the first command that matches FROM key
        for    mode in M_ANY: # TODO: m_enum iteration fails in py3.8
            if mode & modes_enum:
                textcmd_d = key2textcmd(key, mode)
                if (_cmd_txt := textcmd_d['main'  ]): # ‘b’ → <...ViMoveByWordsBackward>
                    def_cmd = _cmd_txt
                    break
                if (_cmd_txt := textcmd_d['plugin']): # ‘gh’ → <...MultipleCursorsStart>
                    def_cmd = _cmd_txt
                    break

        if _cmd_txt := (cmd_txt_d.get('main'  ) or\
                        cmd_txt_d.get('plugin')): # found a match
            cmd_txt = _cmd_txt # MoveByWordsBackward
            props['defk'] = cmd_s # save ‘b’ default vim key to props ‘defk’
        if def_cmd:
            props['defc'] = def_cmd # save ‘MultipleCursorsSkip’ default command for ‘l’ key to props ‘defc’
        if '"' in cmd_txt: # create a raw string to avoid escaping quotes
            arg = kdl2.RawString(tag=None,value=cmd_txt)
        else:
            arg = kdl2.   String(tag=None,value=cmd_txt)
        node_key = kdl2.Node(tag=mode_s, name=key, args=[arg], props=props)
        NeoVintageous.nv.cfg_parse._NVRC_KDL.nodes.append(node_key)

    for mode in modes:
        _mappings[mode][key] = rhs

def mappings_add_text(mode:str, key:str, cmd:Union[str,list], prop:dict={}) -> None:
    #           mode_normal     W        MoveByBigWords       {file:['txt','rs']}
    key_norm = _normalise_lhs(key)
    old_cmd_ftype = _mappings_text[mode].get(key_norm)
    _log.mapp(" map+txt ¦%s¦ ‹¦%s ≈ %s¦⟶¦%s¦› @file¦%s¦ oldcmd¦%s¦"
      ,                mode, key,key_norm,cmd,prop.get('file',''),old_cmd_ftype)
    if (file_types := prop.get('file')):
        if not old_cmd_ftype:
            _mappings_text[mode][key_norm]            = {}
        elif (isinstance(old_cmd_ftype,str ) or\
              isinstance(old_cmd_ftype,list)):
            _mappings_text[mode][key_norm]            = {'':old_cmd_ftype}
        for file_type in file_types:
            _mappings_text    [mode][key_norm][file_type] = cmd
        return
    if       (isinstance(old_cmd_ftype,dict)): # don't overwrite existing filetype commands
        _mappings_text        [mode][key_norm][''       ] = cmd
    else:                                          # ok to overwrite old commands
        _mappings_text        [mode][key_norm]            = cmd

    if prop: # store User data (icons, descriptions, type) to our classes for later use in Status and Help
        cmd_txt = ''
        if isinstance(cmd,list) and len(cmd) == 1 and isinstance(cmd0 := cmd[0],str): # cmd can be None if null in kdl
            cmd_txt = cmd0.lower()
        if isinstance(cmd,str):
            cmd_txt = cmd .lower()
        if not cmd_txt:
            return
        cmd_cls = _text_to_command(view=None,text=cmd_txt)
        if not isinstance(cmd_cls,CommandNotFound):
            if _p := prop.get('desc',None):
                cmd_cls.desc = _p
            if _p := prop.get('icon',None):
                cmd_cls.icon = _p
            if _p := prop.get('type',None):
                cmd_cls.type = _p

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
    mode = get_mode                (view)
    cmd  = ''.join(get_partial_text(view)) + key
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


def _text_to_command(view, text:str):
    """ Convert textual command (MoveByLineCols) into command function (ViMoveByLineCols)
        ←  view	View	.
         text  	str 	Text command, eg, 'MoveByLineCols'
        → ViCommandDefBase | CommandNotFound
    """
    cmd_plugin  = plugin.map_textcmd2cmd.get(text)
    cmd_keys    =   keys.map_textcmd2cmd.get(text)
    _log.map(" cmd_text ‘%s’ → cmd_plugin ‘%s’ cmd_keys = ‘%s’"
        ,               text,       cmd_plugin,         cmd_keys)
    if cmd_plugin\
        and (not view or (view and is_plugin_enabled(view, cmd_plugin))):
        return cmd_plugin
    if cmd_keys:
        return cmd_keys
    return CommandNotFound()


def _seq_to_command(view, seq: str, mode: str):
    """Return the command definition mapped for seq and mode
    view  View:
    seq   str : Command sequence
    mode  str : Forces the use of this mode instead of the global state's.
    → ViCommandDefBase | CommandNotFound
    """
    if mode in plugin.mappings:
        if (plugin_command := plugin.mappings[mode].get(seq)):
            if is_plugin_enabled(view, plugin_command):
                _log.map("  ‘%s’cmd_plug ←‘%s’seq",plugin_command,seq)
                return plugin_command
    if mode in keys.mappings:
        command = keys.mappings[mode].get(seq)
        if command:
            _log.map("  ‘%s’cmd_keys ←‘%s’seq",command,seq)
            return command
    return CommandNotFound()


def mappings_resolve(view, sequence: str = None, mode: str = None, check_user_mappings: bool = True):
    """Look at the current global state and return the command mapped to the available sequence.
    sequence           	str 	Command sequence. If passed, use instead of the global state's. This is necessary for some commands that aren't name spaces but act as them (for example, ys from the surround plugin).
    mode               	str 	If passed, use instead of the global state's. This is necessary when we are in operator pending mode and we receive a new action. By combining the existing action's name with name of the action just received we could find a new action.
    check_user_mappings	bool	.
    → Mapping | IncompleteMapping | CommandNotFound
    """
    cmd,cmdU,cmdS = '','',''
    seqIn = sequence if sequence else ''
    cmdSpart = get_partial_sequence(view) # We usually need to look at the partial sequence, but some commands do weird things, like ys, which isn't a namespace but behaves as such.
    seq = seqIn or cmdSpart
    if check_user_mappings: # Resolve the full sequence rather than the "bare" sequence, because the user may have defined some mappings that start with numbers (counts), or " (register character), which are stripped from the bare sequences. See https://github.com/NeoVintageous/NeoVintageous/issues/434.
        # XXX The reason these does not pass the mode, and instead uses the get_mode(), is because implementation of commands like dd are a bit hacky. For example, the dd definition does is not assigned to operator pending mode, the second d is instead caught by the feed key command and resolved by specifying NORMAL mode explicitly, which resolves the delete line command definition. Commands like this can probably be fixed by allowing the definitions to handle the OPERATOR PENDING and let the definition handle any special-cases itself instead of passing off the responsibility to the feed key command.
        cmdU = _seq_to_mapping(view, seq)
        if     not cmdU :
            if not seqIn:
                if _has_partial_matches(view, get_mode(view), seq):
                    _log.debug("→IncompleteMapping no cmdU/seqIn, but partial match")
                    return IncompleteMapping()
    cmd = cmdU if cmdU else (cmdS:=_seq_to_command(view, to_bare_command_name(seq), mode or get_mode(view)))
    _log.map(' @mapResS ‹‘%s’=‘%s’› (%s usr%s cmd: ‘%s’in ‘%s’usr ‘%s’S¦‘%s’Spart ‘%s’cmd ‘%s’cmd_cls)'
        ,cmd.lhs if hasattr(cmd,'lhs') else ''
        ,cmd.rhs if hasattr(cmd,'rhs') else ''
        ,mode if mode else 'm0','1' if check_user_mappings else '0'
        ,seqIn,'✓map' if cmdU else '✗map',cmdS,cmdSpart, cmd, cmd.__class__.__mro__)
    return cmd

def mappings_resolve_text(view, text_command:str = None, mode: str = None, check_user_mappings: bool = True):
    """Check current global state and return the command mapped to the available text_command
    text_command       	str 	Text command sequence. If passed, use instead of the global state's (some commands aren't name spaces but act as them like ‘ys’ from plugin surround)
    mode               	str 	if passed, use instead of the global state's
    check_user_mappings	bool	.
    → Mapping |  CommandNotFound
    """
    cmd,cmdU,cmdT = '','',''
    cmdIn = text_command if text_command else ''
    cmdTpart = get_partial_text(view) # We usually need to look at the partial sequence, but some commands do weird things, like ys, which isn't a namespace but behaves as such
    cmdTxt = cmdIn or ''.join(cmdTpart)
    _log.map("  TXT ¦%s¦in ¦%s¦part",cmdIn,cmdTpart)
    if check_user_mappings:
        cmdU = _text_cmd_to_mapping(view, cmdTxt)
        if     not cmdU:
            if not cmdIn:
                if _has_partial_matches_text(view, get_mode(view), cmdTxt):
                    _log.debug("→IncompleteMapping no cmdU/cmdTxt, but partial match for ‘%s’cmdTxt",cmdTxt)
                    return IncompleteMapping()
    cmd = cmdU if cmdU else (cmdT:=_text_to_command(view, cmdTxt))
    _log.map(' @mapResT %s ‹‘%s’=‘%s’› (%s usr%s cmd: ‘%s’in ‘%s’usr ‘%s’T¦‘%s’Tpart ‘%s’cmd ‘%s’cmd_cls)'
        ,cmd.__class__.__name__
        ,cmd.lhs if hasattr(cmd,'lhs') else ''
        ,cmd.rhs if hasattr(cmd,'rhs') else ''
        ,mode if mode else 'm0','1' if check_user_mappings else '0'
        ,cmdIn,'✓map' if cmdU else '✗map',cmdT,cmdTpart, cmd, cmd.__class__.__mro__)
    return cmd
