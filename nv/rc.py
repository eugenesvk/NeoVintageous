import builtins
import logging
import os
import re
import json
from pathlib import Path
from typing import List, Union
import time
from datetime import datetime

import sublime

import NeoVintageous.dep.kdl as kdl
import NeoVintageous.dep.kdl2 as kdl2
from NeoVintageous.nv.polyfill import nv_message as message
from NeoVintageous.nv.helper import flatten_dict, flatten_kdl, Singleton


from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL, TFMT, DFMT
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


t = datetime.now()
def load_rc() -> None:
    global t
    _log.t("load_rc      ⏰%s %s", DFMT.format(t=(datetime.now() - t)), TFMT.format(t=(t:=datetime.now())))
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
    global t
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
    _log.t("load_kdl pre ⏰%s %s", DFMT.format(t=(datetime.now() - t)), TFMT.format(t=(t:=datetime.now())))
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

from NeoVintageous.nv.cfg_parse import clean_name, clean_cmd
re_count = re.compile(r"[№⌗×⋅cn](\d+)")
re_subl_tag = re.compile(r"subl|sublime|st")
re_filetype = re.compile(r"[\s,]+")
_keybind_prop = {
    'desc':['d','des','desc','description','inf','info'],
    'icon':['i','icn','icon','img','image'],
    'type':['t','type'],
    'file':['ft','filetype'],
    'defk':['defk','default_key','≝k'],
    'defc':['defc','default_cmd','≝c'],
    }

def _parse_set_kdl(node:kdl.Node,cfg='') -> None:
    from NeoVintageous.nv.ex_cmds import ex_set # inline import to avoid circular dependency errors
    win  = sublime.active_window()
    view = win.active_view()
    args = dict()
    if win:
        args['window'] = win
    if view:
        args['view']   = view

    for arg in node.args:          # Parse arguments
        tag = clean_name(arg.tag   if hasattr(arg,'tag'  ) else '' )
        val = clean_cmd (arg.value if hasattr(arg,'value') else arg)
        _log.debug(f"set option from kdl arg: ¦{val}¦")
        ex_set(option=val,value=None, **args)
    for pkey,tag_val in node.props.items(): # Parse properties
        tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
        val = tag_val.value if hasattr(tag_val,'value') else tag_val
        _log.debug(f"set option from kdl prop: ¦{pkey}¦=¦{val}¦")
        if   val == True:
            opt_key =       pkey
            opt_val = None
        elif val == False:
            opt_key = 'no' +pkey
            opt_val = None
        elif val in ['inv','invert','!']:
            opt_key = 'inv'+pkey
            opt_val = None
        elif val in ['show','?']:
            opt_key =       pkey+'?'
            opt_val = None
        else:
            opt_key =       pkey
            opt_val = val
        ex_set(option=opt_key,value=opt_val, **args)

from NeoVintageous.nv import variables
def _parse_let_kdl(node:kdl.Node,cfg='') -> None:
    if not node.props:
        _log.warn("%sconfig has a ‘let’ command without var=value properties (%s)",
            f'‘{cfg}’ ' if cfg else '',                                     node)
    for pkey,tag_val in node.props.items():
        tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
        val = tag_val.value if hasattr(tag_val,'value') else tag_val
        _log.debug(f"set var from kdl: ¦{pkey}¦=¦{val}¦")
        variables.set(pkey,val)

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

def _parse_rc_g_kdl(rc_g:kdl.Node):
    win = sublime.active_window()
    for node in rc_g.nodes: # r#":set invrelativenumber"#
        _parse_rc_cfg_kdl(win,rc_cfg=node)
def _parse_rc_cfg_kdl(win,rc_cfg:kdl.Node) -> None:
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

def _parse_general_g_kdl(general_g:kdl.Node):
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
        _parse_general_cfg_kdl(general_cfg=node,st_pref=st_pref)
def _parse_general_cfg_kdl(general_cfg:kdl.Node,st_pref=None) -> None:
    if not (cfgT := type(general_cfg)) is kdl.Node:
        _log.error("Type of ‘general’ config group should be kdl.Node, not ‘%s’",cfgT)
        return None
    node = general_cfg          # set relativenumber=true
    opt_name    = node.name     # ‘set’
    if   opt_name == '≠': # skip comment nodes (todo: when lib supports roundtrip, save as actual comments)
        return
    elif opt_name == 'source': # source was loaded before
        return
    elif opt_name == 'let':
        _parse_let_kdl(node)
        return None
    elif opt_name == 'set':
        _parse_set_kdl(node)
        return None
    elif opt_name == 'vardef': #vardef pre="‹" pos="›"
        # print('CFG pre',CFG)
        tag_val = node.name
        tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
        val = tag_val.value if hasattr(tag_val,'value') else tag_val
        if tag: # vardef should have no tags
            _log.warn("node ‘%s’ has unrecognized tag",node.name)
            return None
        for pkey,tag_val in node.props.items(): # parse definition properties
            tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
            val = tag_val.value if hasattr(tag_val,'value') else tag_val
            if pkey == 'pre':
                CFG['var_def'][0] = val #‹
            if pkey == 'pos':
                CFG['var_def'][1] = val #›
        # print('CFG pos',CFG)
        return None
    elif opt_name in DEF['gen_def']:
        opt_d    =   DEF['gen_def'][opt_name]
        name_def = opt_d['key'] # vintageous_auto_switch_input_method
        type_def = opt_d['t']   # bool
        val_def  = opt_d['v']   # False
        if type_def == dict: # todo: iterate over values to strip tags?
            if not node.props:
                _log.error("Unrecognized option type for %s in the ‘general’ config group, expecting %s, but there are no key=val properties!"
                        ,                             opt_name,                                   type_def)
            else:
                CFG['general'][name_def] = node.props
                _over = ''
                if  st_pref.has(f"vintageous_{name_def}"): # override Preferences with KDL's
                    st_pref.set(f"vintageous_{name_def}", node.props)
                    _over = ' (overridden Preferences)'
                if  st_pref.has(           f"{name_def}"): # override Preferences with KDL's
                    st_pref.set(           f"{name_def}", node.props)
                    _over = ' (overridden Preferences)'
                _log.cfg("set user dict ‘%s’=‘%s’%s",name_def,node.props,_over)
            return None
        else:
            for arg in node.args:
                tag = arg.tag   if hasattr(arg,'tag'  ) else ''
                val = arg.value if hasattr(arg,'value') else arg
                _log.debug("%s %s %s", arg, f"tag={tag}", f"val={val}")
                isSameType = False
                if     isinstance(    type_def,type):
                    if isinstance(val,type_def):
                        isSameType = True
                elif isinstance(type_def,list):
                    for t_ in type_def:
                        if isinstance(val,t_):
                            isSameType = True
                if not isSameType:
                    _log.error("Unrecognized option type for %s in the ‘general’ config group, expecting %s not ‘%s’ (‘%s’)"
                        ,                             opt_name,                                   type_def,type(val),val)
                    return None
                CFG['general'][name_def] = val
                _over = ''
                if  st_pref.has(f"vintageous_{name_def}"): # override Preferences with KDL's
                    st_pref.set(f"vintageous_{name_def}", val)
                    _over = ' (overridden Preferences)'
                if  st_pref.has(           f"{name_def}"):
                    st_pref.set(           f"{name_def}", val)
                    _over = ' (overridden Preferences)'
                _log.cfg("set user ‘%s=%s’ (%s)%s"
                    ,         name_def,val, type(val), _over)
                return None
    else:
        _log.error("Unrecognized option type within ‘general’ config group, expecting ‘let’/‘set’/‘-’, not ‘%s’",opt_name)
        return None

def _parse_keybind_arg(node:kdl.Node, prop_subl={}):
    cmd_l   = []
    isChain = False
    for arg in node.args:          # Parse arguments
        tag = clean_name(arg.tag   if hasattr(arg,'tag'  ) else '' )
        val = clean_cmd (arg.value if hasattr(arg,'value') else arg)
        val_dirt = arg.value if hasattr(arg,'value') else arg
        count = 1
        if val == 'chain':
            isChain = True
            continue
        if re_subl_tag.search(tag): # Sublime command per tag, serialize into a json dump
            prop_subl_clean = copy.deepcopy(prop_subl)
            for key in prop_subl: # remove reserved flags so Sublime doesn't choke on them
                if clean_name(key) in CFG['res_tag']:
                    del prop_subl_clean[key]
            subl_arg = f',"args":{json.dumps(prop_subl_clean)}' if prop_subl_clean else ''
            cmd      = f'"command":"{val_dirt}"{subl_arg}<CR>'
            # (Ⓝ)q (subl)"move" by="words" forward=true extend=true
            # →"command":"move","args":{"by": "words", "forward": true, "extend": true}<CR>
            _log.cfg("parsed (subl) command ¦%s¦ val_dirty=¦%s¦ arg=¦%s¦ → ¦%s¦"
                ,                            cmd, val_dirt,subl_arg, prop_subl_clean)
        else:
            cmd = val
        if count_l := re_count.findall(tag): # find a count tag and add commands×count
            count = int(count_l[0])
        for i in range(1,1+(count if count > 1 else 1)):
            cmd_l.append(cmd)
    return (cmd_l, isChain)
def _parse_vars_kdl(node_vars:kdl.Node,var_d:dict={}):
    # print(f"var_d pre {var_d}")
    # use var_d from #import key=val props to seed initial values
    pre = CFG['var_def'][0] #‘
    pos = CFG['var_def'][1] #’
    if 'def' in var_d:
        var_def = var_d['def']
        if len(var_def) >= 2:
            pre = var_def[0]
            pos = var_def[1]
    var_set = var_d['set'] if 'set' in var_d else dict()
    for node in node_vars.getAll('vardef'):
        tag_val = node.name
        tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
        val = tag_val.value if hasattr(tag_val,'value') else tag_val
        if tag: # vardef should have no tags
            _log.warn("node ‘%s’ has unrecognized tag",node.name)
            continue
        for pkey,tag_val in node.props.items(): # parse definition properties
            tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
            val = tag_val.value if hasattr(tag_val,'value') else tag_val
            if pkey == 'pre':
                pre = val
            if pkey == 'pos':
                pos = val
    var_def = [pre,pos]
    for node in node_vars.getAll('varset'):
        tag_val = node.name
        tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
        val = tag_val.value if hasattr(tag_val,'value') else tag_val
        if tag: # vardef/set should have no tags
            continue
        for (key,tag_val) in node.props.items(): # 2. testvar=⎇ key=value pairs
            if hasattr(tag_val,'value'): #=(t)⎇ if (t) exists (though shouldn't)
                val = tag_val.value # ignore tag
                _log.warn("node ‘%s’ has unrecognized tag in argument ‘%s’"
                    ,      node.name,                               tag_val)
            else:
                val = tag_val
            var_set[key.lower()] = val
    _log.debug("found in vardef¦%s¦ and varset¦%s¦"
        ,                  var_def,         var_set)
    re_flags = 0
    re_flags |= re.MULTILINE | re.IGNORECASE
    re_var_set_p = f'{pre}(' + f'){pos}|{pre}('.join(var_set.keys()) + f'){pos}'
    re_var_set = re.compile(re_var_set_p, flags=re_flags)
    var_d['def'] = var_def
    var_d['set'] = var_set
    var_d['re']  = re_var_set
    # print(f"var_d pos {var_d}")
    return var_d

def _parse_keybinds_kdl(keybinds:kdl.Node,var_d:dict={}):
    var_d_combo = _parse_vars_kdl(keybinds,var_d)
    for kb_node in keybinds.nodes: # (Ⓝ)"q" "OpenNameSpace"
        _parse_keybind_kdl(keybind=kb_node, var_d=var_d_combo)
def _parse_keybind_kdl(keybind:kdl.Node, gmodes:Mode=Mode(0), var_d:dict={}):
    from NeoVintageous.nv.mappings import mappings_add, mappings_add_text
    if not (cfgT := type(keybind)) is kdl.Node:
        _log.error("Type of ‘keybind’ should be kdl.Node, not ‘%s’",cfgT)
        return None
    node = keybind                 # (Ⓝ)"q" "OpenNameSpace"
    mode_s = node.tag              # ‘Ⓝ’
    key    = node.name             # ‘q’
    children = node.nodes          # either full keybinds or just commands with Chain argument
    cmd_txt = []                   # ‘[OpenNameSpace]’
    if key in ['vardef','varset'] and node.tag is None: # skip variables (parsed earlier)
        return
    if key == '≠': # skip comment nodes (todo: when lib supports roundtrip, save as actual comments)
        return
    if key == 'let':
        _parse_let_kdl(node)
        return
    if key == 'set':
        _parse_set_kdl(node)
        return
    if var_d and var_d['set']:
        # key_old = key # ‘var_name’ → var_value (match ‘var_name’, but need to find value for var_name, so use index to find the ‘(var_name)’ regex match)
        if key:
            key    = var_d['re'].sub(lambda m: m.group().replace(m.group(),var_d['set'][m[m.lastindex]],1), key   )
        if mode_s:
            mode_s = var_d['re'].sub(lambda m: m.group().replace(m.group(),var_d['set'][m[m.lastindex]],1), mode_s)
        # if not key_old == key:
            # _log.debug("replaced var in key: %s → %s"
                # ,                        key_old, key)
    modes  = text_to_modes(mode_s) # ‘Mode.Normal’ enum for ‘Ⓝ’ (‘Mode.Any’ for None tag)
    if gmodes:
        if mode_s:
            modes |= gmodes        # append modes from a group
        else:
            modes  = gmodes        # replace ‘Mode.Any’ with group mode

    prop = dict()                  # Parse properties
    prop_rest = dict()             # Properties left from known defaults (e.g., part of Sublime commands)
    for pkey,tag_val in node.props.items(): # ‘i="✗" d="Close a tab"’
        tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
        val = tag_val.value if hasattr(tag_val,'value') else tag_val
        for dkey,key_abbrev in _keybind_prop.items():
            if dkey == 'file':
                if pkey in key_abbrev: # ['ft','filetype']
                    prop[dkey] = []
                    prop[dkey].extend(re_filetype.split(val))
            else:
                if pkey in key_abbrev:
                    prop[dkey] = val
            if pkey not in key_abbrev: # non-specified key=val pairs
                if isinstance(val,float) and val.is_integer():
                    prop_rest[pkey] = int(val)
                else:
                    prop_rest[pkey] = val
    (cmd,isChain)         = _parse_keybind_arg(node=node, prop_subl=prop_rest) # Parse arguments
    cmd_txt.extend(cmd)
    if children and isChain:           # with Chain argument...
        for child in children:         # ...parse children as commands
            prop_rest = dict()
            for pkey,tag_val in child.props.items(): #
                tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
                val = tag_val.value if hasattr(tag_val,'value') else tag_val
                for dkey,key_abbrev in _keybind_prop.items():
                    if pkey not in key_abbrev: # non-specified key=val pairs
                        prop_rest[pkey] = val
            (cmd,_) = _parse_keybind_arg(node=child, prop_subl=prop_rest)
            cmd_txt.extend(cmd)

    if not modes:
        _log.error("Couldn't parse ‘%s’ to a list of modes, skipping ‘%s’"
            ,                     mode_s,                            node)
        return
    if not key:
        _log.error("Missing keyboard shortcut, skipping ‘%s’",node)
        return
    if not cmd_txt and not children:
        _log.error("Missing text command(s), skipping ‘%s’",node)
        return
    if (m_inv := modes & ~M.CmdTxt): # if there are more modes than allowed
        # s = 's' if len(m_inv) > 1 else '' # TODO len fails in py3.8
        mode_sym = ''
        for mode in M_ANY: # TODO: m_inv iteration fails in py3.8
            if mode & m_inv: # todo: store original re matches in text_to_mode to allow roundtrip of modes matching user input
                mode_sym += mode_names[mode][0]
        s = 's' if len(mode_sym) > 1 else ''
        _log.warn("Invalid mode%s ‘%s’ in ‘%s’ in node ‘%s’"
            ,                  s,mode_sym,mode_s,     node)
    if cmd_txt:
        for mode in M_CMDTXT: # iterate over all of the allowed modes
            if mode & modes:  # if it's part of the keybind's modes, register the key
                cfgU.text_commands[mode][key] = cmd_txt
                mappings_add_text(mode=MODE_NAMES_OLD[mode], key=key, cmd=cmd_txt, prop=prop)
                # print(f"kb map+ ({mode}){key}={cmd_txt} with {prop}")
    if children and not isChain:       # without Chain argument...
        for child in children:         # ...parse children as keybinds
            _parse_keybind_kdl(keybind=child, gmodes=modes, var_d=var_d)

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
        try:
            parse_kdl2_config(cfg, cfg_f, kdl_docs)
            return kdl_docs
        except Exception as e2:
            # print(f"couldn't parse the docs as KDL2 due to: {e2}")
            try:
                NeoVintageous.nv._KDL_VERSION = 1
                parse_kdl_config(cfg, cfg_f, kdl_docs)
                return kdl_docs
            except Exception as e1:
                print(f"Couldn't parse {cfg_f} as KDL2 due to: {e2}")
                print(f"  nor as KDL1 due to: {e1}")
                return []

    @staticmethod
    def load_kdl():
        global t
        if hasattr(cfgU,'kdl') and cfgU.kdl: # avoid loading the same config multiple times
            return
        cfg_l:List[(kdl.Document,dict)] = cfgU.read_kdl_file()
        _log.t("load_kdl file ⏰%s %s", DFMT.format(t=(datetime.now() - t)), TFMT.format(t=(t:=datetime.now())))
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

        _log.t("load_kdl pars ⏰%s %s", DFMT.format(t=(datetime.now() - t)), TFMT.format(t=(t:=datetime.now())))
        ignore = {1:cfg_group, 2:[]} # ignore the lowest level dictionary groups as they repeat node names
        for g,subg in cfg_nest.items():
            ignore[2] += subg
        cfgU.flat = flatten_kdl(cfgU.kdl, ignore=ignore) # store a flat dictionary for easy access
        _log.t("load_kdl flat ⏰%s %s", DFMT.format(t=(datetime.now() - t)), TFMT.format(t=(t:=datetime.now())))
        # print('cfgU.flat', cfgU.flat)

        if (general_g := cfgU.kdl['general']):
            _parse_general_g_kdl(general_g=general_g)
        _log.t("load_kdl gen  ⏰%s %s", DFMT.format(t=(datetime.now() - t)), TFMT.format(t=(t:=datetime.now())))

        if (rc_g := cfgU.kdl['rc']):
            _parse_rc_g_kdl(rc_g=rc_g)
        _log.t("load_kdl rc   ⏰%s %s", DFMT.format(t=(datetime.now() - t)), TFMT.format(t=(t:=datetime.now())))

        for (keybind,var_d) in cfgU.kdl['keybind']:
            _parse_keybinds_kdl(keybinds=keybind,var_d=var_d)
        _log.t("load_kdl key  ⏰%s %s", DFMT.format(t=(datetime.now() - t)), TFMT.format(t=(t:=datetime.now())))

        _import_plugins_with_user_data_kdl()
        _log.t("load_kdl imp  ⏰%s %s", DFMT.format(t=(datetime.now() - t)), TFMT.format(t=(t:=datetime.now())))

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
