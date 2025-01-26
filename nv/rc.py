import builtins
import logging
import os
import re
import json
from pathlib import Path
from typing import List, Union

import sublime

from NeoVintageous.nv.polyfill import nv_message as message
from NeoVintageous.nv.helper import Singleton
import NeoVintageous.nv.cfg_parse
from NeoVintageous.nv.cfg_parse import _pre_load, _source


from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL
_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)


def _file_path() -> str:
    return os.path.join(sublime.packages_path(), 'User', '.neovintageousrc')
def _file_path_config_kdl() -> str:
    return os.path.join(sublime.packages_path(), 'User', f"{PACKAGE_NAME}.kdl")


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


from NeoVintageous.plugin import PACKAGE_NAME
from NeoVintageous.nv.modes import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE
from NeoVintageous.nv.modes import Mode, Mode as M, text_to_modes, mode_names, MODE_NAMES_OLD, M_EVENT, M_ANY, M_CMDTXT

from NeoVintageous.nv.cfg import _keybind_prop, re_count, re_subl_tag, re_filetype
from NeoVintageous.nv.cfg_parse import clean_name, clean_cmd

from NeoVintageous.nv import cfg as nvcfg
# cfgU_settings = (f'{PACKAGE_NAME}.sublime-settings')
class cfgU(metaclass=Singleton):
    cfg_p = _file_path_config_kdl()
    cfg_f = Path(cfg_p).expanduser()

    text_commands = dict()
    for _m in M_CMDTXT:
        text_commands[_m] = dict()

    @staticmethod
    def read_kdl_file() -> List: #List[(kdl1|kdl2|ckdl.Document, dict)]
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

        st_pref = sublime.load_settings('Preferences.sublime-settings')

        cfg_pref = nvcfg.CFG['pref']
        def_kdlp = nvcfg.CFG['pref_def']['kdlp']
        if (kdlp := st_pref.get('nv_kdl_parser')):
            if   isinstance(kdlp,def_kdlp['t']):
                if kdlp in def_kdlp['lim']:
                    cfg_pref['kdlp'] =     kdlp
                else:
                    _log.error(f"‘nv_kdl_parser’ in ‘Preferences.sublime-settings’ should be either of {def_kdlv['lim']}, not {kdlp} (using default {def_kdlp['v']})")
            else:
                _log.error(    f"‘nv_kdl_parser’ in ‘Preferences.sublime-settings’ should be a string, not {type(kdlp)} (using default {def_kdlp['v']})")

        def_kdlv = nvcfg.CFG['pref_def']['kdlv']
        if (kdlv := st_pref.get('nv_kdl_v')):
            if   isinstance(kdlv,def_kdlv['t']):
                if kdlv in def_kdlv['lim']:
                    cfg_pref['kdlv'] =     kdlv
                else:
                    _log.error(f"‘nv_kdl_v’ in ‘Preferences.sublime-settings’ should be either of {def_kdlv['lim']}, not {kdlv} (using default {def_kdlv['v']})")
            elif isinstance(kdlv,str):
                if kdlv in ["1","2"]:
                    cfg_pref['kdlv'] = int(kdlv)
                else:
                    _log.error(f"‘nv_kdl_v’ in ‘Preferences.sublime-settings’ should be either of {def_kdlv['lim']}, not {kdlv} (using default {def_kdlv['v']})")
        v_1st =      nvcfg.CFG['pref']['kdlv']
        v_2nd = 1 if nvcfg.CFG['pref']['kdlv'] == 2 else 2
        if nvcfg.CFG['pref']['kdlp'] == 'ckdl' and _libckdl:
            from NeoVintageous.nv.cfg_parse_c import parse_kdl_config1, parse_kdl_config2
            parse_kdl_cfg_1st = parse_kdl_config2 if v_1st == 2 else parse_kdl_config1
            parse_kdl_cfg_2nd = parse_kdl_config1 if v_2nd == 1 else parse_kdl_config2
        else:
            from NeoVintageous.nv.cfg_parse1 import parse_kdl_config as parse_kdl1_config
            from NeoVintageous.nv.cfg_parse2 import parse_kdl_config as parse_kdl2_config
            parse_kdl_cfg_1st = parse_kdl2_config if v_1st == 2 else parse_kdl1_config
            parse_kdl_cfg_2nd = parse_kdl1_config if v_2nd == 1 else parse_kdl2_config
        try:
            parse_kdl_cfg_1st(cfg, cfg_f, kdl_docs)
            return kdl_docs
        except Exception as e1st:
            # print(f"couldn't parse the docs as KDL{v_1st} due to: {e1st}")
            try:
                nvcfg.CFG['pref']['kdlv'] = v_2nd
                parse_kdl_cfg_2nd(cfg, cfg_f, kdl_docs)
                return kdl_docs
            except Exception as e2nd:
                print(f"Couldn't parse {cfg_f} as KDL{v_1st} due to: {e1st}")
                print(f"  nor as KDL{v_2nd} due to: {e2nd}")
                return []

    @staticmethod
    def load_kdl():
        if hasattr(cfgU,'kdl') and cfgU.kdl: # avoid loading the same config multiple times
            return
        cfg_l = cfgU.read_kdl_file() #cfg_l:List[(kdl1|kdl2|ckdl.Document,dict)]
        cfgU.kdl = dict()
        if     nvcfg.CFG['pref']['kdlp'] == 'ckdl' and _libckdl:
            from     NeoVintageous.nv import cfg_parse_c as cfg_parse
        else:
            if nvcfg.CFG['pref']['kdlv'] == 2:
                from NeoVintageous.nv import cfg_parse2  as cfg_parse
            else:
                from NeoVintageous.nv import cfg_parse1  as cfg_parse
        cfgU.cfg_parse = cfg_parse

        # Split config into per-section/per-plugin group
        cfg_group  = ['keymap','event','status','edit','keybind','general','rc','textobject','mark']
        cfg_nest   = {'plugin'   :['surround','abolish','unimpaired']
            ,         'indicator':['ls','registers','count','keyhelp','macro']}
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
                if (node := cfg_parse.node_get(cfg, g, None)):
                    if g == 'keybind':
                        cfgU.kdl[g] += [(node,var_d)]
                    else:
                        cfgU.kdl[g]  = node
            for nest in cfg_nest: # nested config groups like 'surround' within 'plugin'
                if (node_nest := cfg_parse.node_get(cfg, nest, None)):       # 'plugin'   node
                    for g in cfg_nest[nest]:                 # 'surround'
                        if (node := cfg_parse.node_get(node_nest, g, None)): # 'surround' child node
                            if g in cfgU.kdl[nest]: # dupe, but the other is less specific, overwrite
                                _log.error("node ‘%s’ already set as a direct node, overwriting"
                                    ,             g)
                            cfgU.kdl[nest][g] = node
                        if (node := cfg_parse.node_get(cfg, g, None)):       # 'surround' direct node
                            if g in cfgU.kdl[nest]: # dupe, but     this  is less specific, ignore
                                _log.error("node ‘%s’ already set as a child of ‘%s’, skipping this dupe"
                                    ,             g,                            nest)
                            else:
                                cfgU.kdl[nest][g] = node

        ignore = {1:cfg_group, 2:[]} # ignore the lowest level dictionary groups as they repeat node names
        for g,subg in cfg_nest.items():
            ignore[2] += subg
        cfgU.flat = cfg_parse.flatten_kdl(cfgU.kdl, ignore=ignore) # store a flat dictionary for easy access
        # print('cfgU.flat', cfgU.flat)

        if (general_g := cfgU.kdl['general']):
            cfg_parse._parse_general_g_kdl(general_g=general_g,CFG=nvcfg.CFG,DEF=nvcfg.DEF)

        if (rc_g := cfgU.kdl['rc']):
            cfg_parse._parse_rc_g_kdl(rc_g=rc_g)

        for (keybind,var_d) in cfgU.kdl['keybind']:
            cfg_parse._parse_keybinds_kdl(keybinds=keybind,CFG=nvcfg.CFG,cfgU=cfgU,var_d=var_d)

        _import_plugins_with_user_data_kdl()

    @staticmethod
    def unload_kdl():
        if hasattr(cfgU,'kdl'): # reset config
            cfgU.kdl  = dict() ;_log.debug('@cfgU.unload_kdl: erased current cfgU.kdl')
        if hasattr(cfgU,'flat'): # reset flat config
            cfgU.flat = dict() ;_log.debug('@cfgU.unload_kdl: erased current cfgU.flat')
        if hasattr(cfgU,'text_commands'): # reset text_commands config
            text_commands = dict()
            for _m in M_CMDTXT:
                text_commands[_m] = dict()
            cfgU.text_commands = text_commands ;_log.debug('@cfgU.unload_kdl: erased current cfgU.text_commands')
        nvcfg.CFG = copy.deepcopy(nvcfg.DEF) # reset to defaults on reload
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
    from NeoVintageous.nv import ui
    ui.reload_with_user_data_kdl()

from NeoVintageous.nv.cfg_parse import _libckdl
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
