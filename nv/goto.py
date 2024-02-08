import re

from sublime import LITERAL
from sublime import Region
from sublime import find_resources
from sublime import load_resource
from sublime import version

from NeoVintageous.nv.jumplist        import jumplist_updater
from NeoVintageous.nv.marks           import get_mark
from NeoVintageous.nv.polyfill        import set_selection, view_find
from NeoVintageous.nv.ui              import ui_bell
from NeoVintageous.nv.utils           import next_non_blank, regions_transform_to_normal_mode, regions_transformer, resolve_normal_target, resolve_visual_block_target, resolve_visual_line_target, resolve_visual_target, show_if_not_visible, wrapscan
from NeoVintageous.nv.vi.text_objects import find_next_lone_bracket, find_prev_lone_bracket
from NeoVintageous.nv.vim             import EOF
from NeoVintageous.nv.modes           import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE
from NeoVintageous.nv.vim             import enter_normal_mode, status_message


def goto_help(view) -> None:
    if not view or not view.sel():
        raise ValueError('view selection is required')

    sel = view.sel()[0]

    score = view.score_selector(sel.b, 'text.neovintageous jumptag')

    # TODO goto to help for any word in a help file. See :h bar Anyway, you can
    # use CTRL-] on any word, also when it is not within |, and Vim will try to
    # find help for it.  Especially for options in single quotes, e.g.
    # 'compatible'.

    if score == 0:
        return

    subject = view.substr(view.extract_scope(sel.b))
    if not subject:
        return

    if len(subject) > 50:
        return status_message('E149: Sorry, no help found')

    goto_help_subject(view.window(), subject)


# TODO Refactor into common cache module
_help_tags_cache = {}  # type: dict


def goto_help_subject(window, subject: str = None) -> None:
    if not subject:
        subject = 'help.txt'

    if not _help_tags_cache:
        tags_matcher = re.compile('^([^\\s]+)\\s+([^\\s]+)\\s+(.+)$')
        for line in load_resource('Packages/NeoVintageous/res/doc/tags').split('\n'):
            if line:
                match = tags_matcher.match(line)
                if match:
                    _help_tags_cache[match.group(1)] = (match.group(2), match.group(3))

    subject = subject.rstrip()

    # Recognize a few exceptions e.g. some strings that contain '*'
    # with "star", "|" with "bar" and '"' with "quote".
    subject_replacements = {
        "*": "star",
        "g*": "gstar",
        "[*": "[star",
        "]*": "]star",
        "/*": "/star",
        "/\\*": "/\\star",
        "\"*": "quotestar",
        "**": "starstar",
        "/|": "/bar",
        "/\\|": "/\\bar",
        '|': 'bar',
        '"': 'quote'
    }

    try:
        subject = subject_replacements[subject]
    except KeyError:
        pass

    if subject not in _help_tags_cache:

        # Basic hueristic to find nearest relevant help e.g. `help ctrl-k` will
        # look for "ctrl-k", "c_ctrl-k", "i_ctrl-k", etc. Another example is
        # `:help copy` will look for "copy" then ":copy". Also checks lowercase
        # variants e.g. ctrl-k", "c_ctrl-k, etc., and uppercase variants e.g.
        # CTRL-K", "C_CTRL-K, etc.

        subject_candidates = [subject]

        if subject.lower() not in subject_candidates:
            subject_candidates.append(subject.lower())

        if subject.upper() not in subject_candidates:
            subject_candidates.append(subject.upper())

        ctrl_key = re.sub('ctrl-([a-zA-Z])', lambda m: 'CTRL-' + m.group(1).upper(), subject)
        if ctrl_key not in subject_candidates:
            subject_candidates.append(ctrl_key)

        found = False
        for p in ('', ':', 'c_', 'i_', 'v_', '-', '/'):
            for s in subject_candidates:
                _subject = p + s
                if _subject in _help_tags_cache:
                    subject = _subject
                    found = True
                    break

            if found:
                break

    try:
        help_file, help_tag = _help_tags_cache[subject]
    except KeyError:
        status_message('E149: Sorry, no help for %s' % subject)
        return

    help_file_resource = 'Packages/NeoVintageous/res/doc/' + help_file

    # TODO There must be a better way to test for the existence of a resource.
    doc_resources = [r for r in find_resources(help_file) if r.startswith('Packages/NeoVintageous/res/doc/')]
    if not doc_resources:
        # This should only happen if the help "tags" file is out of date.
        status_message('Sorry, help file "%s" not found' % help_file)
        return

    def _window_find_open_view(window, name: str):
        for view in window.views():
            if view.name() == name:
                return view

    help_view_name = '%s [vim help]' % (help_file)
    view = _window_find_open_view(window, help_view_name)
    if view:
        window.focus_view(view)
    else:
        view = window.new_file()
        view.set_scratch(True)
        view.set_name(help_view_name)
        settings = view.settings()
        settings.set('auto_complete', False)
        settings.set('auto_indent', False)
        settings.set('auto_match_enabled', False)
        settings.set('draw_centered', False)
        settings.set('draw_indent_guides', False)
        settings.set('draw_white_space', 'none')
        settings.set('line_numbers', False)
        settings.set('match_selection', False)
        settings.set('rulers', [])
        settings.set('scroll_past_end', False)
        settings.set('smart_indent', False)
        settings.set('tab_size', 8)
        settings.set('translate_tabs_to_spaces', False)
        settings.set('trim_automatic_white_space', False)
        settings.set('word_wrap', False)
        view.assign_syntax('Packages/NeoVintageous/res/Help.sublime-syntax')
        view.run_command('nv_view', {'action': 'insert', 'text': load_resource(help_file_resource)})
        view.set_read_only(True)

    # Format the tag so that we can
    # do a literal search rather
    # than regular expression.
    tag_region = view_find(view, help_tag.lstrip('/').replace('\\/', '/').replace('\\\\', '\\'), 0, LITERAL)
    if not tag_region:
        # This should only happen if the help "tags" file is out of date.
        tag_region = Region(0)

    # Add one point so that the cursor is
    # on the tag rather than the tag
    # punctuation star character.
    c_pt = tag_region.begin() + 1

    set_selection(view, c_pt)
    view.show(c_pt, False)

    # Fixes #420 show() doesn't work properly when the Sublime Text
    # animation_enabled is true, which the default in Sublime.
    xy = view.text_to_layout(view.text_point(view.rowcol(c_pt)[0], 0))
    view.set_viewport_position(xy)


def goto_line(view, mode: str, line_number: int) -> None:
    line_number = line_number if line_number > 0 else 1
    dest = view.text_point(line_number - 1, 0)

    def f(view, s):
        if mode == NORMAL:
            pt = next_non_blank(view, dest)
            if view.substr(pt) == EOF:
                pt = max(pt - 1, 0)

            return Region(pt)
        elif mode == INTERNAL_NORMAL:
            start_line = view.full_line(s.a)
            dest_line = view.full_line(dest)
            if start_line.a == dest_line.a:
                return dest_line
            elif start_line.a < dest_line.a:
                return Region(start_line.a, dest_line.b)
            else:
                return Region(start_line.b, dest_line.a)
        elif mode == VISUAL:
            dest_non_blank = next_non_blank(view, dest)
            if dest_non_blank < s.a and s.a < s.b:
                return Region(s.a + 1, dest_non_blank)
            elif dest_non_blank < s.a:
                return Region(s.a, dest_non_blank)
            elif dest_non_blank > s.b and s.a > s.b:
                return Region(s.a - 1, dest_non_blank + 1)
            return Region(s.a, dest_non_blank + 1)
        elif mode == VISUAL_LINE:
            if dest < s.a and s.a < s.b:
                return Region(view.full_line(s.a).b, dest)
            elif dest < s.a:
                return Region(s.a, dest)
            elif dest >= s.a and s.a > s.b:
                return Region(view.full_line(s.a - 1).a, view.full_line(dest).b)
            return Region(s.a, view.full_line(dest).b)
        return s

    with jumplist_updater(view):
        if mode == VISUAL_BLOCK:
            resolve_visual_block_target(view, get_linewise_non_blank_target(view, dest))
        else:
            regions_transformer(view, f)

    show_if_not_visible(view)


def get_linewise_non_blank_target(view, target: int) -> int:
    line = view.line(target)
    if line.size() == 0 and view.substr(line.b) == EOF:
        line = view.line(target - 1)

    return next_non_blank(view, line.a)


def _goto_modification(action: str, view, mode: str, count: int) -> None:
    with wrapscan(view, forward=(action == 'next')):
        if int(version()) >= 3189:
            for i in range(count):
                view.run_command(action + '_modification')

            a = view.sel()[0].a
            if view.substr(a) == '\n':
                if not view.line(a).empty():
                    a += 1

            set_selection(view, a)
            enter_normal_mode(view, mode)
        else:
            # @deprecated sinxe build 3189
            view.run_command('git_gutter_' + action + '_change', {'count': count, 'wrap': False})
            line = view.line(view.sel()[0].b)
            if line.size() > 0:
                pt = view.find('^\\s*', line.begin()).end()
                if pt != line.begin():
                    set_selection(view, pt)


def goto_next_change(view, mode: str, count: int) -> None:
    _goto_modification('next', view, mode, count)


def goto_prev_change(view, mode: str, count: int) -> None:
    _goto_modification('prev', view, mode, count)


def goto_next_mispelled_word(view, mode: str, count: int) -> None:
    with wrapscan(view):
        for i in range(count):
            view.run_command('next_misspelling')

    regions_transform_to_normal_mode(view)


def goto_prev_mispelled_word(view, mode: str, count: int) -> None:
    with wrapscan(view, forward=False):
        for i in range(count):
            view.run_command('prev_misspelling')

    regions_transform_to_normal_mode(view)


def goto_next_changelist(view, mode: str, count: int) -> None:
    for i in range(count):
        view.run_command('next_modification')
    regions_transform_to_normal_mode(view)


def goto_prev_changelist(view, mode: str, count: int) -> None:
    for i in range(count):
        view.run_command('prev_modification')
    regions_transform_to_normal_mode(view)


def goto_prev_target(view, mode: str, count: int, target: str) -> None:
    targets = {
        '{': ('\\{', '\\}'),
        '(': ('\\(', '\\)'),
    }

    brackets = targets.get(target)
    if not brackets or mode not in (NORMAL, VISUAL, VISUAL_LINE):
        ui_bell()
        return

    def f(view, s):
        if mode == NORMAL:
            start = s.b
            if view.substr(start) == target:
                start -= 1

            prev_target = find_prev_lone_bracket(view, start, brackets)
            if prev_target is not None:
                return Region(prev_target.a)

        elif mode in (VISUAL, VISUAL_LINE):
            start = s.b
            if s.b > s.a:
                start -= 1

            if view.substr(start) == target:
                start -= 1

            prev_target = find_prev_lone_bracket(view, start, brackets)
            if prev_target:
                if mode == VISUAL:
                    resolve_visual_target(s, prev_target.a)
                elif mode == VISUAL_LINE:
                    resolve_visual_line_target(view, s, prev_target.a)

        return s

    regions_transformer(view, f)


def goto_next_target(view, mode: str, count: int, target: str) -> None:
    targets = {
        '}': ('\\{', '\\}'),
        ')': ('\\(', '\\)'),
    }

    brackets = targets.get(target)

    if not brackets or mode not in (NORMAL, VISUAL, VISUAL_LINE):
        ui_bell()
        return

    def f(view, s):
        if mode == NORMAL:
            start = s.b
            if view.substr(start) == target:
                start += 1

            bracket = find_next_lone_bracket(view, start, brackets, count)
            if bracket is not None:
                s = Region(bracket.a)

        elif mode in (VISUAL, VISUAL_LINE):
            start = s.b
            if s.b <= s.a and view.substr(start) == target:
                start += 1

            next_target = find_next_lone_bracket(view, start, brackets)
            if next_target:
                if mode == VISUAL:
                    resolve_visual_target(s, next_target.a)
                elif mode == VISUAL_LINE:
                    resolve_visual_line_target(view, s, next_target.a)

        return s

    regions_transformer(view, f)


class GotoView():

    def __init__(self, view, mode: str, count: int):
        self.view = view
        self.mode = mode
        self.count = count

    def next_change(self) -> None:
        goto_next_change(self.view, self.mode, self.count)

    def prev_change(self) -> None:
        goto_prev_change(self.view, self.mode, self.count)

    def next_mispelled_word(self) -> None:
        goto_next_mispelled_word(self.view, self.mode, self.count)

    def prev_mispelled_word(self) -> None:
        goto_prev_mispelled_word(self.view, self.mode, self.count)

    def next_target(self, **kwargs) -> None:
        goto_next_target(self.view, self.mode, self.count, **kwargs)

    def prev_target(self, **kwargs) -> None:
        goto_prev_target(self.view, self.mode, self.count, **kwargs)

    def line(self) -> None:
        goto_line(self.view, self.mode, self.count)

    def help(self) -> None:
        goto_help(self.view)

    def next_changelist(self):
        goto_next_changelist(self.view, self.mode, self.count)

    def prev_changelist(self):
        goto_prev_changelist(self.view, self.mode, self.count)


def jump_to_mark(view, mode: str, mark: str, to_non_blank: bool = False) -> None:
    if int(version()) >= 4082 and mark in ("'", '`'):
        view.run_command('jump_back')
        return

    if to_non_blank:
        def f(view, s):
            if mode == NORMAL:
                resolve_normal_target(s, next_non_blank(view, view.line(target.b).a))
            elif mode == VISUAL:
                resolve_visual_target(s, next_non_blank(view, view.line(target.b).a))
            elif mode == VISUAL_LINE:
                resolve_visual_line_target(view, s, next_non_blank(view, view.line(target.b).a))
            elif mode == INTERNAL_NORMAL:
                if s.a < target.a:
                    s = Region(view.full_line(s.b).a, view.line(target.b).b)
                else:
                    s = Region(view.full_line(s.b).b, view.line(target.b).a)

            return s
    else:
        def f(view, s):
            if mode == NORMAL:
                resolve_normal_target(s, target.b)
            elif mode == VISUAL:
                resolve_visual_target(s, target.b)
            elif mode == VISUAL_LINE:
                resolve_visual_line_target(view, s, target.b)
            elif mode == INTERNAL_NORMAL:
                if s.a < target.a:
                    s = Region(view.full_line(s.b).a, view.line(target.b).b)
                else:
                    s = Region(view.full_line(s.b).b, view.line(target.b).a)

            return s

    try:
        target = get_mark(view, mark)
    except KeyError:
        ui_bell('E78: unknown mark')
        return

    if target is None:
        ui_bell('E20: mark not set')
        return

    if isinstance(target, tuple):
        view, target = target
        view.window().focus_view(view)

    with jumplist_updater(view):
        regions_transformer(view, f)

    if not view.visible_region().intersects(target):
        view.show_at_center(target)
