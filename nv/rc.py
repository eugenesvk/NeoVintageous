import builtins
import logging
import os
import re
import json
from pathlib import Path
from typing import List, Union

import sublime

import NeoVintageous.dep.kdl as kdl
import NeoVintageous.dep.kdl2 as kdl2
from NeoVintageous.nv.polyfill import nv_message as message
from NeoVintageous.nv.helper import flatten_dict, flatten_kdl, Singleton


from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL
_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)


def _file_name() -> str:
    return '.neovintageousrc'
def _file_name_config_kdl() -> str:
    return f"{PACKAGE_NAME}.kdl"


def _file_path() -> str:
    return os.path.join(sublime.packages_path(), 'User', _file_name())
def _file_path_config_kdl() -> str:
    return os.path.join(sublime.packages_path(), 'User', _file_name_config_kdl())


def open_rc(window) -> None:
    file = _file_path()

    if not os.path.exists(file):
        with builtins.open(file, 'w', encoding='utf-8') as f:
            f.write('" A double quote character starts a comment.\n')

    window.open_file(file)
def open_config_file_kdl(window) -> None:
    file = _file_path_config_kdl()
    if not os.path.exists(file):
        with builtins.open(file, 'w', encoding='utf-8') as f:
            f.write('/* See ‘NeoVintageous.help.kdl’ for an example\n')
            f.write('  (run ‘NeoVintageous: Open new config file example (KDL)’ in Command Palette to open it)\n')
            f.write('  (run ‘Preferences: NeoVintageous New Settings (KDL)’ in Command Palette to open it along with your config)\n')
            f.write('*/\n')
            f.write('v 0.1 // config format version to hopefully allow updates without breaking existing configs (‘#’ is optional)\n')
    window.open_file(file)


def load_rc() -> None:
    _log.debug('sourcing %s', _file_path())
    _load()


def reload_rc() -> None:
    _log.debug('reloading %s', _file_path())
    _unload()
    _load()


def _unload() -> None:
    # Imports are inline to avoid circular dependency errors.
    from NeoVintageous.nv.mappings import clear_mappings
    from NeoVintageous.nv.options import clear_options
    from NeoVintageous.nv.variables import clear_variables

    clear_variables()
    clear_mappings()
    clear_options()
    _unload_cfgU()


def _pre_load(window,source) -> None:
    if source and isinstance(source, str):
        try:
            _source(window, iter(sublime.load_resource(source).splitlines()))
            _log.info('sourced %s', source)
        except FileNotFoundError as e:
            print('NeoVintageous:', e)

def _load() -> None:
    window = sublime.active_window()

    settings = sublime.load_settings('Preferences.sublime-settings')
    source = settings.get('vintageous_source')
    _pre_load(window,source)

    try:
        with builtins.open(_file_path(), 'r', encoding='utf-8', errors='replace') as f:
            _source(window, f)
            _log.info('sourced %s', _file_path())
    except FileNotFoundError:
        _log.info('%s file not found', _file_path())
    # load_cfgU()
    cfgU.load_kdl()


import NeoVintageous.nv.cfg_parse
def _source(window, source, nodump=False) -> None:
    from NeoVintageous.nv.ex_cmds import do_ex_cmdline # inline import to avoid circular dependency errors

    try:
        window.settings().set('_nv_sourcing', True)
        for line in source:
            ex_cmdline = _parse_line(line)
            if ex_cmdline:
                do_ex_cmdline(window, ex_cmdline)
            elif NeoVintageous.nv.cfg_parse._dump_to_kdl and not nodump:
                node_key = kdl2.Node(tag=None, name='≠', args=[kdl2.RawString(line.rstrip())])
                NeoVintageous.nv.cfg_parse._NVRC_KDL.nodes.append(node_key)
    finally:
        window.settings().erase('_nv_sourcing')


# Recursive mappings (:map, :nmap, :omap, :smap, :vmap) are not supported. They
# were removed in version 1.5.0. They were removed because they were they were
# implemented as non-recursive mappings.
_PARSE_LINE_PATTERN = re.compile(
    '^\\s*(?::)?(?P<cmdline>(?P<cmd>(?:[nsviox])?noremap|let|set|(?:[nsviox])?unmap) .*)$')


def _parse_line(line: str):
    try:
        line = line.rstrip()
        if line:
            match = _PARSE_LINE_PATTERN.match(line)
            if match:
                cmdline = match.group('cmdline')
                # Ensure there is leading colon, because the parser pattern omits it.
                if cmdline:
                    cmdline = ':' + cmdline

                # The '|' character is used to chain commands. Users should
                # escape it with a slash or use '<bar>'. See :h map-bar. It's
                # translated to <bar> internally (implementation detail).
                # See https://github.com/NeoVintageous/NeoVintageous/issues/615.
                cmdline = cmdline.replace('\\|', '<bar>')
                cmdline = cmdline.replace('\t', ' ') # avoid bugs with tab literal

                if '|' in cmdline:
                    # Using '|' to separate map commands is currently not supported.
                    raise Exception('E488: Trailing characters: {}'.format(line.rstrip()))

                return cmdline
    except Exception as e:
        message('error detected while processing {} at line "{}":\n{}'.format(_file_name(), line.rstrip(), str(e)))

    return None


from NeoVintageous.plugin import PACKAGE_NAME
from NeoVintageous.nv.modes import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE
from NeoVintageous.nv.modes import Mode, Mode as M, text_to_modes, mode_names, MODE_NAMES_OLD, M_EVENT, M_ANY, M_CMDTXT

from NeoVintageous.nv.cfg import _keybind_prop, re_count, re_subl_tag, re_filetype
from NeoVintageous.nv.cfg_parse import clean_name, clean_cmd

from NeoVintageous.nv.cfg_parse1 import _parse_general_cfg_kdl1, _parse_keybinds_kdl1
from NeoVintageous.nv.cfg_parse2 import _parse_general_cfg_kdl2, _parse_keybinds_kdl2
def _parse_rc_g_kdl1(rc_g:kdl.Node):
    win = sublime.active_window()
    for node in rc_g.nodes: # r#":set invrelativenumber"#
        _parse_rc_cfg_kdl1(win,rc_cfg=node)
def _parse_rc_cfg_kdl1(win,rc_cfg:kdl.Node) -> None:
    if not (cfgT := type(rc_cfg)) is kdl.Node:
        _log.error("Type of ‘rc’ config group should be kdl.Node, not ‘%s’",cfgT)
        return None
    node = rc_cfg               # r#":set invrelativenumber"#
    if node.args or\
       node.props:
        _log.warn("‘rc’ config nodes must have no arguments/properties ‘%s’",node)
        return None
    opt_name = node.name     # r#":set invrelativenumber"#
    if opt_name:
        # print(f"‘rc’ config: node with no args/props, running as an Ex command ‘{node}’")
        _source(win, [opt_name], nodump=True)
        return None
def _parse_rc_g_kdl2(rc_g:kdl2.Node):
    win = sublime.active_window()
    for node in rc_g.nodes: # r#":set invrelativenumber"#
        _parse_rc_cfg_kdl2(win,rc_cfg=node)
def _parse_rc_cfg_kdl2(win,rc_cfg:kdl2.Node) -> None:
    if not (cfgT := type(rc_cfg)) is kdl2.Node:
        _log.error("Type of ‘rc’ config group should be kdl2.Node, not ‘%s’",cfgT)
        return None
    node = rc_cfg               # r#":set invrelativenumber"#
    if not len(node.entries) == 0:
        _log.warn("‘rc’ config nodes must have no arguments/properties ‘%s’",node)
        return None
    opt_name = node.name     # r#":set invrelativenumber"#
    if opt_name:
        # print(f"‘rc’ config: node with no args/props, running as an Ex command ‘{node}’")
        _source(win, [opt_name], nodump=True)
        return None

def _parse_general_g_kdl1(general_g:kdl.Node,CFG:dict,DEF:dict):
    win = sublime.active_window()
    st_pref = sublime.load_settings('Preferences.sublime-settings')
    if (src_pre := general_g.get((None,"source"))):
        if (args := src_pre.args):
            tag_val = args[0] #(t)"/dvorak.neovintageous" if (t) exists (though shouldn't)
            # val = tag_val.value if hasattr(tag_val,'value') else tag_val # ignore tag
            if hasattr(tag_val,'value'):
                val = tag_val.value # ignore tag
                _log.warn("node ‘%s’ has unrecognized tag in argument ‘%s’"
                    ,      src_pre.name,                               tag_val)
            else:
                val = tag_val
            # print(f"loading source first ‘{val}’")
            _pre_load(win,val)
    for node in general_g.nodes: # set relativenumber=true
        _parse_general_cfg_kdl1(general_cfg=node,CFG=CFG,DEF=DEF,st_pref=st_pref)
def _parse_general_g_kdl2(general_g:kdl2.Node,CFG:dict,DEF:dict):
    win = sublime.active_window()
    st_pref = sublime.load_settings('Preferences.sublime-settings')
    if (src_pre := general_g.get((None,"source"))):
        for arg in src_pre.getArgs((...,...)): # only get the first one
            tag_val = arg #(t)"/dvorak.neovintageous" if (t) exists (though shouldn't)
            # val = tag_val.value if hasattr(tag_val,'value') else tag_val # ignore tag
            if hasattr(tag_val,'value'):
                val = tag_val.value # ignore tag
                _log.warn("node ‘%s’ has unrecognized tag in argument ‘%s’"
                    ,      src_pre.name,                               tag_val)
            else:
                val = tag_val
            # print(f"loading source first ‘{val}’")
            _pre_load(win,val)
            break
    for node in general_g.nodes: # set relativenumber=true
        _parse_general_cfg_kdl2(general_cfg=node,CFG=CFG,DEF=DEF,st_pref=st_pref)

DEF = dict()
DEF['res_tag'] = list() # internal command description tags, exclude these when parsing a sublime command so that it doesn't get arguments it can't understand
for dkey,key_abbrev in _keybind_prop.items(): # 'type':['t','type']
    for val in key_abbrev:                    #          t   type
        DEF['res_tag'].append(val)
DEF['var_def'] = ['‘','’']
DEF['general'] = {}
DEF['gen_def'] = { # todo: replace float with int when kdl-py issue is fixed
    # clean name                    	: dict(type   default value	 old/internal key name
    'defaultmode'                   	: dict(t=str ,v="normal"   	,key='default_mode'),
    'resetmodewhenswitchingtabs'    	: dict(t=bool,v=False      	,key='reset_mode_when_switching_tabs'),
    'highlightedyank'               	: dict(t=bool,v=True       	,key='highlighted_yank'),
    'highlightedyankduration'       	: dict(t=float,v=1000      	,key='highlighted_yank_duration'),
    'highlightedyankstyle'          	: dict(t=str ,v="fill"     	,key='highlighted_yank_style'),
    'searchcurstyle'                	: dict(t=str ,v="fill"     	,key='search_cur_style'),
    'searchincstyle'                	: dict(t=str ,v="fill"     	,key='search_inc_style'),
    'searchoccstyle'                	: dict(t=str ,v="fill"     	,key='search_occ_style'),
    'bell'                          	: dict(t=str ,v="blink"    	,key='bell'),
    'bellcolorscheme'               	: dict(t=str ,v="dark"     	,key='bell_color_scheme'),
    'autonohlsearchonnormalenter'   	: dict(t=bool,v=True       	,key='auto_nohlsearch_on_normal_enter'),
    'enableabolish'                 	: dict(t=bool,v=True       	,key='enable_abolish'),
    'enablecommentary'              	: dict(t=bool,v=True       	,key='enable_commentary'),
    'enablemultiplecursors'         	: dict(t=bool,v=True       	,key='enable_multiple_cursors'),
    'enablesneak'                   	: dict(t=bool,v=True       	,key='enable_sneak'),
    'enablesublime'                 	: dict(t=bool,v=True       	,key='enable_sublime'),
    'enablesurround'                	: dict(t=bool,v=True       	,key='enable_surround'),
    'enabletargets'                 	: dict(t=bool,v=True       	,key='enable_targets'),
    'enableunimpaired'              	: dict(t=bool,v=True       	,key='enable_unimpaired'),
    'usectrlkeys'                   	: dict(t=bool,v=True       	,key='use_ctrl_keys'),
    'usesuperkeys'                  	: dict(t=bool,v=True       	,key='use_super_keys'),
    'handlekeys'                    	: dict(t=dict,v={}         	,key='handle_keys'),
    'iescapejj'                     	: dict(t=bool,v=True       	,key='i_escape_jj'),
    'iescapejk'                     	: dict(t=bool,v=True       	,key='i_escape_jk'),
    'nvⓘ⎋←ii'                       	: dict(t=bool,v=True       	,key='nvⓘ_⎋←ii'),
    'nvⓘ⎋←;i'                       	: dict(t=bool,v=True       	,key='nvⓘ_⎋←;i'),
    'usesysclipboard'               	: dict(t=bool,v=True       	,key='use_sys_clipboard'),
    'clearautoindentonesc'          	: dict(t=bool,v=True       	,key='clear_auto_indent_on_esc'),
    'autocompleteexitfrominsertmode'	: dict(t=bool,v=True       	,key='auto_complete_exit_from_insert_mode'),
    'multicursorexitfromvisualmode' 	: dict(t=bool,v=False      	,key='multi_cursor_exit_from_visual_mode'),
    'lspsave'                       	: dict(t=bool,v=False      	,key='lsp_save'),
    'shellsilent'                   	: dict(t=bool,v=False      	,key='shell_silent'),
    'showmarksingutter'             	: dict(t=bool,v=True       	,key='show_marks_in_gutter'),
    'sneakuseicscs'                 	: dict(t=float,v=1         	,key='sneak_use_ic_scs'),
    'exitwhenquittinglastwindow'    	: dict(t=[bool,str],v=True 	,key='exit_when_quitting_last_window'),
    'source'                        	: dict(t=str ,v=''         	,key='source'),
    'autoswitchinputmethod'         	: dict(t=bool,v=False      	,key='auto_switch_input_method'),
    'autoswitchinputmethoddefault'  	: dict(t=str ,v=''         	,key='auto_switch_input_method_default'),
    'autoswitchinputmethodgetcmd'   	: dict(t=str ,v=''         	,key='auto_switch_input_method_get_cmd'),
    'autoswitchinputmethodsetcmd'   	: dict(t=str ,v=''         	,key='auto_switch_input_method_set_cmd'),
}
import copy
CFG = copy.deepcopy(DEF) # copy defaults to be able to reset values on config reload

# cfgU_settings = (f'{PACKAGE_NAME}.sublime-settings')
class cfgU(metaclass=Singleton):
    cfg_p = _file_path_config_kdl()
    cfg_f = Path(cfg_p).expanduser()

    text_commands = dict()
    for _m in M_CMDTXT:
        text_commands[_m] = dict()

    @staticmethod
    def read_kdl_file() -> List[kdl.Document]:
        cfg_p = cfgU.cfg_p
        cfg_f = cfgU.cfg_f
        kdl_docs = [] # list of KDL docs in the order of parsing, includes imports as separate items
        if cfg_f.exists():
            try:
                with open(cfg_f, 'r', encoding='utf-8', errors='replace') as f:
                    cfg = f.read()
            except FileNotFoundError as e:
                sublime.error_message(f"{PACKAGE_NAME}:\nTried and failed to load\n{cfg_f}")
                return kdl_docs
        else:
            _log.info("Couldn't find ‘%s’",cfg_p) # config file is optional
            return kdl_docs

        parse_kdl_cfg_1st = parse_kdl2_config if NeoVintageous.nv.cfg.KDLV == 2 else parse_kdl_config
        parse_kdl_cfg_2nd = parse_kdl_config  if NeoVintageous.nv.cfg.KDLV == 2 else parse_kdl2_config
        v_1st =      NeoVintageous.nv.cfg.KDLV
        v_2nd = 1 if NeoVintageous.nv.cfg.KDLV == 2 else 2
        try:
            parse_kdl_cfg_1st(cfg, cfg_f, kdl_docs)
            return kdl_docs
        except Exception as e1st:
            # print(f"couldn't parse the docs as KDL{v_1st} due to: {e1st}")
            try:
                NeoVintageous.nv.cfg.KDLV = v_2nd
                parse_kdl_cfg_2nd(cfg, cfg_f, kdl_docs)
                return kdl_docs
            except Exception as e2nd:
                print(f"Couldn't parse {cfg_f} as KDL{v_1st} due to: {e1st}")
                print(f"  nor as KDL{v_2nd} due to: {e2nd}")
                return []

    @staticmethod
    def load_kdl():
        is2 = (NeoVintageous.nv.cfg.KDLV == 2)
        _parse_general_g_kdl = _parse_general_g_kdl2 if is2 else _parse_general_g_kdl1
        _parse_rc_g_kdl      = _parse_rc_g_kdl2      if is2 else _parse_rc_g_kdl1
        _parse_keybinds_kdl  = _parse_keybinds_kdl2  if is2 else _parse_keybinds_kdl1
        if hasattr(cfgU,'kdl') and cfgU.kdl: # avoid loading the same config multiple times
            return
        cfg_l:List[(kdl.Document,dict)] = cfgU.read_kdl_file()
        cfgU.kdl = dict()

        # Split config into per-section/per-plugin group
        cfg_group  = ['keymap','event','status','edit','keybind','general','rc','textobject','mark']
        cfg_nest   = {'plugin'   :['surround','abolish','unimpaired']
            ,         'indicator':['ls','registers','count','macro']}
        # Set config dictionaries to emtpy
        for g in cfg_group:
            cfgU.kdl          [g] = None
        cfgU.kdl      ['keybind'] = [] # allow concatenation of keybinds from various imports
        for nest in cfg_nest:
            cfgU.kdl    [nest]    = dict()
            for g in nest:
                cfgU.kdl[nest][g] = None
        # Fill config dictionaries
        for (cfg,var_d) in cfg_l: # store the latest existing value in any of the docs
            for g in cfg_group:   # direct config groups like 'keymap'
                if (node := cfg.get(g, None)):
                    if g == 'keybind':
                        cfgU.kdl[g] += [(node,var_d)]
                    else:
                        cfgU.kdl[g]  = node
            for nest in cfg_nest: # nested config groups like 'surround' within 'plugin'
                if (node_nest := cfg.get(nest, None)):       # 'plugin'   node
                    for g in cfg_nest[nest]:                 # 'surround'
                        if (node := node_nest.get(g, None)): # 'surround' child node
                            if g in cfgU.kdl[nest]: # dupe, but the other is less specific, overwrite
                                _log.error("node ‘%s’ already set as a direct node, overwriting"
                                    ,             g)
                            cfgU.kdl[nest][g] = node
                        if (node := cfg.get(g, None)):       # 'surround' direct node
                            if g in cfgU.kdl[nest]: # dupe, but     this  is less specific, ignore
                                _log.error("node ‘%s’ already set as a child of ‘%s’, skipping this dupe"
                                    ,             g,                            nest)
                            else:
                                cfgU.kdl[nest][g] = node

        ignore = {1:cfg_group, 2:[]} # ignore the lowest level dictionary groups as they repeat node names
        for g,subg in cfg_nest.items():
            ignore[2] += subg
        cfgU.flat = flatten_kdl(cfgU.kdl, ignore=ignore) # store a flat dictionary for easy access
        # print('cfgU.flat', cfgU.flat)

        if (general_g := cfgU.kdl['general']):
            _parse_general_g_kdl(general_g=general_g,CFG=CFG,DEF=DEF)

        if (rc_g := cfgU.kdl['rc']):
            _parse_rc_g_kdl(rc_g=rc_g)

        for (keybind,var_d) in cfgU.kdl['keybind']:
            _parse_keybinds_kdl(keybinds=keybind,CFG=CFG,cfgU=cfgU,var_d=var_d)

        _import_plugins_with_user_data_kdl()

    @staticmethod
    def unload_kdl():
        global CFG
        if hasattr(cfgU,'kdl'): # reset config
            cfgU.kdl = dict()
            _log.debug('@cfgU.unload_kdl: erased current cfgU.kdl')
        if hasattr(cfgU,'flat'): # reset flat config
            cfgU.flat = dict()
            _log.debug('@cfgU.unload_kdl: erased current cfgU.flat')
        if hasattr(cfgU,'text_commands'): # reset text_commands config
            text_commands = dict()
            for _m in M_CMDTXT:
                text_commands[_m] = dict()
            cfgU.text_commands = text_commands
            _log.debug('@cfgU.unload_kdl: erased current cfgU.text_commands')
        CFG = copy.deepcopy(DEF) # reset to defaults on reload
        _import_plugins_with_user_data_kdl() # reset plugin defaults

def _import_plugins_with_user_data_kdl():
    from NeoVintageous.nv.vi import text_objects
    text_objects.reload_with_user_data_kdl()
    from NeoVintageous.nv import plugin_surround
    plugin_surround.reload_with_user_data_kdl()
    from NeoVintageous.nv import plugin_abolish
    plugin_abolish.reload_with_user_data_kdl()
    from NeoVintageous.nv import plugin_unimpaired
    plugin_unimpaired.reload_with_user_data_kdl()
    from NeoVintageous.nv import vim
    vim.reload_with_user_data_kdl()
    # from NeoVintageous.nv import state # all needed config values are taken from nv.vim
    # state.reload_with_user_data_kdl()
    from NeoVintageous.nv import ex_cmds
    ex_cmds.reload_with_user_data_kdl()
    from NeoVintageous.nv import registers
    registers.reload_with_user_data_kdl()
    from NeoVintageous.nv import events_user
    events_user.reload_with_user_data_kdl()
    from NeoVintageous.nv import state
    state.reload_with_user_data_kdl()
    from NeoVintageous.nv import marks
    marks.reload_with_user_data_kdl()
    from NeoVintageous.nv import macros
    macros.reload_with_user_data_kdl()

from NeoVintageous.nv.cfg_parse import parse_kdl_config, parse_kdl2_config
# def load_cfgU() -> None:
#     """load alternative user config file to a global class and add a watcher event to track changes"""
#     global cfgU
#     global user_settings

#     try:
#         user_settings = sublime.load_settings(cfgU_settings)
#         cfgU.load();
#         user_settings.clear_on_change(PACKAGE_NAME)
#         user_settings.add_on_change  (PACKAGE_NAME, lambda: cfgU.load())
#     except FileNotFoundError:
#         _log.info(f'‘{cfgU_settings}’ file not found')

def _unload_cfgU() -> None: # clear old config, change watcher
    global cfgU
#     global user_settings
    cfgU.unload_kdl()
#     user_settings.clear_on_change(PACKAGE_NAME)
