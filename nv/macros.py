from string import ascii_letters, digits

from NeoVintageous.nv.polyfill import erase_status, set_status
from NeoVintageous.nv.session  import get_session_value, maybe_do_runtime_save_session, set_session_value
from NeoVintageous.nv.settings import get_glue_until_normal_mode
from NeoVintageous.nv.rc       import cfgU

_data = {}  # type: dict

RU_LETTERS = 'йцукенгшщзхъфывапролджэёячсмитьбюЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЁЯЧСМИТЬБЮ'

DEF = {
    'record':'recording @',# prefix when recording
}
import copy
CFG = copy.deepcopy(DEF) # copy defaults to be able to reset values on config reload


def reload_with_user_data_kdl() -> None:
    if hasattr(cfgU,'kdl') and (nest := cfgU.kdl.get('indicator',None))\
        and                    (cfg  :=     nest.get('macro',None)): # skip on initial import when Plugin API isn't ready, so no settings are loaded
        global CFG
        # _log.debug(f"@macros: Parsing config indicator/macro")
        for cfg_key in CFG:
            if (node := cfg.get(cfg_key,None)): # record "🔴" node/arg pair
                args = False
                for i,(arg,tag,val) in enumerate(cfgU.cfg_parse.arg_tag_val(node)):
                    args = True
                    if i == 0:
                        if tag:
                            _log.warn("node ‘%s’ has unrecognized tag in argument ‘%s’",node.name,arg)
                        CFG[node.name] = val #;_log.debug('indicator macro from arg @%s %s',node.name,val)
                    elif i > 0:
                        _log.warn("node ‘%s’ has extra arguments in its child ‘%s’ (only the 1st was used): ‘%s’...",cfg_key,node.name,arg)
                        break
                if not args:
                    _log.warn("node ‘%s’ is missing arguments in its child ‘%s’"
                        ,         cfg_key,                               node.name)
        node = cfg
        for i,(key,tag_val,tag,val) in enumerate(prop_key_tag_val(node)): # record="🔴", alt notation to child node/arg pairs
            if tag:
                _log.warn("node ‘%s’ has unrecognized tag in property ‘%s=%s’",node.name,key,tag_val)
            if key in CFG:
                CFG[key] = val ;_log.debug("indicator macro from property ‘%s=%s’",key,val)
            else:
                _log.error("node ‘%s’ has unrecognized property ‘%s=%s’",node.name,key,tag_val)
    else:
        CFG = copy.deepcopy(DEF) # copy defaults to be able to reset values on config reload


def is_readable(name: str) -> bool:
    return name in tuple(digits + ascii_letters + RU_LETTERS + '".=*+@')


def is_writable(name: str) -> bool:
    return name in tuple(digits + ascii_letters + RU_LETTERS + '"')


def is_recording() -> bool:
    return _data.get('recording', False)


def start_recording(name: str) -> None:
    _data['recording'         ] = True
    _data['recording_steps'   ] = []
    _data['recording_register'] = name

    set_status('vim-recording', f"{CFG['record']}{name}")


def stop_recording() -> None:
    name = _data.get('recording_register')
    if name:
        macros = _get_macros()
        steps = _get_steps()
        if steps:
            macros[name] = steps
        else:
            try:
                del macros[name]
            except KeyError:
                pass

        maybe_do_runtime_save_session()

    _data['recording'         ] = False
    _data['recording_steps'   ] = []
    _data['recording_register'] = None

    erase_status('vim-recording')


def _get_macros() -> dict:
    return get_session_value('macros', {})


def _get_steps() -> list:
    return _data.get('recording_steps', [])


def get_recorded(name: str):
    return _get_macros().get(name)


def get_last_used_register_name() -> str:
    return get_session_value('last_used_register_name')


def set_last_used_register_name(name: str) -> None:
    set_session_value('last_used_register_name', name, persist=True)


def add_macro_step(view, cmd: str, args: dict) -> None:
    if is_recording():
        if cmd == 'nv_vi_toggle_macro_record': # Don't store the ending macro step.
            return
        if not get_glue_until_normal_mode(view):
            _data['recording_steps'].append((cmd, args))
