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

import sublime

from NeoVintageous.nv.polyfill import nv_message as message
from NeoVintageous.nv.helper import flatten_dict


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
        with builtins.open(file, 'w', encoding='utf-8') as f: # todo
            f.write('/* See ‘NeoVintageous.help.kdl’ for an example\n')
            f.write('  (run ‘NeoVintageous: Open new config file example (KDL)’ in Command Palette)\n')
            f.write('  See  ‘NeoVintageous.keymap-default.kdl’ for a list of default keybinds\n')
            f.write('  (run ‘NeoVintageous: Dump default keymap as KDL’ in Command Palette to generate it)\n')
            f.write('  To reload run ‘NeoVintageous: Reload config"’ in Command Palette\n')
            f.write('\n')
            f.write('  Install ‘KDL’ package for syntax highlighting\n')
            f.write('  // Comment /*block/inline comment*/  /-node comment to disable the whole section\n')
            f.write('  Node names are CaSe, ␠whitespace⭾, and se-pa-rat_or insensitive: keymap = key-map = key_map = "key map"\n')
            f.write('*/\n')
            f.write('\n')
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
    # _unload_cfgU()


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
    load_cfgU_kdl()


def _source(window, source) -> None:
    # The import is inline to avoid circular dependency errors.
    from NeoVintageous.nv.ex_cmds import do_ex_cmdline

    try:
        window.settings().set('_nv_sourcing', True)
        for line in source:
            ex_cmdline = _parse_line(line)
            if ex_cmdline:
                do_ex_cmdline(window, ex_cmdline)
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
from NeoVintageous.nv.modes import Mode as M, text_to_modes, MODE_NAMES_OLD
import NeoVintageous.dep.kdl as kdl
from typing import List, Union

# cfgU_settings = (f'{PACKAGE_NAME}.sublime-settings')
# cfgU_command = (f'{PACKAGE_NAME}.json')
class cfgU():
    text_commands = {
        M.Insert              : {},
        M.Normal              : {},
        M.OperatorPending    : {},
        M.Select              : {},
        M.Visual              : {},
        M.VisualBlock        : {},
        M.VisualLine         : {}
    }  # type: dict

    @staticmethod
    def load_kdl(cfg_l:List[kdl.Document]):
        from NeoVintageous.nv.mappings import mappings_add, mappings_add_text
        cfg_kdl_f = cfgU.kdl_f # config file path
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
                                _log.error(f"node ‘{g}’ already set as a direct node, overwriting")
                            cfgU.kdl[nest][g] = node
                        if (node := cfg.get(g, None)):       # 'surround' direct node
                            if g in cfgU.kdl[nest]: # dupe, but     this  is less specific, ignore
                                _log.error(f"node ‘{g}’ already set as a child of ‘{nest}’, skipping this dupe")
                            else:
                                cfgU.kdl[nest][g] = node
        #for g in cfg_group: # Rudimentary type checks (can have props, also empty is ok)
        #    if  cfgU.kdl[g] and not (cfgU.kdl[g].nodes):
        #        cfgU.kdl[g] = None; _log.warn(f"‘{g}’ in ‘{cfg_kdl_f}’ has no child nodes!")

        _import_plugins_with_user_data_kdl()


    # @staticmethod
    # def load():
    #     from NeoVintageous.nv.mappings import mappings_add, mappings_add_text
    #     global user_settings, user_commands

    #     win = sublime.active_window()

    #     _log.debug(f'🌕️@cfgU.load: user_settings={user_settings.to_dict()}\nuser_commands={user_commands.to_dict()}')

    #     cfgU.flat = flatten_dict(user_settings.to_dict()) # store a flat dictionary for easy access
    #     # but also do some validation
    #     cfgU.keymap = user_settings.get('keymap'    , None)

    #     cfgU.events = user_settings.get('events'    , None)
    #     if not (evtT := type(cfgU.events)) is dict:
    #         _log.warn(f"‘events’ in ‘{cfgU_settings}’ should be a dictionary, not {evtT}")
    #         cfgU.events = None

    #     cfgU.status   = user_settings.get('status'  , None)
    #     if not (cfgT := type(cfgU.status)) is dict:
    #         _log.warn(f"‘status’ in ‘{cfgU_settings}’ should be a dictionary, not {cfgT}")
    #         cfgU.status = None

    #     cfgU.indicator_ls   = user_settings.get('indicator_ls'  , None)
    #     if not (cfgT := type(cfgU.indicator_ls)) is dict:
    #         _log.warn(f"‘indicator_ls’ in ‘{cfgU_settings}’ should be a dictionary, not {cfgT}")
    #         cfgU.indicator_ls = None

    #     cfgU.indicator_register   = user_settings.get('indicator_register'  , None)
    #     if not (cfgT := type(cfgU.indicator_register)) is dict:
    #         _log.warn(f"‘indicator_register’ in ‘{cfgU_settings}’ should be a dictionary, not {cfgT}")
    #         cfgU.indicator_register = None

    #     cfgU.surround   = user_settings.get('surround'  , None)
    #     if not (cfgT := type(cfgU.surround)) is dict:
    #         _log.warn(f"‘surround’ in ‘{cfgU_settings}’ should be a dictionary, not {cfgT}")
    #         cfgU.surround = None

    #     cfgU.edit   = user_settings.get('edit'  , None)
    #     if not (cfgT := type(cfgU.edit)) is dict:
    #         _log.warn(f"‘edit’ in ‘{cfgU_settings}’ should be a dictionary, not {cfgT}")
    #         cfgU.edit = None

    #     # _import_plugins_with_user_data()

    #     # todo: #? convert mappings_add to a helper function that accepts enum2|enum2
    #     keybinds = user_commands.get('keybind')
    #     if   not               keybinds:
    #         pass
    #     elif not (cfgT := type(keybinds)) is dict:
    #         _log.warn(f"Type of ‘keybind’ @ ‘{cfgU_command}’ should be dict, not {cfgT}")
    #     else:
    #         for mode_string,command_list in keybinds.items():
    #             #{↑"NI"    :↑[{"m":"cmd1"},{"n":"cmd2"},]}
    #             if not (cfgT := type(command_list)) is list:
    #                 _log.warn(f"Type of ‘{mode_string}’ @ ‘{cfgU_command}’ should be list, not {cfgT}")
    #                 break
    #             modes = text_to_modes(mode_string) # "NI" → M.Normal | M.Insert
    #             if not modes:
    #                 _log.warn(f"Couldn't parse ‘{mode_string}’ @ ‘{cfgU_command}’ to a list of modes")
    #                 break
    #             if hasattr(M, modes.name): # create an iterable from a single item for ↓
    #                 modes = [modes]
    #             for mode in modes: # M.Normal
    #                 if not mode in cfgU.text_commands:
    #                     _log.warn(f"Invalid mode ‘{mode}’ in ‘{mode_string}’ in ‘{cfgU_command}’")
    #                     break
    #                 for command_dict in command_list: # {"m":"cmd1"}
    #                     if not (cfgT := type(command_dict)) is dict:
    #                         _log.warn(f"Type of ‘{command_dict}’ within ‘{mode_string}’ @‘{cfgU_command}’ should be dict, not {cfgT}")
    #                         break
    #                     for key,text_command in command_dict.items():
    #                         #{↑"m":↑"cmd1"}
    #                         cfgU.text_commands[mode][key] = text_command
    #                         mappings_add_text(mode=MODE_NAMES_OLD[mode], lhs=key, rhs=text_command)

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

# def _import_plugins_with_user_data():
#     from NeoVintageous.nv import plugin_surround
#     plugin_surround.reload_with_user_data()
#     from NeoVintageous.nv import vim
#     vim.reload_with_user_data()
#     from NeoVintageous.nv import state
#     state.reload_with_user_data()
#     from NeoVintageous.nv import ex_cmds
#     ex_cmds.reload_with_user_data()
#     from NeoVintageous.nv import registers
#     registers.reload_with_user_data()

from pathlib import Path
from NeoVintageous.nv.cfg_parse import parse_kdl_config
def load_cfgU_kdl() -> None:
    global cfgU
    cfg_p = _file_path_config_kdl()
    if (cfg_f := Path(cfg_p).expanduser()).exists():
        try:
            with open(cfg_f, 'r', encoding='utf-8', errors='replace') as f:
                cfg = f.read()
        except FileNotFoundError as e:
            sublime.error_message(f"{PACKAGE_NAME}:\nTried and failed to load\n{cfg_f}")
            return
    else:
        # sublime.error_message(f"{PACKAGE_NAME}:\nCouldn't find\n{cfg_p}") # this config file is optional
        return
    kdl_docs = [] # list of KDL docs in the order of parsing, includes imports as separate items
    parse_kdl_config(cfg, cfg_f, kdl_docs)
    cfgU.kdl_f = cfg_f
    cfgU.load_kdl(kdl_docs)

# def load_cfgU() -> None:
#     """load alternative user config file to a global class and add a watcher event to track changes"""
#     global cfgU
#     global user_settings, user_commands

#     try:
#         user_settings = sublime.load_settings(cfgU_settings)
#         user_commands = sublime.load_settings(cfgU_command)
#         cfgU.load();
#         user_settings.clear_on_change(PACKAGE_NAME)
#         user_settings.add_on_change  (PACKAGE_NAME, lambda: cfgU.load())
#         user_commands.clear_on_change(PACKAGE_NAME)
#         user_commands.add_on_change  (PACKAGE_NAME, lambda: cfgU.load())
#     except FileNotFoundError:
#         _log.info(f'‘{cfgU_settings}’ or ‘{cfgU_command}’ file(s) not found')

# def _unload_cfgU() -> None: # clear config change watcher
#     global cfgU
#     global user_settings, user_commands

#     user_settings.clear_on_change(PACKAGE_NAME)
#     user_commands.clear_on_change(PACKAGE_NAME)
