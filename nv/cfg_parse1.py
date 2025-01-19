import re
import logging
from typing  import Union
from pathlib import Path

import sublime
import sublime_plugin

import NeoVintageous.dep.kdl as kdl
import NeoVintageous.dep.kdl2 as kdl2

def _parse_set_kdl1(node:kdl.Node,cfg='') -> None:
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
def _parse_let_kdl1(node:kdl.Node,cfg='') -> None:
    if not node.props:
        _log.warn("%sconfig has a ‘let’ command without var=value properties (%s)",
            f'‘{cfg}’ ' if cfg else '',                                     node)
    for pkey,tag_val in node.props.items():
        tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
        val = tag_val.value if hasattr(tag_val,'value') else tag_val
        _log.debug(f"set var from kdl: ¦{pkey}¦=¦{val}¦")
        variables.set(pkey,val)

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
def _parse_general_cfg_kdl1(general_cfg:kdl.Node,CFG:dict,DEF:dict,st_pref=None) -> None:
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
        _parse_let_kdl1(node)
        return None
    elif opt_name == 'set':
        _parse_set_kdl1(node)
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

def _parse_keybind_arg1(node:kdl.Node, CFG:dict, prop_subl={}):
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
def _parse_vars_kdl1(node_vars:kdl.Node,CFG:dict,var_d:dict={}):
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

def _parse_keybinds_kdl1(keybinds:kdl.Node,CFG:dict,var_d:dict={}):
    var_d_combo = _parse_vars_kdl1(keybinds,CFG,var_d)
    for kb_node in keybinds.nodes: # (Ⓝ)"q" "OpenNameSpace"
        _parse_keybind_kdl1(keybind=kb_node, CFG=CFG, var_d=var_d_combo)
def _parse_keybind_kdl1(keybind:kdl.Node, CFG:dict, gmodes:Mode=Mode(0),var_d:dict={}):
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
        _parse_let_kdl1(node)
        return
    if key == 'set':
        _parse_set_kdl1(node)
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
    (cmd,isChain)         = _parse_keybind_arg1(node=node, CFG=CFG, prop_subl=prop_rest) # Parse arguments
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
            (cmd,_) = _parse_keybind_arg1(node=child, CFG=CFG, prop_subl=prop_rest)
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
            _parse_keybind_kdl1(keybind=child, CFG=CFG, gmodes=modes, var_d=var_d)


