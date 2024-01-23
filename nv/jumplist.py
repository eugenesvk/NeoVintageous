from contextlib import contextmanager

import sublime

if int(sublime.version()) < 4082:
    from Default.history_list import get_jump_history

    def _update(view) -> None:
        get_jump_history(view.window().id()).push_selection(view)

    def jumplist_back(view) -> tuple:
        return get_jump_history(view.window().id()).jump_back(view)

else:
    def _update(view) -> None:
        view.run_command("add_jump_record", {"selection": [(r.a, r.b) for r in view.sel()]})

    def jumplist_back(view) -> tuple:  # pragma: no cover
        # No-op @see https://github.com/NeoVintageous/NeoVintageous/issues/806
        return (None, [])


@contextmanager
def jumplist_updater(view):
    _update(view)

    yield

    _update(view)
