from NeoVintageous.nv import shell_unixlike


def open(view) -> None:
    shell_unixlike.open(view)


def read(view, cmd: str) -> str:
    return shell_unixlike.read(view, cmd)


def filter_region(view, text: str, cmd: str) -> str:
    return shell_unixlike.filter_region(view, text, cmd)
