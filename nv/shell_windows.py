import os
import subprocess
import sys
import tempfile
import traceback

from NeoVintageous.nv.options import get_option
from NeoVintageous.nv.settings import get_setting

# https://mypy.readthedocs.io/en/latest/common_issues.html#python-version-and-system-platform-checks
assert sys.platform.startswith('win')

try:
    import ctypes
except ImportError:
    traceback.print_exc()
    ctypes = None


def open(view) -> None:
    term = get_setting(view, 'terminal', 'cmd.exe')
    if term:
        args = [term]
        if term == 'cmd.exe':
            args.append('/k')

        subprocess.Popen(args, cwd=os.getcwd())


def read(view, cmd: str) -> str:
    p = subprocess.Popen([get_option(view, 'shell'), '/c', cmd],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         startupinfo=_get_startup_info())

    out, err = p.communicate()

    if out:
        return _translate_newlines(out.decode(_get_encoding()))

    if err:
        return _translate_newlines(err.decode(_get_encoding()))

    return ''


def filter_region(view, txt: str, cmd: str) -> str:
    try:
        contents = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
        contents.write(txt.encode('utf-8'))
        contents.close()

        script = tempfile.NamedTemporaryFile(suffix='.bat', delete=False)
        script.write(('@echo off\ntype %s | %s' % (contents.name, cmd)).encode('utf-8'))
        script.close()

        p = subprocess.Popen([script.name],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             startupinfo=_get_startup_info())

        out, err = p.communicate()

        if out:
            return _translate_newlines(out.decode(_get_encoding()))

        if err:
            return _translate_newlines(err.decode(_get_encoding()))

        return ''
    finally:
        os.remove(script.name)
        os.remove(contents.name)


def _get_startup_info():
    # Hide the child process window.
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    return startupinfo


def _get_encoding() -> str:
    if ((enc := ctypes.windll.kernel32.GetOEMCP()) == 65001):
        return 'UTF-8'
    else:
        return str(enc)


# TODO Review Do newlines really need to converted on Windows?
def _translate_newlines(text: str):
    return text.replace('\r\n', '\n')
