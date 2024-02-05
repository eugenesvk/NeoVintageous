from NeoVintageous.nv.polyfill import merge_dicts
from NeoVintageous.nv.settings import get_count
from NeoVintageous.nv.settings import get_mode
from NeoVintageous.nv.settings import get_register
from NeoVintageous.nv.settings import set_glue_until_normal_mode
from NeoVintageous.nv.utils import InputParser
from NeoVintageous.nv.utils import translate_char


class ViCommandDefBase:

    _serializable = ['_inp', ]

    def __init__(self, *args, **kwargs):
        self.input_parser = None
        self.inp = ''

    def __str__(self) -> str:
        return '<{}>'.format(self.__class__.__qualname__)

    @property
    def accept_input(self) -> bool:
        return False

    def accept(self, key: str) -> bool:
        raise NotImplementedError('{} must implement accept()'.format(self.__class__.__name__))

    @property
    def inp(self) -> str:
        return self._inp

    @inp.setter
    def inp(self, value: str) -> None:
        self._inp = value

    def reset(self) -> None:
        self.inp = ''

    def translate(self, view) -> dict:
        """Return the command as a JSON object."""
        raise NotImplementedError('{} must implement translate()'.format(self.__class__.__name__))

    @classmethod
    def from_json(cls, data: dict) -> object:
        """Instantiate the command from a JSON object."""
        instance = cls()
        instance.__dict__.update(data)

        return instance

    def serialize(self) -> dict:
        """Serialize the command as JSON object."""
        return {
            'name': self.__class__.__name__,
            'data': {k: v for k, v in self.__dict__.items() if k in self._serializable}
        }


class CommandNotFound(ViCommandDefBase):

    def translate(self):
        raise TypeError('CommandNotFound should not be used as a runnable command')


class ViMotionDef(ViCommandDefBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.updates_xpos = False
        self.scroll_into_view = False
        self.command = ''
        self.command_args = None
        self.init()

    def init(self):
        pass

    def translate(self, view):
        return translate_motion(view, self.command, self.command_args)


class ViOperatorDef(ViCommandDefBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.updates_xpos = False
        self.scroll_into_view = False
        self.motion_required = False
        self.repeatable = False
        self.glue_until_normal_mode = False
        self.builtin = False
        self.command = ''
        self.command_args = None
        self.init()

    def init(self):
        pass

    def translate(self, view):
        if self.glue_until_normal_mode:
            set_glue_until_normal_mode(view, True)

        if self.builtin:
            return translate_builtin_action(self.command, self.command_args)

        return translate_action(view, self.command, self.command_args)


class RequireOneCharMixin(ViCommandDefBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input_parser = InputParser(InputParser.IMMEDIATE)

    @property
    def accept_input(self) -> bool:
        return self.inp == ''

    def accept(self, key: str) -> bool:
        self.inp += translate_char(key)

        return True


def translate_builtin_action(command: str, args: dict = None) -> dict:
    return {
        'action': command,
        'action_args': args if args else {},
    }


def translate_action(view, command: str, args: dict = None) -> dict:
    return {
        'action': command,
        'action_args': merge_dicts({
            'mode': get_mode(view),
            'count': get_count(view),
            'register': get_register(view)
        }, args if args else {})
    }


def translate_motion(view, command: str, args: dict = None) -> dict:
    return {
        'motion': command,
        'motion_args': merge_dicts({
            'mode': get_mode(view),
            'count': get_count(view),
        }, args if args else {})
    }
