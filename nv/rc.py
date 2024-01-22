# Copyright (C) 2018-2023 The NeoVintageous Team (NeoVintageous).
#
# This file is part of NeoVintageous.
#
# NeoVintageous is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# NeoVintageous is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NeoVintageous.  If not, see <https://www.gnu.org/licenses/>.

import builtins
import logging
import os
import re
from pathlib import Path
from typing import List, Union

import sublime

import NeoVintageous.dep.kdl as kdl
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
            f.write('#v 0.1 // config format version to hopefully allow updates without breaking existing configs (‘#’ is optional)\n')
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
    if source and isinstance(source, str):
        try:
            _source(window, iter(sublime.load_resource(source).splitlines()))
            _log.info('sourced %s', source)
        except FileNotFoundError as e:
            print('NeoVintageous:', e)

    try:
        with builtins.open(_file_path(), 'r', encoding='utf-8', errors='replace') as f:
            _source(window, f)
            _log.info('sourced %s', _file_path())
    except FileNotFoundError:
        _log.info('%s file not found', _file_path())
    # load_cfgU()
    cfgU.load_kdl()


import NeoVintageous.nv.cfg_parse
def _source(window, source) -> None:
    # The import is inline to avoid circular dependency errors.
    from NeoVintageous.nv.ex_cmds import do_ex_cmdline

    try:
        window.settings().set('_nv_sourcing', True)
        for line in source:
            ex_cmdline = _parse_line(line)
            if ex_cmdline:
                do_ex_cmdline(window, ex_cmdline)
            elif NeoVintageous.nv.cfg_parse._dump_to_kdl:
                node_key = kdl.Node(tag=None, name='-', args=[kdl.RawString(line.rstrip())])
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
from NeoVintageous.nv.modes import Mode as M, text_to_modes, mode_names, MODE_NAMES_OLD, M_EVENT, M_ANY, M_CMDTXT

from NeoVintageous.nv.cfg_parse import clean_name, clean_cmd
re_count = re.compile(r"[№#⌗cn](\d+)")
re_filetype = re.compile(r"[\s,]+")
_keybind_prop = {
    'desc':['d','des','desc','description','inf','info'],
    'icon':['i','icn','icon','img','image'],
    'file':['ft','file','filetype'],
    'def':['def','default'],
    }
def _parse_keybind_kdl(keybind:kdl.Node):
    from NeoVintageous.nv.mappings import mappings_add, mappings_add_text
    if not (cfgT := type(keybind)) is kdl.Node:
        _log.error("Type of ‘keybind’ should be kdl.Node, not ‘%s’",cfgT)
        return None
    for node in keybind.nodes: # (Ⓝ)"q" "OpenNameSpace"
        mode_s = node.tag             # ‘Ⓝ’
        modes  = text_to_modes(mode_s) # ‘Mode.Normal’ enum for ‘Ⓝ’ (‘Mode.Any’ for None tag)
        key    = node.name             # ‘q’
        cmd_txt = []                   # ‘[OpenNameSpace]’
        if key == '-': # skip comment nodes (todo: when lib supports roundtrip, save as actual comments)
            continue
        for arg in node.args:          # Parse arguments
            tag = clean_name(arg.tag   if hasattr(arg,'tag'  ) else '' )
            cmd =            arg.value if hasattr(arg,'value') else arg
            count = 1
            if count_l := re_count.findall(tag):
                count = int(count_l[0])
            for i in range(1,1+(count if count > 1 else 1)):
                cmd_txt.append(cmd)

        prop = dict()                  # Parse properties
        for pkey,tag_val in node.props.items(): # ‘i="✗" d="Close a tab"’
            tag = arg.tag   if hasattr(tag_val,'tag'  ) else ''
            val = arg.value if hasattr(tag_val,'value') else tag_val
            for dkey,key_abbrev in _keybind_prop.items():
                if dkey == 'file':
                    if pkey in key_abbrev: # ['ft','file','filetype']
                        prop[dkey] = []
                        prop[dkey].extend(re_filetype.split(val))
                else:
                    if pkey in key_abbrev:
                        prop[dkey] = val

        if not modes:
            _log.error("Couldn't parse ‘%s’ to a list of modes, skipping ‘%s’"
                ,                     mode_s,                            node)
            continue
        if not key:
            _log.error("Missing keyboard shortcut, skipping ‘%s’",node)
            continue
        if not cmd_txt:
            _log.error("Missing text command(s), skipping ‘%s’",node)
            continue
        if (m_inv := modes & ~M.CmdTxt): # if there are more modes than allowed
            # s = 's' if len(m_inv) > 1 else '' # TODO len fails in py3.8
            mode_sym = ''
            for mode in M_ANY: # TODO: m_inv iteration fails in py3.8
                if mode & m_inv: # todo: store original re matches in text_to_mode to allow roundtrip of modes matching user input
                    mode_sym += mode_names[mode][0]
            s = 's' if len(mode_sym) > 1 else ''
            _log.warn("Invalid mode%s ‘%s’ in ‘%s’ in node ‘%s’"
                ,                  s,mode_sym,mode_s,     node)

        for mode in M_CMDTXT: # iterate over all of the allowed modes
            if mode & modes: # if it's part of the keybind's modes, register the key
                cfgU.text_commands[mode][key] = cmd_txt
                mappings_add_text(mode=MODE_NAMES_OLD[mode], key=key, cmd=cmd_txt, prop=prop)


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
        parse_kdl_config(cfg, cfg_f, kdl_docs)
        return kdl_docs

    @staticmethod
    def load_kdl():
        if hasattr(cfgU,'kdl') and cfgU.kdl: # avoid loading the same config multiple times
            return
        cfg_l:List[kdl.Document] = cfgU.read_kdl_file()
        cfgU.kdl = dict()

        # Split config into per-section/per-plugin group
        cfg_group  = ['keymap','event','status','edit','keybind']
        cfg_nest   = {'plugin'   :['surround']
            ,         'indicator':['ls','registers']}
        # Set config dictionaries to emtpy
        for g in cfg_group:
            cfgU.kdl          [g] = None
        for nest in cfg_nest:
            cfgU.kdl    [nest]    = dict()
            for g in nest:
                cfgU.kdl[nest][g] = None
        # Fill config dictionaries
        for cfg in cfg_l: # store the latest existing value in any of the docs
            for g in cfg_group:   # direct config groups like 'keymap'
                if (node := cfg.get(g, None)):
                    cfgU.kdl  [g] = node
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
        #for g in cfg_group: # Rudimentary type checks (can have props, also empty is ok)
        #    if  cfgU.kdl[g] and not (cfgU.kdl[g].nodes):
        #        cfgU.kdl[g] = None; _log.warn(f"‘{g}’ in ‘{cfgU.cfg_f}’ has no child nodes!")

        ignore = {1:cfg_group, 2:[]} # ignore the lowest level dictionary groups as they repeat node names
        for g,subg in cfg_nest.items():
            ignore[2] += subg
        cfgU.flat = flatten_kdl(cfgU.kdl, ignore=ignore) # store a flat dictionary for easy access
        # print('cfgU.flat', cfgU.flat)

        if (keybind := cfgU.kdl['keybind']):
            _parse_keybind_kdl(keybind)

        _import_plugins_with_user_data_kdl()

    @staticmethod
    def unload_kdl():
        if cfgU.kdl: # reset config
            cfgU.kdl = dict()
            _log.debug('@cfgU.unload_kdl: erased current cfgU.kdl')
        if cfgU.flat: # reset flat config
            cfgU.flat = dict()
            _log.debug('@cfgU.unload_kdl: erased current cfgU.flat')
        if cfgU.text_commands: # reset text_commands config
            text_commands = dict()
            for _m in M_CMDTXT:
                text_commands[_m] = dict()
            cfgU.text_commands = text_commands
            _log.debug('@cfgU.unload_kdl: erased current cfgU.text_commands')
        _import_plugins_with_user_data_kdl() # reset plugin defaults

def _import_plugins_with_user_data_kdl():
    from NeoVintageous.nv import plugin_surround
    plugin_surround.reload_with_user_data_kdl()
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

from NeoVintageous.nv.cfg_parse import parse_kdl_config
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
