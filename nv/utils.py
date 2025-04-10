from collections import Counter
from contextlib  import contextmanager
from functools   import wraps
import os
import re

from sublime import FORCE_GROUP, Region, View, Window, CLASS_WORD_END, CLASS_WORD_START, version, SymbolSource, SymbolType, KindId

from NeoVintageous.nv.options  import get_option
from NeoVintageous.nv.polyfill import make_all_groups_same_size, set_selection, spell_add, spell_undo
from NeoVintageous.nv.settings import get_cmdline_cwd, get_mode, get_setting, get_visual_block_direction, set_mode, set_processing_notation, set_visual_block_direction, set_xpos, get_config
from NeoVintageous.nv.vim      import DIRECTION_DOWN, DIRECTION_UP
from NeoVintageous.nv.modes    import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE
from NeoVintageous.nv.vim      import is_visual_mode, status_message

import logging
from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL
_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)
if _log.hasHandlers(): # clear existing handlers, including sublime's
    logging.getLogger(__name__).handlers.clear()
    # _log.addHandler(stream_handler)
# _L = True if _log.isEnabledFor(logging.KEY) else False


def is_view(view) -> bool:
    if not isinstance(view, View):
        return False

    settings = view.settings()

    if settings.get('is_widget', False):
        return False

    # Useful for plugins to disable NeoVintageous for specific views.
    if settings.get('__vi_external_disable', False):
        return False

    return True


def save_view(view) -> None:
    if get_setting(view, 'lsp_save'):
        # Override native save to handle LSP Code-Actions-On-Save.
        # See https://github.com/sublimelsp/LSP/issues/1725
        view.run_command('lsp_save')
    else:
        view.run_command('save', {'async': get_setting(view, 'save_async')})


def _regions_transformer(sels, view, f, with_idx, sel_old=None, sel_restore=False) -> None:
    new = []
    if   sel_old:
        _log.debug("got old regions to restore %s", sel_old)
    elif sel_restore:
        sel_old = []
        for sel in view.sel():
            sel_old.append(sel)
        _log.debug("stored old regions to restore %s", sel_old)
    for idx, sel in enumerate(sels):
        if with_idx:
            regions = f(view, sel, idx)
        else:
            regions = f(view, sel     )

        if isinstance  (  regions, Region):
            new.append (  regions)
        elif isinstance(  regions, list):
            for region in regions:
                if not isinstance(region, Region):
                    raise TypeError('region or array of region required')
                new.append(region)
        else:
            raise TypeError('region or array of region required')

    if   sel_old:
        _log.debug("sel restored to %s", sel_old)
        set_selection(view, sel_old)
    elif sel_restore:
        _log.warn("sel restore failed due to no selections")
        set_selection(view, new)
    else:
        _log.debug("no sel restore/old %s",new)
        set_selection(view, new)


def regions_transformer         (                    view, f,        sel_old=None    , sel_restore=False      ) -> None:
    _regions_transformer(         list(view.sel()) , view, f, False, sel_old=sel_old , sel_restore=sel_restore)
def regions_transformer_indexed (                    view, f,        sel_old=None    , sel_restore=False      ) -> None:
    _regions_transformer(         list(view.sel()) , view, f, True , sel_old=sel_old , sel_restore=sel_restore)
def regions_transformer_reversed(                    view, f,        sel_old=None    , sel_restore=False      ) -> None:
    _regions_transformer(reversed(list(view.sel())), view, f, False, sel_old=sel_old , sel_restore=sel_restore)


def _transform_first_non_blank(view, s) -> Region:
    return Region(next_non_blank(view, view.line(s.begin()).a))


def regions_transform_to_first_non_blank(view) -> None:
    regions_transformer(view, _transform_first_non_blank)


def regions_transform_to_normal_mode(view) -> None:
    def f(view, s):
        s.b = s.a
        return s

    regions_transformer(view, f)


def regions_transform_extend_to_line_count(view, count) -> None:
    def f(view, s):
        if count > 0:
            s.a = view.line(s.begin()).a
            s.b = view.line(view.text_point(row_at(view, s.a) + (count - 1), 0)).b

        return s

    regions_transformer(view, f)


def replace_line(view, edit, replacement: str):
    pt = next_non_blank(view, view.line(view.sel()[0].b).a)
    view.replace(edit, Region(pt, view.line(pt).b), replacement)


def get_insertion_point_at_b(region: Region) -> int:
    if region.a < region.b:
        return region.b - 1

    return region.b


def get_insertion_point_at_a(region: Region) -> int:
    if region.b < region.a:
        return region.a - 1

    return region.a


# Save selection, but only if it's not empty.
def save_previous_selection(view, mode: str) -> None:
    if view.has_non_empty_selection_region():
        view.add_regions('visual_sel', list(view.sel()))
        view.settings().set('_nv_visual_sel_mode', mode)


def get_previous_selection(view) -> tuple:
    return (view.get_regions('visual_sel'), view.settings().get('_nv_visual_sel_mode'))


def show_if_not_visible(view, pt=None) -> None:
    if isinstance(pt, Region):
        pt = pt.b
    elif pt is None and len(view.sel()) >= 1:
        # Sublime has no way to show which region in the selection is the actual
        # cursor position e.g. the selection could be a multiple cursor.
        # TODO Is there a better hueristic to find the actual cursor position?
        pt = view.sel()[0].b

    if pt and not view.visible_region().contains(pt):
        view.show(pt)


def hide_panel(window) -> None:
    window.run_command('hide_panel', {'cancel': True})


# Create a region that includes the char at a or b depending on orientation.
def new_inclusive_region(a: int, b: int) -> Region:
    if a <= b:
        return Region(a, b + 1)
    else:
        return Region(a + 1, b)


def row_at(view, pt: int) -> int:
    return view.rowcol(pt)[0]


def next_non_blank(view, pt: int) -> int:
    limit = view.size()
    substr = view.substr
    while substr(pt) in ' \t' and pt <= limit:
        pt += 1

    return pt


def prev_non_blank(view, pt: int) -> int:
    substr = view.substr
    while substr(pt) in ' \t' and pt > 0:
        pt -= 1

    return pt


def prev_blank(view, pt: int) -> int:
    substr = view.substr
    while pt >= 0 and substr(pt) not in '\t ':
        pt -= 1

    return pt


def next_blank(view, pt: int) -> int:
    limit = view.size()
    substr = view.substr
    while substr(pt) not in ' \t' and pt <= limit:
        pt += 1

    return pt


def prev_non_nl(view, pt: int) -> int:
    substr = view.substr
    while substr(pt) in '\n' and pt > 0:
        pt -= 1

    return pt


def prev_non_ws(view, pt: int) -> int:
    substr = view.substr
    while substr(pt) in ' \t\n' and pt > 0:
        pt -= 1

    return pt


def next_non_ws(view, pt: int) -> int:
    limit = view.size()
    substr = view.substr
    while substr(pt) in ' \t\n' and pt <= limit:
        pt += 1

    return pt


def last_row(view) -> int:
    return view.rowcol(view.size())[0]


def get_line_count(view: View) -> int:
    return last_row(view) + 1


def get_file_type(view: View) -> str:
    file_name = view.file_name()
    if not file_name:
        return ''

    parts = os.path.splitext(file_name)

    ext = parts[1]
    if ext and ext[0] == '.':
        ext = ext[1:]

    return ext


# Used for example by commands like f{char}, t{char}, r{char}
# TODO Refactor into nv.vi.keys module
_TRANLSATE_CHAR_MAP = {
    '<bar>': '|',
    '<bslash>': '\\',
    '<cr>': '\n',
    '<enter>': '\n',
    '<k0>': '0',
    '<k1>': '1',
    '<k2>': '2',
    '<k3>': '3',
    '<k4>': '4',
    '<k5>': '5',
    '<k6>': '6',
    '<k7>': '7',
    '<k8>': '8',
    '<k9>': '9',
    '<kdivide>': '/',
    '<kenter>': '\n',
    '<kminus>': '-',
    '<kmultiply>': '*',
    '<kperiod>': '.',
    '<kplus>': '+',
    '<lt>': '<',
    '<sp>': ' ',
    '<space>': ' ',
    '<tab>': '\t',
}


def translate_char(char: str) -> str:
    try:
        return _TRANLSATE_CHAR_MAP[char.lower()]
    except KeyError:
        return char


@contextmanager
def gluing_undo_groups(view):
    set_processing_notation(view, True)
    view.run_command('mark_undo_groups_for_gluing')

    yield

    view.run_command('glue_marked_undo_groups')
    set_processing_notation(view, False)


@contextmanager
def glue_undo_groups(view):
    view.run_command('mark_undo_groups_for_gluing')
    yield
    view.run_command('glue_marked_undo_groups')


@contextmanager
def adding_regions(view, name: str, regions: list, scope_name: str):
    view.add_regions(name, regions, scope_name)

    yield

    view.erase_regions(name)


class SelectionObserver():

    def __init__(self, view):
        self._view = view
        self._orig_sel = list(view.sel())

    def has_sel_changed(self) -> bool:
        # TODO Refactor to use Region() comparison apis
        return not (tuple((s.a, s.b) for s in self._orig_sel) == tuple((s.a, s.b) for s in tuple(self._view.sel())))

    def restore_sel(self) -> None:
        if self.has_sel_changed():
            set_selection(self._view, self._orig_sel)


@contextmanager
def sel_observer(view):
    yield SelectionObserver(view)


def sel_to_lines(view: View, s: Region, count: int) -> list:
    line = view.line(s.b)

    target_row = view.rowcol(line.a)[0] + (count - 1)
    target_line = view.line(view.text_point(target_row, 0))

    region = Region(line.a, target_line.b)

    return view.lines(region)


# This is a polyfill to work around various wrapping issues with some of
# Sublime's internal commands such as next_modification, next_misspelling, etc.
# See: https://github.com/SublimeTextIssues/Core/issues/2623.
@contextmanager
def wrapscan(view, forward: bool = True):
    # This works by comparing the postion of the cursor after the enclosed
    # operation. If wrapscan is disabled and the cursor position has "wrapped
    # around" then it's reset to the previous postion before it was wrapped.
    start = list(view.sel())

    yield

    if not get_option(view, 'wrapscan'):
        for before, after in zip(start, list(view.sel())):
            if forward:
                if after.a < before.a:
                    set_selection(view, start)
                    break
            else:
                if after.a > before.a:
                    set_selection(view, start)
                    break


def extract_file_name(view, encode_position: bool):
    sel = view.sel()[-1]

    # Expand to non-whitespace under current cursor or after the cursor.
    if sel.empty():
        begin = sel.begin()

        if view.substr(begin) == ' ':
            begin = next_non_blank(view, begin)

        sel = view.expand_by_class(
            begin,
            CLASS_WORD_START | CLASS_WORD_END,
            separators=" ")

    text = view.substr(sel)

    # For Unix the '~' character is expanded, like in "~user/file".
    # Environment variables are expanded too |expand-env|.
    text = expand_path(text)

    # Trailing punctuation characters ".,:;!" are ignored.
    text = text.rstrip('.,:;!')

    match = re.match(
        '^\\s*'
        '(?:[a-z]+\\:)?'                    # strip protocol e.g. "open:"
        '(?P<path>[a-zA-Z0-9\\.\\\\_/-]+)'  # path
        '(?:(?:\\:|@|\\()(?P<row>\\d+))?'   # row
        '(?:\\:(?P<col>\\d+))?',            # col
        text
    )

    if match:
        path = match.group('path')
        if encode_position:
            row = match.group('row')
            col = match.group('col')

            return (
                path,
                int(row) if row else row,
                int(col) if col else col
            )

        return (path, None, None)


def extract_url(view):
    _URL_REGEX = r"""(?x)
        .*(?P<url>
            https?://               # http:// or https://
            (?:www\.)?              # www.
            (?:[a-zA-Z0-9-]+\.?)+   # domain
            (?:[a-zA-Z]+)?          # tld
            (?:\:[0-9]+)?           # port
            /?[a-zA-Z0-9\-._?,!'(){}\[\]/+&@%$#=:"|~;]*     # url path
        )
    """

    def _extract_url_from_text(regex: str, text: str):
        match = re.match(regex, text)
        if match:
            url = match.group('url')

            # Remove end of line full stop character.
            url = url.rstrip('.')

            # Remove closing tag markdown link e.g. `[title](url)`.
            url = url.rstrip(')')

            # Remove closing tag markdown image e.g. `![alt](url)]`.
            # Remove trailing markdown punctuation e.g. ): int [title](url):
            if url[-2:] in (')]', '):'):
                url = url[:-2]

            # Remove trailing quote marks e.g. `"url"`, `'url'`.
            url = url.rstrip('"\'')

            # Remove trailing quote-comma marks e.g. ", and ,'
            if url[-2:] in ('",', '\','):
                url = url[:-2]

            return url

        return None

    sel = view.sel()[0]
    line = view.line(sel)
    text = view.substr(line)

    return _extract_url_from_text(_URL_REGEX, text)


def get_string_under_cursor(view) -> str:
    return view.substr(view.word(view.sel()[0].end()))


def extract_word(view, mode: str, sel) -> str:
    if is_visual_mode(mode):
        word = view.substr(sel)
    else:
        word = view.substr(view.word(sel))

    return word


# Tries to workaround some of the Sublime Text issues where the cursor caret is
# positioned, off-by-one, at the end of line i.e. the caret positions itself at
# >>>eol| |<<< instead of >>>eo|l|<<<. In some cases, the cursor positions
# itself at >>>eol| |<<<, and then a second later,  moves to the correct
# position >>>eo|l|<<< e.g. a left mouse click after the end of a line. Some of
# these issues can't be worked-around e.g. the mouse click issue described
# above. See https://github.com/SublimeTextIssues/Core/issues/2121.
def fix_eol_cursor(view, mode: str) -> None:
    ignore_nl = get_config('edit.move_left_on_insert_exit') == True
    if mode in (NORMAL, INTERNAL_NORMAL) and ignore_nl:
        def f(view, s):
            b = s.b

            if ((view.substr(b) == '\n' or b == view.size()) and not view.line(b).empty()):
                return Region(b - 1)

            return s

        regions_transformer(view, f)


def highlow_visible_rows(view,count=0) -> tuple:
    visible_region      = view.visible_region()
    highest_visible_row = view.rowcol(visible_region.a    )[0] + count
    lowest_visible_row  = view.rowcol(visible_region.b - 1)[0] - count

    # To avoid scrolling when we move to the highest visible row, we need to check if the row is fully visible or only partially visible. If the row is only partially visible we will move to next one.
    line_height     = view.line_height      ()
    view_position   = view.viewport_position()
    viewport_extent = view.viewport_extent  ()

    # The extent y position needs an additional "1.0" to its height. It's not clear why Sublime needs to add it, but it always adds it.
    highest_position = (highest_visible_row * line_height) + 1.0
    if  highest_position < view_position[1]:
        highest_visible_row += 1

    lowest_position = ((lowest_visible_row + 1) * line_height) + 1.0
    if  lowest_position > (view_position[1] + viewport_extent[1]):
        lowest_visible_row -= 1

    context_lines = get_option(view, 'scrolloff')

    return (highest_visible_row + context_lines, lowest_visible_row - context_lines)


def highest_visible_pt(view, count=0) -> int:
    return view.text_point(highlow_visible_rows(view,count)[0], 0)
def lowest_visible_pt (view, count=0) -> int:
    return view.text_point(highlow_visible_rows(view,count)[1], 0)


# Note: the edit object is required for this to work properly
def scroll_horizontally(view, edit, amount, half_screen: bool = False) -> None:
    if view.settings().get('word_wrap'):
        return

    if half_screen:
        half_extent = view.viewport_extent()[0] / 2
        half_extent_amount = int(half_extent / view.em_width())
        amount = half_extent_amount * int(amount)

    position = view.viewport_position()
    delta = int(amount) * view.em_width()
    pos_x = (position[0] - (position[0] % view.em_width())) + delta
    if pos_x < 0:
        pos_x = 0

    view.set_viewport_position((pos_x, position[1]))


def scroll_viewport_position(view, number_of_scroll_lines: int, forward: bool = True) -> None:
    x, y = view.viewport_position()

    y_addend = ((number_of_scroll_lines) * view.line_height())

    if forward:
        viewport_position = (x, y + y_addend)
    else:
        viewport_position = (x, y - y_addend)

    view.set_viewport_position(viewport_position)


def get_option_scroll(view) -> int:
    # Number of lines to scroll with CTRL-U and CTRL-D commands. Will be set to
    # half the number of lines in the window when the window size changes. If
    # you give a count to the CTRL-U or CTRL-D command it will be used as the
    # new value for 'scroll'.
    line_height = view.line_height()
    viewport_extent = view.viewport_extent()
    line_count = viewport_extent[1] / line_height
    number_of_scroll_lines = line_count / 2

    return int(number_of_scroll_lines)


def _get_scroll_target(view, number_of_scroll_lines: int, forward: bool = True):
    s = view.sel()[0]

    if forward:
        if s.b > s.a and view.substr(s.b - 1) == '\n':
            sel_row, sel_col = view.rowcol(s.b - 1)
        else:
            sel_row, sel_col = view.rowcol(s.b)

        target_row = sel_row + number_of_scroll_lines

        # Ignore the last line if it's a blank line. In Sublime the last
        # character is a NULL character point ('\x00'). We don't need to check
        # that it's NULL, just backup one point and retrieve that row and col.
        last_line_row, last_line_col = view.rowcol(view.size() - 1)

        # Ensure the target does not overflow the bottom of the buffer.
        if target_row >= last_line_row:
            target_row = last_line_row
    else:
        if s.b > s.a and view.substr(s.b - 1) == '\n':
            sel_row, sel_col = view.rowcol(s.b - 1)
        else:
            sel_row, sel_col = view.rowcol(s.b)

        target_row = sel_row - number_of_scroll_lines

        # Ensure the target does not overflow the top of the buffer.
        if target_row <= 0:
            target_row = 0

    # Return nothing to indicate there no need to scroll.
    if sel_row == target_row:
        return

    target_pt = next_non_blank(view, view.text_point(target_row, 0))

    return target_pt


def get_scroll_up_target_pt(view, number_of_scroll_lines: int):
    return _get_scroll_target(view, number_of_scroll_lines, forward=False)


def get_scroll_down_target_pt(view, number_of_scroll_lines: int):
    return _get_scroll_target(view, number_of_scroll_lines, forward=True)


def resolve_normal_target(s: Region, target: int) -> None:
    s.a = s.b = target


def resolve_visual_target(s: Region, target: int) -> None:
    if s.a < s.b:               # A --> B
        if target < s.a:        # TARGET < A --> B
            s.a += 1
            s.b = target
        else:
            s.b = target + 1
    elif s.a > s.b:             # B <-- A
        if target >= s.a:       # B <-- A <= TARGET
            s.a -= 1
            s.b = target + 1
        else:
            s.b = target
    else:                       # A === B

        # If A and B are equal, it means the Visual selection is not "well
        # formed". Instead of raising an error, or not resolving the selection,
        # the selection is coerced to be "well formed" and then resolved.

        if target == s.b:       # B === TARGET
            s.b = target + 1
        else:
            s.b = target


def resolve_visual_line_target(view, s: Region, target: int) -> None:
    if s.a < s.b:                               # A --> B
        if target < s.a:                        # TARGET < A --> B
            s.a = view.full_line(s.a).b
            s.b = view.line(target).a
        elif target > s.a:
            s.b = view.full_line(target).b
        elif target == s.a:
            s.b = s.a
            s.a = view.full_line(target).b
    elif s.a > s.b:                             # B <-- A
        if target > s.a:                        # B <-- A < TARGET
            s.a = view.line(s.a - 1).a
            s.b = view.full_line(target).b
        elif target < s.a:                      # TARGET < B <-- TARGET < A
            s.b = view.line(target).a
        elif target == s.a:                     # A === TARGET
            s.a = view.line(s.a - 1).a
            s.b = view.full_line(target).b
    elif s.a == s.b:                            # A === B

        # If A and B are equal, it means the Visual selection is not "well
        # formed". Instead of raising an error, or not resolving the selection,
        # the selection is coerced to be "well formed" and then resolved.

        if target > s.a:
            s.a = view.line(s.a).a
            s.b = view.full_line(target).b
        elif target < s.a:
            s.a = view.full_line(s.a).b
            s.b = view.line(target).a
        elif target == s.a:
            s.a = view.line(target).a
            s.b = view.full_line(target).b


def resolve_internal_normal_target(view, s: Region, target: int, linewise: bool = None, inclusive: bool = None) -> None:
    # An Internal Normal resolver may have modifiers such as linewise,
    # inclusive, exclusive, etc. Modifiers determine how the selection, relative
    # to the target should be resolved.

    # XXX Should modifiers be a bitwise options param rather than indivisual
    # params? This can be easily refactored later!
    # * For the moment, ensure at least one modifier is specified!
    # * For the moment, modifier can only be used individually!
    if linewise is None and inclusive is None:
        raise NotImplementedError()
    if linewise is not None and inclusive is not None:
        raise NotImplementedError()

    if linewise:
        resolve_visual_target(s, target)

        if s.b >= s.a:
            s.a = view.line(s.a).a
            s.b = view.full_line(s.b).b
        else:
            s.b = view.line(s.b).a
            s.a = view.full_line(s.a).b

    if inclusive:
        s.b = target

        if s.b >= s.a:
            s.b += 1
        else:
            s.a += 1


class VisualBlockSelection():

    # There are two "pivot" points: the direction of the Visual block, and the
    # direction of selections (forward/reverse) within the Visual block.
    #
    # The reason for selections "within" the Visual block, is because Sublime
    # doesn't support real block selections, to work around that limitation,
    # normal selections grouped together are used to emulate a block selection.
    #
    # The direction of the Visual block is indicated as DOWN or UP.
    #
    # The "pivot" for the direction of the selections is the column at point A.
    # Point B determines if the selections are REVERSED or FORWARD, if point B
    # is to the LEFT of COL-A, then the selections are REVERSED, otherwise not.
    #
    # Here are some examples:
    #
    # (when the number of lines is equal to one, then ab==b and a==ba)
    #
    # Visual block is DOWN and contains FORWARD selections:
    #
    #   a     DOWN FORWARD  a----ab
    #    \                  |     |
    #     \                 | --> |
    #      \                |     |
    #       b               ba----b
    #
    # Visual block is DOWN and contains REVERSED selections:
    #
    #       a DOWN REVERSE  ab----a
    #      /                |     |
    #     /                 | <-- |
    #    /                  |     |
    #   b                   b----ba
    #
    # Visual block is UP and contains FORWARD selections:
    #
    #       b UP FORWARD    ba----b
    #      /                |     |
    #     /                 | --> |
    #    /                  |     |
    #   a                   a----ab
    #
    # Visual block is UP and contains REVERSED selections:
    #
    #   b     UP REVERSE    b----ba
    #    \                  |     |
    #     \                 | <-- |
    #      \                |     |
    #       a               ab----a

    def __init__(self, view, direction=DIRECTION_DOWN):
        self.view = view
        self._set_direction(get_visual_block_direction(view, direction))

    def _set_direction(self, direction: int) -> None:
        set_visual_block_direction(self.view, direction)
        self._direction = direction

    def _a(self) -> Region:
        index = 0 if self.is_direction_down() else -1
        return self.view.sel()[index]

    def _b(self) -> Region:
        index = -1 if self.is_direction_down() else 0
        return self.view.sel()[index]

    def begin(self) -> int:
        a = self._a()
        b = self._b()

        if a < b:
            begin = a.begin()
        else:
            begin = b.begin()

        return begin

    def end(self) -> int:
        a = self._a()
        b = self._b()

        if a < b:
            end = b.end()
        else:
            end = a.end()

        return end

    @property
    def a(self) -> int:
        return self._a().a

    @property
    def ab(self) -> int:
        return self._a().b

    @property
    def b(self) -> int:
        return self._b().b

    @property
    def ba(self) -> int:
        return self._b().a

    def rowcolb(self) -> tuple:
        return self.view.rowcol(self.insertion_point_b())

    def to_visual(self) -> Region:
        if self.is_direction_down():
            a = self.begin()
            b = self.end()
        else:
            a = self.end()
            b = self.begin()

        return Region(a, b)

    def to_visual_line(self) -> Region:
        a = self.view.full_line(self.begin()).a
        b = self.view.full_line(self.end()).b

        return Region(a, b)

    def insertion_point_b(self) -> int:
        b = self.b
        ba = self.ba

        return b - 1 if b > ba else b

    def insertion_point_a(self) -> int:
        a = self.a
        ab = self.ab

        return a - 1 if a > ab else a

    def sel_b(self) -> Region:
        return self.view.sel()[-1] if self.b > self.a else self.view.sel()[0]

    def _is_direction(self, direction: int) -> bool:
        return self._direction == direction

    def is_direction_down(self) -> bool:
        return self._is_direction(DIRECTION_DOWN)

    def is_direction_up(self) -> bool:
        return self._is_direction(DIRECTION_UP)

    def resolve_target(self, target: int) -> list:
        # When the TARGET is to the RIGHT of COL-A, then the Visual block will
        # have FORWARD selections. When the TARGET is to the LEFT of COL-A, then
        # the Visual block will have REVERSED selections.
        #
        # When the TARGET is to the LEFT of COL-A, the new Visual block will
        # have REVERSED selections, when it's to the RIGHT of COL-A, the new
        # Visual block will have FORWARD selections.
        #
        # When the TARGET is on the same side as the current column COL-B (the
        # TARGET is changing point B, and thus COL-B), then the direction of the
        # selections is inverted, for example:
        #
        #          a DOWN REVERSE
        #         /|
        #        / |
        #       /  |
        #      b   |
        #          |
        #          | T

        a = self.a
        ab = self.ab

        begin = self.begin()
        end = self.end()

        col_a = self.view.rowcol(a - 1 if a > ab else a)[1]
        col_t = self.view.rowcol(target)[1]

        is_direction_down = self.is_direction_down()

        block = []

        if is_direction_down:
            if target >= begin:
                lines = self.view.lines(Region(begin, target + 1))
            else:
                lines = self.view.lines(Region(a + 1, target))
        else:
            if target >= end:
                lines = self.view.lines(Region(a, target + 1))
            else:
                lines = self.view.lines(Region(a + 1, target))

        if col_t >= col_a:
            for line in lines:
                # If the line size is less than COL-A (selection direction
                # "pivot" point), the line is ommited from FORWARD Visual block.
                if line.size() >= col_a:
                    new_line = Region(
                        min(line.a + col_a, line.b + 1),
                        min(line.a + col_t + 1, line.b + 1)
                    )

                    block.append(new_line)
        else:
            for line in lines:
                # If the line size is less than COL-T, in a REVERSE selection,
                # then the line is omitted from a REVERSE Visual block.
                if line.size() >= col_t:
                    new_line = Region(
                        min(line.a + col_a + 1, line.b + 1),
                        min(line.a + col_t, line.b + 1)
                    )

                    block.append(new_line)

        if is_direction_down:
            if target < begin:
                self._set_direction(DIRECTION_UP)
        else:
            if target >= end:
                self._set_direction(DIRECTION_DOWN)

        return block

    def transform_target(self, target: int) -> None:
        visual_block = self.resolve_target(target)
        if visual_block:
            set_selection(self.view, visual_block)

    # Reduce to single point at beginning of visual block.
    def reduce_to_begin(self):
        begin = self.begin()
        self.view.sel().clear()
        self.view.sel().add(Region(begin, begin + 1))

    def transform_reverse(self):
        sels = list(self.view.sel())
        self.view.sel().clear()
        for sel in sels:
            b = sel.a
            sel.a = sel.b
            sel.b = b
            self.view.sel().add(sel)

    def transform_to_other_end(self, same_line: bool = False):
        if not same_line:
            self._set_direction(
                DIRECTION_UP
                if self.is_direction_down()
                else DIRECTION_DOWN)
        self.transform_reverse()

    def _transform(self, region: Region) -> None:
        set_selection(self.view, region)

    def transform_to_visual(self) -> None:
        self._transform(self.to_visual())

    def transform_to_visual_line(self) -> None:
        self._transform(self.to_visual_line())

    @staticmethod
    def create(view):
        sels = list(view.sel())
        sel = sels[0]

        target = get_insertion_point_at_b(sel)

        direction = DIRECTION_DOWN if sel.b >= sel.a else DIRECTION_UP
        vb = VisualBlockSelection(view, direction)
        vb.transform_target(target)

        return vb


def resolve_visual_block_target(view, target, count: int = 1, nosep:bool=False) -> None:
    visual_block = VisualBlockSelection(view)

    if not isinstance(target, int):
        if nosep:
            target = target(view, visual_block.insertion_point_b(), count, nosep=nosep)
        else:
            target = target(view, visual_block.insertion_point_b(), count)

    visual_block.transform_target(target)


def resolve_visual_block_begin(view) -> None:
    VisualBlockSelection(view).reduce_to_begin()


def resolve_visual_block_reverse(view) -> None:
    VisualBlockSelection(view).transform_reverse()


def get_visual_block_sel_b(view):
    return VisualBlockSelection(view).sel_b()


class InputParser():

    IMMEDIATE = 1
    PANEL = 2
    AFTER_MOTION = 3

    def __init__(self, type: int = None, command=None, param=None):
        self._type = type
        self._command = command
        self._param = param

    def is_after_motion(self) -> bool:
        return self._type == self.AFTER_MOTION

    def is_immediate(self) -> bool:
        return self._type == self.IMMEDIATE

    def is_panel(self) -> bool:
        return self._type == self.PANEL

    def is_interactive(self) -> bool:
        return self.is_panel() and bool(self._command)

    def run_command(self, window) -> None:
        window.run_command(self._command)

    def run_interactive_command(self, window, value) -> None:
        window.run_command(self._command, {self._param: value})


def folded_rows(view, pt: int) -> int:
    folds = view.folded_regions()
    try:
        fold = [f for f in folds if f.contains(pt)][0]
        fold_row_a = view.rowcol(fold.a)[0]
        fold_row_b = view.rowcol(fold.b - 1)[0]
        # Return no. of hidden lines.
        return fold_row_b - fold_row_a
    except IndexError:
        return 0


def _clear_visual_selection(view) -> None:
    sels = []
    for sel in view.sel():
        sels.append(view.text_point(view.rowcol(sel.begin())[0], 0))

    if sels:
        set_selection(view, sels)


def fold(view) -> None:
    view.run_command('fold')
    _clear_visual_selection(view)


def unfold(view) -> None:
    # Sublime's "unfold" command doesn't unfold when a fold is at the end of the
    # line, so we need to call unfold directly with the full line region.
    if any([s.empty() for s in view.sel()]):
        for sel in view.sel():
            view.unfold(view.full_line(sel))
    else:
        view.run_command('unfold')
    _clear_visual_selection(view)


def fold_all(view) -> None:
    view.run_command('fold_all')


def unfold_all(view) -> None:
    view.run_command('unfold_all')


# FIXME If we have two contiguous folds, this method will fail. Handle folded regions
def previous_non_folded_pt(view, pt: int) -> int:
    folds = view.folded_regions()
    try:
        fold = [f for f in folds if f.contains(pt)][0]
        non_folded_row = view.rowcol(fold.a - 1)[0]
        pt = view.text_point(non_folded_row, 0)
    except IndexError:
        pass

    return pt


# FIXME: If we have two contiguous folds, this method will fail. Handle folded regions
def next_non_folded_pt(view, pt: int) -> int:
    folds = view.folded_regions()
    try:
        fold = [f for f in folds if f.contains(pt)][0]
        non_folded_row = view.rowcol(view.full_line(fold.b).b)[0]
        pt = view.text_point(non_folded_row, 0)
    except IndexError:
        pass

    return pt


def calculate_xpos(view, start: int, xpos: int) -> tuple:
    if view.line(start).empty():
        return start, 0

    size = view.settings().get('tab_size')
    eol = view.line(start).b - 1
    pt = 0
    chars = 0
    while (pt < xpos):
        if view.substr(start + chars) == '\t':
            pt += size
        else:
            pt += 1

        chars += 1

    pt = min(eol, start + chars)

    return (pt, chars)


def spell_file_add_word(view, mode, count: int) -> None:
    for s in view.sel():
        spell_add(view, extract_word(view, mode, s))


def spell_file_remove_word(view, mode, count: int) -> None:
    for s in view.sel():
        spell_undo(extract_word(view, mode, s))


def fixup_eof(view, pt: int) -> int:
    if ((pt == view.size()) and (not view.line(pt).empty())):
        pt = prev_non_nl(view, pt - 1)

    return pt


# A temporary hack because *most*, and maybe all, motions shouldn't move the
# cursor after an operation, but changing it for all commands could cause some
# regressions. TODO When enough commands are updated, this should be removed.
def should_motion_apply_op_transformer(motion) -> bool:
    if motion['motion'] == 'nv_vi_select_text_object':
        if 'text_object' in motion['motion_args']:
            if motion['motion_args']['text_object'] in '"\'/_t,.;:+-=~*#\\&$|':
                return False

    blacklist = (
        'nv_vi_move_column',
        'nv_vi_dollar',
        'nv_vi_find_in_line',
        'nv_vi_move_to_soft_eol',
        'nv_vi_move_char_left','nv_vi_move_char_right',
        'nv_vi_move_to_bol',
    )

    return motion and 'motion' in motion and motion['motion'] not in blacklist


# Some motions should be treated as linewise operations by registers, for
# example, some text objects are linewise, but only if they contain a newline.
def is_linewise_operation(mode: str, motion):
    if mode == VISUAL_LINE:
        return True

    if motion:
        if 'motion' in motion:
            motion_name = motion.get('motion', '')
            motion_args = motion.get('motion_args', [])

            if 'text_object' in motion_args:
                if motion_args['text_object'] in '[]()b<>t{}B%`/?nNp':
                    return 'maybe'

            if motion_name in ('nv_vi_move_line_down', 'nv_vi_move_line_up'):
                return 'maybe'

    return False


def update_xpos(view) -> None:
    try:
        sel = view.sel()[0]
        pos = sel.b
        if not sel.empty():
            if sel.a < sel.b:
                pos -= 1

        counter = Counter(view.substr(Region(view.line(pos).a, pos)))  # type: dict
        tab_size = view.settings().get('tab_size')
        xpos = view.rowcol(pos)[1] + ((counter['\t'] * tab_size) - counter['\t'])
    except Exception:
        # TODO [review] exception handling
        xpos = 0

    set_xpos(view, xpos)


def get_visual_repeat_data(view, mode: str):
    # Return the data needed to restore visual selections.
    #
    # Before repeating a visual mode command in normal mode.
    #
    # Returns:
    #   None
    #   3-tuple (lines, chars, mode)
    if mode not in (VISUAL, VISUAL_LINE):
        return

    first = view.sel()[0]
    lines = (row_at(view, first.end()) -
             row_at(view, first.begin()))

    if lines > 0:
        chars = view.rowcol(first.end())[1]
    else:
        chars = first.size()

    return (lines, chars, mode)


def restore_visual_repeat_data(view, mode: str, data: tuple) -> None:
    rows, chars, old_mode = data
    first = view.sel()[0]

    if old_mode == VISUAL:
        if rows > 0:
            end = view.text_point(row_at(view, first.b) + rows, chars)
        else:
            end = first.b + chars

        view.sel().add(Region(first.b, end))
        set_mode(view, VISUAL)

    elif old_mode == VISUAL_LINE:
        rows, _, old_mode = data
        begin = view.line(first.b).a
        end = view.text_point(row_at(view, begin) + (rows - 1), 0)
        end = view.full_line(end).b
        view.sel().add(Region(begin, end))
        set_mode(view, VISUAL_LINE)


def is_help_view(view) -> bool:
    return (view and
            view.is_read_only() and
            view.is_scratch() and
            '[vim help]' in view.name() and
            view.score_selector(0, 'text.neovintageous.help') > 0)


def view_count_excluding_help_views(window) -> int:
    count = 0
    for view in window.views():
        if not is_help_view(view):
            count += 1

    return count


def requires_motion(motion) -> None:
    if motion is None:
        raise ValueError('motion data required')


def find_next_num(view) -> list:
    regions = list(view.sel())

    # Modify selections that are inside a number already.
    for i, r in enumerate(regions):
        a = r.b

        while view.substr(a).isdigit():
            a -= 1

        if a != r.b:
            a += 1

        regions[i] = Region(a)

    lines = [view.substr(Region(r.b, view.line(r.b).b)) for r in regions]
    number_pattern = re.compile('\\d')
    matches = [number_pattern.search(text) for text in lines]
    if all(matches):
        return [(reg.b + ma.start()) for (reg, ma) in zip(regions, matches)]  # type: ignore[union-attr]

    return []


def find_symbol(view, r, globally=False):
    query = view.substr(view.word(r))
    fname = view.file_name()
    if not fname:
        return

    if int(version()) >= 4050: # find all locations where symbol sym is located
        locations = view.window().symbol_locations(sym=query
            , source     =SymbolSource.ANY # ANY|INDEX|OPEN_FILES Sources which should be searched for symbol
            , type       =SymbolType  .ANY # ANY|DEFINITION|REFERENCE type of symbol to find
            , kind_id    =KindId.AMBIGUOUS # KindId of symbol AMBIGUOUS|KEYWORD|TYPE|FUNCTION|NAMESPACE|NAVIGATION|MARKUP|VARIABLE|SNIPPET|COLOR_REDISH|COLOR_ORANGISH|COLOR_YELLOWISH|COLOR_GREENISH|COLOR_CYANISH|COLOR_BLUISH|COLOR_PURPLISH|COLOR_PINKISH|COLOR_DARK|COLOR_LIGHT|
            , kind_letter=''               # letter representing the kind of the symbol. See Kind
        ) # Contains information about a file that contains a symbol
        # path          : str           filesystem       path to the file containing the symbol
        # display_name  : str           project-relative path to the file containing the symbol
        # row           : int           row    of the file     the symbol is contained on
        # col           : int           column of the row that the symbol is contained on
        # syntax        : str           name of the syntax for the symbol
        # type          : SymbolType    type of the                symbol. See SymbolType
        # kind          : Kind          kind of the                symbol. See Kind
    else: # ↓ deprecated
        locations = view.window().lookup_symbol_in_index(query)
    if not locations:
        return

    try:
        if not globally:
            if int(version()) >= 4050:
                for hit in locations:
                    if fname.endswith(hit.path):
                        return hit.row - 1, hit.col - 1
            else:
                fname = fname.replace('\\', '/')
                location = [hit[2] for hit in locations if fname.endswith(hit[1])][0]
                return location[0] - 1, location[1] - 1
        else: # TODO: There might be many symbols with the same name.
            return locations[0]
    except IndexError:
        return


def expand_path(path: str) -> str:
    expanded = os.path.expanduser(path)
    expanded = os.path.expandvars(expanded)

    return expanded


def expand_to_realpath(path: str) -> str:
    return os.path.realpath(expand_path(path))


def current_working_directory(f, *args, **kwargs):
    @wraps(f)
    def init(*args, **kwargs) -> None:
        try:
            original = os.getcwd()
            cwd = get_cmdline_cwd()
            if cwd and os.path.isdir(cwd):
                os.chdir(cwd)
            f(*args, **kwargs)
        finally:
            if original:
                os.chdir(original)
    return init


@current_working_directory
def open_file(window: Window, file: str) -> None:
    file = expand_path(file)
    if not os.path.isabs(file):
        file = os.path.join(os.getcwd(), file)

    window.open_file(file, FORCE_GROUP)


def create_pane(window, direction: str, file: str = None) -> None:
    # Uses Origami command.
    window.run_command('create_pane', {'direction': direction, 'give_focus': True})
    if file:
        open_file(window, file)
    _maybe_equalalways(window)


def clone_file(window, direction: str) -> None:
    window.run_command('clone_file_to_pane', {'direction': direction})
    _maybe_equalalways(window)


def _maybe_equalalways(window) -> None:
    view = window.active_view()
    if view and get_option(view, 'equalalways'):
        make_all_groups_same_size(window)


def is_insert_mode(view, mode: str = None) -> bool:
    return _resolve_mode(view, mode) == INSERT


def is_not_insert_mode(view, mode: str = None) -> bool:
    return _resolve_mode(view, mode) != INSERT


def _resolve_mode(view, mode: str = None) -> str:
    if mode is None:
        return get_mode(view)

    return mode


def adjust_selection_if_first_non_blank(view, mode: str, first_non_blank: bool, selection: Region) -> None:
    if first_non_blank and mode in (NORMAL, INTERNAL_NORMAL):
        row = view.rowcol(selection.b)[0]
        first_non_blank_pt = next_non_blank(view, view.text_point(row, 0))
        set_selection(view, first_non_blank_pt)


def get_indentation(view, level: int) -> str:
    translate = view.settings().get('translate_tabs_to_spaces')
    tab_size = int(view.settings().get('tab_size'))
    tab_text = ' ' * tab_size if translate else '\t'

    return tab_text * level


def show_ascii(view) -> None:
    def _char_to_notation(char: str) -> str:
        # Convert a char to a key notation. Uses vim key notation.
        # See https://vimhelp.appspot.com/intro.txt.html#key-notation
        char_notation_map = {
            '\0': "Nul",
            ' ': "Space",
            '\t': "Tab",
            '\n': "NL"
        }

        if char in char_notation_map:
            char = char_notation_map[char]

        return "<" + char + ">"

    region = view.sel()[-1]
    c_str = view.substr(get_insertion_point_at_b(region))
    c_ord = ord(c_str)
    c_hex = hex(c_ord)
    c_oct = oct(c_ord)
    c_not = _char_to_notation(c_str)
    status_message('%7s %3s %4s %5s' % (c_not, c_ord, c_hex, c_oct))

def build_shell_cmd(view, cmd: str):
    builder = [get_option(view, 'shell')]
    builder.extend(get_option(view, 'shellcmdflag').split())
    builder.append(cmd)

    return builder
