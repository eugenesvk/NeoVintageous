import os
import subprocess

from NeoVintageous.nv.options import get_option
from NeoVintageous.nv.settings import get_setting


def open(view) -> None:
    term = get_setting(view, 'terminal', os.environ.get('TERM'))
    if term:
        subprocess.Popen([term, '-e', 'bash'], cwd=os.getcwd())


def read(view, cmd: str) -> str:
    p = subprocess.Popen([get_option(view, 'shell'), '-c', cmd],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)

    out, err = p.communicate()

    if out:
        return out.decode('utf-8')

    if err:
        return err.decode('utf-8')

    return ''


def filter_region(view, text: str, cmd: str) -> str:
    # Redirect STDERR to STDOUT to capture both.
    # This seems to be the behavior of vim as well.
    p = subprocess.Popen([get_option(view, 'shell'), '-c', cmd],
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)

    # Pass in text as input: saves having to deal with quoting stuff.
    out, _ = p.communicate(text.encode('utf-8'))

    return out.decode('utf-8', errors='backslashreplace')
