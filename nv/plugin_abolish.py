# A port of https://github.com/tpope/vim-abolish.
import re

from sublime_plugin import TextCommand

from NeoVintageous.nv.plugin      import register, register_text
from NeoVintageous.nv.polyfill    import set_selection
from NeoVintageous.nv.vi          import seqs
from NeoVintageous.nv.vi.cmd_base import RequireOneCharMixin, ViOperatorDef, translate_action
from NeoVintageous.nv.modes import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE

__all__ = ['nv_abolish_command']

def _coerce_to_mixedcase       (string:str) -> str:
    return _coerce_to_spacecase(string).title().replace(' ','')
def _coerce_to_uppercase       (string:str) -> str:
    return _coerce_to_snakecase(string).upper()
def _coerce_to_dashcase        (string:str) -> str:
    return _coerce_to_snakecase(string).replace('_','-')
def _coerce_to_spacecase       (string:str) -> str:
    return _coerce_to_snakecase(string).replace('_',' ')
def _coerce_to_dotcase         (string:str) -> str:
    return _coerce_to_snakecase(string).replace('_','.')
def _coerce_to_titlecase       (string:str) -> str:
    return _coerce_to_spacecase(string).title()
def _coerce_to_camelcase       (string:str) -> str:
    string=_coerce_to_spacecase(string).title().replace(' ','')
    if len(string) > 1:
        return string[0].lower() + string[1:]
    else:
        return string   .lower()
re_sn1 = re.compile(r"([A-Z]       +)([A-Z][a-z])", flags=re.X) # extended ignores whitespace
re_sn2 = re.compile(r"(     [a-z\d] )([A-Z]     )", flags=re.X)
def _coerce_to_snakecase       (string:str) -> str: # stackoverflow.com/a/1176023 github.com/jpvanhal/inflection
    string = re_sn1.sub(r'\1_\2',string)
    string = re_sn2.sub(r'\1_\2',string)
    string = string.replace("-","_")
    return string.lower()

DEF = {
    'alias' : {
        'm'       : 'mixedcase',
        'p'       : 'mixedcase',
        'c'       : 'camelcase',
        '_'       : 'snakecase',
        's'       : 'snakecase',
        'u'       : 'uppercase',
        'U'       : 'uppercase',
        '-'       : 'dashcase',
        'k'       : 'dashcase',
        ' '       : 'spacecase',
        '<space>' : 'spacecase',
        '.'       : 'dotcase',
        't'       : 'titlecase'
    },
    'coercion' : {
        'mixedcase': _coerce_to_mixedcase,
        'camelcase': _coerce_to_camelcase,
        'snakecase': _coerce_to_snakecase,
        'uppercase': _coerce_to_uppercase,
        'dashcase' : _coerce_to_dashcase ,
        'spacecase': _coerce_to_spacecase,
        'dotcase'  : _coerce_to_dotcase  ,
        'titlecase': _coerce_to_titlecase

    }
}

@register(seqs.SEQ['cr'], (NORMAL,))
@register_text(['AbolishCoercions'], (NORMAL,))
class AbolishCoercions(RequireOneCharMixin, ViOperatorDef):
    def init(self):
        self.scroll_into_view = True
        self.updates_xpos     = True
    def translate(self, view):
        return translate_action(view, 'nv_abolish', {'to':self.inp})


class nv_abolish_command(TextCommand):
    def run(self, edit, mode=None, count=None, register=None, to=None):
        try:
            to = CFG['alias'][to]
        except KeyError:
            pass
        try:
            coerce_func = CFG['coercion'][to]
        except KeyError:
            return

        new_sels = []
        for sel in self.view.sel():
            sel =  self.view.word(sel)
            new_sels.append(sel.begin())
            self.view.replace(edit, sel, coerce_func(self.view.substr(sel)))

        if new_sels:
            set_selection(self.view, new_sels)
