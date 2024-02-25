from NeoVintageous.nv.modes import INSERT as _INSERT
from NeoVintageous.nv.modes import NORMAL as _NORMAL
from NeoVintageous.nv.modes import OPERATOR_PENDING as _OPERATOR_PENDING
from NeoVintageous.nv.modes import SELECT as _SELECT
from NeoVintageous.nv.modes import VISUAL as _VISUAL
from NeoVintageous.nv.modes import VISUAL_BLOCK as _VISUAL_BLOCK
from NeoVintageous.nv.modes import VISUAL_LINE as _VISUAL_LINE


mappings = {
    _INSERT: {},
    _NORMAL: {},
    _OPERATOR_PENDING: {},
    _SELECT: {},
    _VISUAL: {},
    _VISUAL_BLOCK: {},
    _VISUAL_LINE: {}
}  # type: dict
mappings_reverse = { # map[internal class Name] = key from  ↑ to make finding a key easier later when we need to convert full text command from user config to internal vim key labels
    _INSERT: {},
    _NORMAL: {},
    _OPERATOR_PENDING: {},
    _SELECT: {},
    _VISUAL: {},
    _VISUAL_BLOCK: {},
    _VISUAL_LINE: {}
}  # type: dict

map_textcmd2cmd = {} # type: dict
map_cmd2textcmd = {} # type:dict map[internal command Name] = assigned textual command name from ↑ to make matching a textual command to a key easier (also preserves CaSe of entered commands)


classes = {}  # type: dict


def register(seq: list, modes: tuple, *args, **kwargs):
    """Register a 'key sequence' to 'command' mapping with NeoVintageous
      'key sequence' must be known to NeoVintageous
      'command'      must be a ViMotionDef or ViOperatorDef
    Decorated class is instantiated with `*args` and `**kwargs`
    @keys: A list of (`mode:tuple`, `sequence:list`) pairs to map the decorated class to
    """
    def inner(cls):
        for mode in modes:
            for seq_lng in seq:
                mappings[mode][seq_lng] = cls(*args, **kwargs)
                if (T := type(cls(*args, **kwargs))) not in mappings_reverse[mode]: # store the first letter map
                    mappings_reverse[mode][T] =     [seq_lng]
                else: # and append others
                    mappings_reverse[mode][T].append(seq_lng)
                classes[cls.__name__] = cls
        return cls
    return inner

def register_text(commands: list, modes: tuple, *args, icon:str='', **kwargs):
    """Register a 'text command' to 'command' mapping with NeoVintageous
      'text command' must be known to NeoVintageous (converted to lower case)
      'command'      must be a ViMotionDef or ViOperatorDef
      'icon'         display in the status bar when the command is used in a sequence
    Decorated class is instantiated with `*args` and `**kwargs`.
    @keys: A list of (`mode:tuple`, `commands:list`) pairs to map the decorated class to
    """
    def inner(cls):
        cls.icon = icon
        for cmd in commands:  # 'SneakBack' → class SneakS(SneakInputMotion)
            if (C := cmd.lower())               not in map_textcmd2cmd:
                map_textcmd2cmd[C] = cls(*args,**kwargs)
            classes[cls.__name__] = cls
        if     (T := type(cls(*args,**kwargs))) not in map_cmd2textcmd:
            map_cmd2textcmd    [T] = commands
        return cls
    return inner
