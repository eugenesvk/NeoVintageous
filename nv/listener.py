_listeners = {}


def register(name: str, listener) -> None:
    _listeners[name] = listener


# InsertEnter - Just before starting Insert mode.
def on_insert_enter(view, prev_mode: str) -> None:
    for listener in _listeners.values():
        listener.on_insert_enter(view, prev_mode)


# InsertLeave - Just after leaving Insert mode.
def on_insert_leave(view, new_mode: str) -> None:
    for listener in _listeners.values():
        listener.on_insert_leave(view, new_mode)
