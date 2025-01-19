from collections import OrderedDict
from string import ascii_letters, ascii_lowercase

from sublime import HIDDEN, PERSISTENT, Region

from NeoVintageous.nv.jumplist import jumplist_back
from NeoVintageous.nv.session  import get_session_value
from NeoVintageous.nv.settings import get_setting
from NeoVintageous.nv.utils    import get_insertion_point_at_b
from NeoVintageous.nv          import cfg as nvcfg

from NeoVintageous.nv.rc import cfgU

import logging
from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL
_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)
if _log.hasHandlers(): # clear existing handlers, including sublime's
    logging.getLogger(__name__).handlers.clear()
    # _log.addHandler(stream_handler)
# _L = True if _log.isEnabledFor(logging.KEY) else False


DEF = {
    'back' : ['\'','`']
    }
import copy
CFG =  copy.deepcopy(DEF) # copy defaults to be able to reset values on config reload


def reload_with_user_data_kdl() -> None:
    global CFG
    if hasattr(cfgU,'kdl') and (cfg := cfgU.kdl.get('mark',None)): # skip on initial import when Plugin API isn't ready, so no settings are loaded
        _log.debug("@marks: Parsing config")
        for node in cfg.nodes: # back "'" "`"
            tag_val = node.name
            tag = tag_val.tag   if hasattr(tag_val,'tag'  ) else ''
            val = tag_val.value if hasattr(tag_val,'value') else tag_val
            cfg_key = val
            if tag:
                _log.warn("node ‘%s’ has unrecognized tag, skipping",node.name)
                continue
            if cfg_key == 'back': # "'" "`"
                CFG['back'] = list() # reset defaults
                nargs = node.getArgs((...,...)) if nvcfg.KDLV == 2 else node.args
                for arg in nargs:     # Parse arguments
                    tag = arg.tag   if hasattr(arg,'tag'  ) else ''
                    val = arg.value if hasattr(arg,'value') else arg
                    # if tag:
                        # _log.debug("node ‘%s’ has unrecognized tag in argument %s",node.name,arg)
                    if not isinstance(val, str):
                        _log.warn("node ‘%s’ has unrecognized argument ‘%s’, expected a string, not ‘%s’",node.name,arg,type(val))
                        continue
                    if len(val) > 1:
                        _log.warn("node ‘%s’ has unrecognized argument ‘%s’, expected a single symbol, got length ‘%s’",node.name,arg,len(val))
                        continue
                    CFG['back'].append(val)
            else:
                _log.warn("node ‘%s’ has unrecognized name, skipping",node.name)
                continue
    else:
        CFG = copy.deepcopy(DEF) # copy defaults to be able to reset values on config reload


def set_mark(view, name: str) -> None:
    if not _is_writable(name):
        raise KeyError()
    if name.isupper():
        if not view.file_name():
            return

        _get_file_name_marks()[name] = view.file_name()

    regions = [Region(get_insertion_point_at_b(view.sel()[0]))]

    view.add_regions(
        _get_key(name),
        regions,
        flags=HIDDEN | PERSISTENT,
        scope='region.cyanish neovintageous.mark',
        icon=_get_icon(view, name))


def get_mark(view, name: str):
    if not _is_readable(name):
        raise KeyError()

    if name in CFG['back']:
        marks_view, marks = jumplist_back(view)
        if len(marks) > 0:
            if marks_view != view:
                return marks_view, marks[0]
            else:
                return             marks[0]
    else:
        if name.isupper():
            view = _get_uppercase_mark_view(view, name)
            if not view:
                return

        marks = _get_regions(view, name)
        if marks:
            if name.isupper():
                return view, marks[0]
            else:
                return       marks[0]


def get_marks(view) -> OrderedDict:
    marks = OrderedDict()
    for name in ascii_letters:
        mark = get_mark(view, name)
        if mark is None:
            continue

        if isinstance(mark, tuple):
            view, mark = mark

        marks[name] = _get_mark_info(view, mark)

    return marks


def del_mark(view, name: str) -> None:
    if name.isupper():
        view = _get_uppercase_mark_view(view, name)

        try:
            del _get_file_name_marks()[name]
        except KeyError:
            pass

    if view:
        view.erase_regions(_get_key(name))


def del_marks(view) -> None:
    for mark in ascii_lowercase:
        del_mark(view, mark)


def _get_mark_info(view, region: Region) -> dict:
    line_number, col = view.rowcol(region.b)
    line_number += 1

    if view.file_name():
        file_or_text = view.file_name()
    else:
        file_or_text = view.substr(view.line(region.b))

    return {
        'line_number': line_number,
        'col': col,
        'file_or_text': file_or_text
    }


def _is_writable(name: str) -> bool:
    return name in ascii_letters


def _is_readable(name: str) -> bool:
    return name in ascii_letters + '\'`'


def _get_key(name: str) -> str:
    return '_nv_mark' + name


def _get_regions(view, name: str) -> list:
    return view.get_regions(_get_key(name))


def _get_file_name_marks() -> dict:
    return get_session_value('marks', {})


def _get_uppercase_mark_view(view, name: str):
    try:
        file_name = _get_file_name_marks()[name]
    except KeyError:
        return

    window = view.window()
    if not window:
        return

    return window.find_open_file(file_name)


def _get_icon(view, name: str) -> str:
    if not get_setting(view, 'show_marks_in_gutter'):
        return ''

    return 'Packages/NeoVintageous/res/icons/%s_%s.png' % (
        'lower' if name.islower() else 'upper',
        name.lower())
