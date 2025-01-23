import sublime  # noqa: E402
from sublime import DRAW_EMPTY_AS_OVERWRITE, DRAW_NO_FILL, DRAW_NO_OUTLINE, DRAW_SOLID_UNDERLINE, DRAW_SQUIGGLY_UNDERLINE, DRAW_STIPPLED_UNDERLINE
from sublime import active_window, set_timeout, PopupFlags

from NeoVintageous.nv.options  import get_option
from NeoVintageous.nv.settings import get_setting
from NeoVintageous.nv.settings import get_setting_hly
from NeoVintageous.nv.vim      import status_message
from NeoVintageous.nv.helper   import remove_prefix


def _ui_bell(*msg: str) -> None:
    window = active_window()
    if not window:
        return

    view = window.active_view()
    if not view:
        return

    if msg:
        status_message(*msg)

    if get_option(view, 'belloff') == 'all':
        return

    color_scheme = get_setting(view, 'bell_color_scheme')
    if color_scheme in ('dark', 'light'):
        color_scheme = 'Packages/NeoVintageous/res/Bell-%s.hidden-color-scheme' % color_scheme

    duration = int(0.3 * 1000)
    times = 4
    delay = 55

    style = get_setting(view, 'bell')

    settings = view.settings()

    if style == 'view':
        settings.set('color_scheme', color_scheme)

        def remove_bell() -> None:
            settings.erase('color_scheme')

        set_timeout(remove_bell, duration)
    elif style == 'views':
        views = []
        for group in range(window.num_groups()):
            view = window.active_view_in_group(group)
            if view:
                view.settings().set('color_scheme', color_scheme)
                views.append(view)

        def remove_bell() -> None:
            for view in views:
                view.settings().erase('color_scheme')

        set_timeout(remove_bell, duration)
    elif style == 'blink':
        # Ensure we leave the setting as we found it.
        times = times if (times % 2) == 0 else times + 1

        def do_blink() -> None:
            nonlocal times
            if times > 0:
                settings.set('highlight_line', not settings.get('highlight_line'))
                times -= 1
                set_timeout(do_blink, delay)

        do_blink()


def ui_bell(*args: str) -> None:
    _ui_bell(*args)


_REGION_FLAGS = {
    'fill': DRAW_NO_OUTLINE,
    'outline': DRAW_NO_FILL,
    'squiggly_underline': DRAW_SQUIGGLY_UNDERLINE | DRAW_NO_FILL | DRAW_NO_OUTLINE | DRAW_EMPTY_AS_OVERWRITE,
    'stippled_underline': DRAW_STIPPLED_UNDERLINE | DRAW_NO_FILL | DRAW_NO_OUTLINE | DRAW_EMPTY_AS_OVERWRITE,
    'underline': DRAW_SOLID_UNDERLINE | DRAW_NO_FILL | DRAW_NO_OUTLINE | DRAW_EMPTY_AS_OVERWRITE,
}


def ui_region_flags(name: str) -> int:
    return _REGION_FLAGS.get(name, 0)


def ui_highlight_yank(view) -> None:
    if not get_setting_hly(view, 'highlighted_yank'):
        return

    view.add_regions(
        'highlightedyank',
        list(view.sel()),
        scope='string highlightedyank',
        flags=ui_region_flags(get_setting_hly(view, 'highlighted_yank_style'))
    )

    set_timeout(
        lambda: view.erase_regions('highlightedyank'),
        get_setting_hly(view, 'highlighted_yank_duration')
    )


def ui_highlight_yank_clear(view) -> None:
    view.erase_regions('highlightedyank')

DEF = dict( # proper HTML tables not supported in limited Sublime's html, so use a bad formatting gimmick
     enable = True
    ,delay  = 1
    ,table  = '''<body id="nv_help_key">
      <div>K⃣          🅃    Command\t            \tℹ</div>
      {rows}
    </body>'''
    ,row            = '''<div>{key}   {icon}   {type} ¦ {cmd} ¦ {info}</div>'''
    ,max_width       = 1280 # 320
    ,max_height      =  960 # 240
)
import copy
CFG = copy.deepcopy(DEF) # copy defaults to be able to reset values on config reload
def get_popup_key_table_html(prefix,cmd_part:dict) -> str:
    rows = []
    for key,val in cmd_part.items(): # 'nnn': {
        key_no_pre = remove_prefix(key,prefix)
        key_b = f"{prefix}<b>{key_no_pre}</b>"
        cmdo = ' '.join(val['cmdo']) or '' #'cmdo':['MoveToBracketMatch']
        icon = val['icon'] or '   ' #'desc':'Go (comment) ([{ or preprocessor directive match @ line'
        type = val['type'] or '  ' #'icon':'🢔(n)🢖'
        info = val['desc'] or '   ' #'type':'‸'
        row = CFG['row'].format_map(dict(key=key_b,icon=icon,type=type,cmd=cmdo,info=info))
        rows.append(row)
    return CFG['table'].format_map(dict(rows=''.join(rows)))
from NeoVintageous.nv.mappings import _get_partial_matches_help
def show_popup_key_help(view:sublime.View, prefix:str, point:int=-1) -> None:
    if not view:
        return
    cmd_part = _get_partial_matches_help(view, "mode_normal", prefix)
    # print(f"prefix={prefix} cmd_part = {cmd_part}")
    view.show_popup(
        content       = get_popup_key_table_html(prefix,cmd_part) # str
        ,flags        = PopupFlags.HIDE_ON_CHARACTER_EVENT        #
        ,location     = point                                     # Point -1
        ,max_width    = CFG['max_width']                          # DIP
        ,max_height   = CFG['max_height']                         # DIP
    )
