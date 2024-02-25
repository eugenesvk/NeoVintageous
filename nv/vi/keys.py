import re

from NeoVintageous.nv import variables
from NeoVintageous.nv.vi import seqs
from NeoVintageous.nv.modes import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE


mappings = { # map[key]=internal class/command
    INSERT: {},
    NORMAL: {},
    OPERATOR_PENDING: {},
    SELECT: {},
    VISUAL: {},
    VISUAL_BLOCK: {},
    VISUAL_LINE: {}
}  # type: dict
mappings_reverse = { # map[internal class Name] = key from  ↑ to make finding a key easier later when we need to convert full text command from user config to internal vim key labels
    INSERT: {},
    NORMAL: {},
    OPERATOR_PENDING: {},
    SELECT: {},
    VISUAL: {},
    VISUAL_BLOCK: {},
    VISUAL_LINE: {}
}  # type: dict


map_textcmd2cmd = {} # type: dict
map_cmd2textcmd = {} # type:dict map[internal command Name] = assigned textual command name from ↑ to make matching a textual command to a key easier (also preserves CaSe of entered commands)

_NAMED_KEYS_NEST = [

    seqs.SEQ['⧵'],
    seqs.SEQ['␈'],
    seqs.BAR,
    seqs.SEQ['␡'],
    seqs.SEQ['▼'],
    seqs.SEQ['⇥'],
    seqs.SEQ['⏎'],
    seqs.SEQ['⎋'],
    seqs.SEQ['⇤'],
    seqs.SEQ['⎀'],
    seqs.SEQ['🔢0'],
    seqs.SEQ['🔢1'],
    seqs.SEQ['🔢2'],
    seqs.SEQ['🔢3'],
    seqs.SEQ['🔢4'],
    seqs.SEQ['🔢5'],
    seqs.SEQ['🔢6'],
    seqs.SEQ['🔢7'],
    seqs.SEQ['🔢8'],
    seqs.SEQ['🔢9'],
    seqs.SEQ['🔢/'],
    seqs.SEQ['🔢='],
    seqs.SEQ['🔢-'],
    seqs.SEQ['🔢*'],
    seqs.SEQ['🔢.'],
    seqs.SEQ['🔢+'],
    seqs.SEQ['Ⓛ'],
    seqs.SEQ['◀'],
    seqs.LESS_THAN,
    seqs.SEQ['⇟'],
    seqs.SEQ['⇞'],
    seqs.SEQ['▶'],
    seqs.SEQ['␠'],
    seqs.SEQ['⭾'],
    seqs.SEQ['▲'],

    seqs.SEQ['F1'],
    seqs.SEQ['F2'],
    seqs.SEQ['F3'],
    seqs.SEQ['F4'],
    seqs.SEQ['F5'],
    seqs.SEQ['F6'],
    seqs.SEQ['F7'],
    seqs.SEQ['F8'],
    seqs.SEQ['F9'],
    seqs.SEQ['F10'],
    seqs.SEQ['F11'],
    seqs.SEQ['F12'],
    seqs.SEQ['F13'],
    seqs.SEQ['F14'],
    seqs.SEQ['F15'],
    seqs.SEQ['F16'],
    seqs.SEQ['F17'],
    seqs.SEQ['F18'],
    seqs.SEQ['F19'],
    seqs.SEQ['F20'],

]
_NAMED_KEYS = [item for sublist in _NAMED_KEYS_NEST for item in sublist]



def _resolve_named_key_alias(key: str):
    try:
        return seqs.NAMED_KEY_ALIASES[key]
    except KeyError:
        return key


_KEYPAD_NUM = re.compile('<k(\\d)>')


def resolve_keypad_count(key: str) -> str:
    keypad_num = _KEYPAD_NUM.search(key)
    if keypad_num:
        return keypad_num.group(1)

    return key


class KeySequenceTokenizer():
    """Takes in a sequence of key names and tokenizes it."""

    _EOF = -2

    def __init__(self, source: str):
        """Sequence of key names in Vim notation."""
        self.idx = -1
        self.source = source

    def _consume(self):
        self.idx += 1
        if self.idx >= len(self.source):
            self.idx -= -1
            return self._EOF
        return self.source[self.idx]

    def _peek_one(self):
        if (self.idx + 1) >= len(self.source):
            return self._EOF
        return self.source[self.idx + 1]

    def _is_named_key(self, key: str) -> bool:
        return key.lower() in _NAMED_KEYS

    def _sort_modifiers(self, modifiers: str) -> str:
        """Ensure consistency in the order of modifier letters according to c > m > s."""
        if len(modifiers) == 6:
            modifiers = 'c-m-s-'
        elif len(modifiers) > 2:
            if modifiers.startswith('s-') and modifiers.endswith('c-'):
                modifiers = 'c-s-'
            elif modifiers.startswith('s-') and modifiers.endswith('m-'):
                modifiers = 'm-s-'
            elif modifiers.startswith('m-') and modifiers.endswith('c-'):
                modifiers = 'c-m-'
        return modifiers

    def _long_key_name(self) -> str:
        key_name = ''
        modifiers = ''

        while True:
            c = self._consume()

            if c == self._EOF:
                raise ValueError("expected '>' at index {0}".format(self.idx))

            elif (c.lower() in ('c', 's', 'm', 'd', 'a')) and (self._peek_one() == '-'):
                # <A-...> is aliased to <M-...>
                if c.lower() == 'a':
                    c = 'm'

                if c.lower() in modifiers.lower():
                    raise ValueError('invalid modifier sequence: {0}'.format(self.source))

                modifiers += c + self._consume()

            elif c == '>':
                modifiers = self._sort_modifiers(modifiers.lower())

                if len(key_name) == 1  and key_name not in seqs.NAMED_KEY_ALIASES:
                    if not modifiers:
                        raise ValueError('wrong sequence {0}'.format(self.source))

                    return '<' + modifiers.upper() + key_name + '>'

                elif self._is_named_key('<' + _resolve_named_key_alias(key_name.lower()) + '>'):
                    return '<' + modifiers.upper() + _resolve_named_key_alias(key_name.lower()) + '>'

                else:
                    raise ValueError("'<{0}>' is not a known key".format(key_name))

            else:
                key_name += c

    def _tokenize_one(self):
        c = self._consume()

        if c in seqs.NAMED_KEY_ALIASES:
            return '<' + seqs.NAMED_KEY_ALIASES[c] + '>'
        elif c == '<':
            if len(self.source) == 1:
                return c
            else:
                return self._expand_vars(self._long_key_name())
        else:
            return c

    def _iter_tokenize(self):
        while True:
            token = self._tokenize_one()
            if token == self._EOF:
                break
            yield token

    def _expand_vars(self, c: str) -> str:
        return variables.get(c) if variables.is_key_name(c) else c


def tokenize_keys(keys: str) -> list:
    return KeySequenceTokenizer(keys)._iter_tokenize()


_BARE_COMMAND_NAME_PATTERN = re.compile(r'^(?:".)?(?:[1-9]+)?')


def to_bare_command_name(seq: str) -> str:
    # Args:
    #   seq (str): The command sequence.
    #
    # Return:
    #   str: The command sequence with register and counts strips e.g. 2daw ->
    #       daw, "a2d2aw -> daw, etc. The special case '0' is returned
    #       unmodified.
    if seq == '0':
        return seq

    # Account for d2d and similar sequences.
    new_seq = list(tokenize_keys(_BARE_COMMAND_NAME_PATTERN.sub('', seq)))

    return ''.join(k for k in new_seq if not k.isdigit())


def assign(seq: list, modes, *args, **kwargs):
    """Register a 'key sequence' to 'command' mapping with NeoVintageous
      'key sequence' must be known to NeoVintageous
      'command'      must be a ViMotionDef or ViOperatorDef
    Decorated class is instantiated with `*args` and `**kwargs`.
    'mappings'         is a '{mode : {sequence : cmd}}' dict
      # [mode_normal][<insert>] = <ViEnterInsertMode>
      # [mode_normal][i       ] = <ViEnterInsertMode>
    'mappings_reverse' is a '{mode : {cmd : sequence}}' dict (list of all sequences)
    """
    def inner(cls):
        for mode in modes:
            for seq_lng in seq:
                mappings[mode][seq_lng] = cls(*args, **kwargs)
                if (T := type(cls(*args, **kwargs))) not in mappings_reverse[mode]: # store the first letter map
                    mappings_reverse[mode][T] =     [seq_lng]
                else: # and append others
                    mappings_reverse[mode][T].append(seq_lng)
        return cls
    return inner


def assign_text(commands:list, modes:tuple, *args, icon:str='', **kwargs):
    """Register a 'text command' to 'command' mapping with NeoVintageous
      'text command' must be known to NeoVintageous (converted to lower case)
      'command'      must be a ViMotionDef or ViOperatorDef
      'icon'         display in the status bar when the command is used in a sequence
    Decorated class is instantiated with `*args` and `**kwargs`.
    @keys: A list of (`mode:tuple`, `commands:list`) pairs to map the decorated class to
    """
    def inner(cls):
        cls.icon = icon
        for cmd in commands:  # 'EnterInsertMode' → class ViEnterInsertMode(ViOperatorDef)
            if (C := cmd.lower())               not in map_textcmd2cmd:
                map_textcmd2cmd[C] = cls(*args,**kwargs)
        if     (T := type(cls(*args,**kwargs))) not in map_cmd2textcmd:
            map_cmd2textcmd    [T] = commands
        return cls
    return inner
