from string import ascii_letters
from string import digits

from NeoVintageous.nv.polyfill import erase_status
from NeoVintageous.nv.polyfill import set_status
from NeoVintageous.nv.session import get_session_value
from NeoVintageous.nv.session import maybe_do_runtime_save_session
from NeoVintageous.nv.session import set_session_value
from NeoVintageous.nv.settings import get_glue_until_normal_mode

_data = {}  # type: dict

RU_LETTERS = 'йцукенгшщзхъфывапролджэёячсмитьбюЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЁЯЧСМИТЬБЮ'

def is_readable(name: str) -> bool:
    return name in tuple(digits + ascii_letters + RU_LETTERS + '".=*+@')


def is_writable(name: str) -> bool:
    return name in tuple(digits + ascii_letters + RU_LETTERS + '"')


def is_recording() -> bool:
    return _data.get('recording', False)


def start_recording(name: str) -> None:
    _data['recording'] = True
    _data['recording_steps'] = []
    _data['recording_register'] = name

    set_status('vim-recording', 'recording @%s' % name)


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

    _data['recording'] = False
    _data['recording_steps'] = []
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
