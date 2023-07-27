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


from NeoVintageous.plugin import DEFAULT_LOG_LEVEL
_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)


def _file_name() -> str:
    return '.neovintageousrc'


def _file_path() -> str:
    return os.path.join(sublime.packages_path(), 'User', _file_name())


def open_rc(window) -> None:
    file = _file_path()

    if not os.path.exists(file):
        with builtins.open(file, 'w', encoding='utf-8') as f:
            f.write('" Type :help nv for help.\n')

    window.open_file(file)


def load_rc() -> None:
    _log.debug('load %s', _file_path())
    _load()


def reload_rc() -> None:
    _log.debug('reload %s', _file_path())
    _unload()
    _load()


def _unload() -> None:
    from NeoVintageous.nv.mappings import mappings_clear
    from NeoVintageous.nv.variables import variables_clear

    variables_clear()
    mappings_clear()
    _unload_cfgU()


def _load() -> None:
    try:
        from NeoVintageous.nv.ex_cmds import do_ex_cmdline
        window = sublime.active_window()
        with builtins.open(_file_path(), 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                ex_cmdline = _parse_line(line)
                if ex_cmdline:
                    do_ex_cmdline(window, ex_cmdline)

        print('%s file loaded' % _file_name())
    except FileNotFoundError:
        _log.info('%s file not found', _file_name())
    load_cfgU()


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
from NeoVintageous.nv.mappings import mappings_add, mappings_add_text

cfgU_settings = (f'{PACKAGE_NAME}.sublime-settings')
cfgU_command = (f'{PACKAGE_NAME}.json')
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
    def load():
        global user_settings, user_commands

        win = sublime.active_window()

        _log.debug(f'🌕️@cfgU.load: user_settings={user_settings.to_dict()}\nuser_commands={user_commands.to_dict()}')

        cfgU.keymap = user_settings.get('keymap'    , None)

        cfgU.events = user_settings.get('events'    , None)
        if not (evtT := type(cfgU.events)) is dict:
            _log.warn(f"⚠️‘events’ in ‘{cfgU_settings}’ should be a dictionary, not {evtT}")
            cfgU.events = None

        cfgU.status   = user_settings.get('status'  , None)
        if not (cfgT := type(cfgU.status)) is dict:
            _log.warn(f"⚠️‘status’ in ‘{cfgU_settings}’ should be a dictionary, not {cfgT}")
            cfgU.status = None

        cfgU.surround   = user_settings.get('surround'  , None)
        if not (cfgT := type(cfgU.surround)) is dict:
            _log.warn(f"⚠️‘surround’ in ‘{cfgU_settings}’ should be a dictionary, not {cfgT}")
            cfgU.surround = None


        _import_plugins_with_user_data()

        # todo: #? convert mappings_add to a helper function that accepts enum2|enum2
        commands_all = user_commands.get('commands')
        if not (cfgT := type(commands_all)) is dict:
            _log.warn(f"⚠️Type of ‘commands’ @ ‘{cfgU_command}’ should be dict, not {cfgT}")
        else:
            for mode_string,command_list in commands_all.items():
                #{↑"NI"    :↑[{"m":"cmd1"},{"n":"cmd2"},]}
                if not (cfgT := type(command_list)) is list:
                    _log.warn(f"⚠️Type of ‘{mode_string}’ @ ‘{cfgU_command}’ should be list, not {cfgT}")
                    break
                modes = text_to_modes(mode_string) # "NI" → M.Normal | M.Insert
                if not modes:
                    _log.warn(f"⚠️Couldn't parse ‘{mode_string}’ @ ‘{cfgU_command}’ to a list of modes")
                    break
                if hasattr(M, modes.name): # create an iterable from a single item for ↓
                    modes = [modes]
                for mode in modes: # M.Normal
                    if not mode in cfgU.text_commands:
                        _log.warn(f"⚠️Invalid mode ‘{mode}’ in ‘{mode_string}’ in ‘{cfgU_command}’")
                        break
                    for command_dict in command_list: # {"m":"cmd1"}
                        if not (cfgT := type(command_dict)) is dict:
                            _log.warn(f"⚠️Type of ‘{command_dict}’ within ‘{mode_string}’ @‘{cfgU_command}’ should be dict, not {cfgT}")
                            break
                        for key,text_command in command_dict.items():
                            #{↑"m":↑"cmd1"}
                            cfgU.text_commands[mode][key] = text_command
                            mappings_add_text(mode=MODE_NAMES_OLD[mode], lhs=key, rhs=text_command)

def _import_plugins_with_user_data():
    from NeoVintageous.nv import plugin_surround
    plugin_surround.reload_with_user_data()
    from NeoVintageous.nv import vim
    vim.reload_with_user_data()
    from NeoVintageous.nv import state
    state.reload_with_user_data()

def load_cfgU() -> None: # load alternative user config file to a global class and add a watcher event to track changes
    # load user config file to a global class and add a watcher event to track changes
    global cfgU
    global user_settings, user_commands

    try:
        user_settings = sublime.load_settings(cfgU_settings)
        user_commands = sublime.load_settings(cfgU_command)
        cfgU.load();
        user_settings.clear_on_change(PACKAGE_NAME)
        user_settings.add_on_change  (PACKAGE_NAME, lambda: cfgU.load())
        user_commands.clear_on_change(PACKAGE_NAME)
        user_commands.add_on_change  (PACKAGE_NAME, lambda: cfgU.load())
    except FileNotFoundError:
        _log.info(f'‘{cfgU_settings}’ or ‘{cfgU_command}’ file(s) not found')

def _unload_cfgU() -> None: # clear config change watcher
    global cfgU
    global user_settings, user_commands

    user_settings.clear_on_change(PACKAGE_NAME)
    user_commands.clear_on_change(PACKAGE_NAME)
