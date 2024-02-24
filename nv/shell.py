import sys
import traceback

from sublime import platform
from sublime import Region

from NeoVintageous.nv.polyfill import set_selection

if   sys.platform.startswith('win'   ) and platform() == 'windows':
    from NeoVintageous.nv import shell_windows as _shell
elif sys.platform.startswith('linux' ) and platform() == 'linux'  :
    from NeoVintageous.nv import shell_linux   as _shell
elif sys.platform.startswith('darwin') and platform() == 'osx'    :
    from NeoVintageous.nv import shell_osx     as _shell
else:
    raise ImportError('no os specific module found')


def open(view) -> None:
    try:
        _shell.open(view)
    except Exception:  # pragma: no cover
        traceback.print_exc()


def read(view, cmd: str) -> str:
    try:
        return _shell.read(view, cmd)
    except Exception:  # pragma: no cover
        traceback.print_exc()

    return ''


def filter_thru_shell(view, edit, regions, cmd: str) -> None:
    # Maintain text size delta as we replace each selection going forward. We
    # can't simply go in reverse because cursor positions will be incorrect.
    accumulated_delta = 0
    new_points = []
    for r in regions:
        r_shifted = Region(r.begin() + accumulated_delta, r.end() + accumulated_delta)
        rv = _shell.filter_region(view, view.substr(r_shifted), cmd).rstrip() + '\n'
        view.replace(edit, r_shifted, rv)
        new_points.append(r_shifted.a)
        accumulated_delta += len(rv) - r_shifted.size()

    # Switch to normal mode and move cursor(s) to beginning of replacement(s).
    view.run_command('nv_enter_normal_mode')
    set_selection(view, new_points)
