# A port of https://github.com/tpope/vim-abolish.
import re
import logging

from sublime_plugin import TextCommand

from NeoVintageous.nv.log         import DEFAULT_LOG_LEVEL, TFMT
from NeoVintageous.nv.plugin      import register, register_text
from NeoVintageous.nv.polyfill    import set_selection
from NeoVintageous.nv.vi          import seqs
from NeoVintageous.nv.vi.cmd_base import RequireOneCharMixin, ViOperatorDef, translate_action
from NeoVintageous.nv.modes       import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE
from NeoVintageous.nv.cfg_parse   import clean_name, get_tag_val_warn

from NeoVintageous.nv.rc import cfgU

_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)
if _log.hasHandlers(): # clear existing handlers, including sublime's
    logging.getLogger(__name__).handlers.clear()
    # _log.addHandler(stream_handler)
_L = True if _log.isEnabledFor(logging.KEY) else False

__all__ = ['nv_abolish_command']

re_sn1 = re.compile(r"([A-Z]       +)([A-Z][a-z])", flags=re.X) # extended ignores whitespace
re_sn2 = re.compile(r"(     [a-z\d] )([A-Z]     )", flags=re.X)
def _coerce_to_snakecase       (string:str) -> str: # stackoverflow.com/a/1176023 github.com/jpvanhal/inflection
    string = re_sn1.sub(r'\1_\2',string)
    string = re_sn2.sub(r'\1_\2',string)
    string = string.replace("-","_")
    return string.lower()
def _coerce_to_uppercase       (string:str) -> str:
    return _coerce_to_snakecase(string).upper()
def _coerce_to_dashcase        (string:str) -> str:
    return _coerce_to_snakecase(string).replace('_','-')
def _coerce_to_spacecase       (string:str) -> str:
    return _coerce_to_snakecase(string).replace('_',' ')
def _coerce_to_dotcase         (string:str) -> str:
    return _coerce_to_snakecase(string).replace('_','.')
def _coerce_to_mixedcase       (string:str) -> str:
    return _coerce_to_spacecase(string).title().replace(' ','')
def _coerce_to_titlecase       (string:str) -> str:
    return _coerce_to_spacecase(string).title()
def _coerce_to_camelcase       (string:str) -> str:
    string=_coerce_to_spacecase(string).title().replace(' ','')
    if len(string) > 1:
        return string[0].lower() + string[1:]
    else:
        return string   .lower()

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
        'snakeuppercase': _coerce_to_uppercase,
        'dashcase' : _coerce_to_dashcase ,
        'kebabcase': _coerce_to_dashcase ,
        'spacecase': _coerce_to_spacecase,
        'dotcase'  : _coerce_to_dotcase  ,
        'titlecase': _coerce_to_titlecase

    }
}
import copy
CFG =  copy.deepcopy(DEF) # copy defaults to be able to reset values on config reload

def reload_with_user_data_kdl() -> None:
    if hasattr(cfgU,'kdl') and (nest := cfgU.kdl.get('plugin'  ,None))\
        and                    (cfg  :=     nest.get('abolish',None)): # skip on initial import when Plugin API isn't ready, so no settings are loaded
        global CFG
        _log.debug("@plugin abolish: Parsing config")
        for node_parent in cfg.nodes: # 'alias'
            # 0. Parse node       args: clear
            # 1. Parse node child args: {m mixedcase;}
            # 2. Parse node properties:  m=mixedcase
            if (cfg_key:=node_parent.name) == 'alias':
                # _log.debug(f"@plugin abolish: Parsing config {cfg_key}")
                if (args := node_parent.args): # 0. clear
                    tag_val = args[0] #(t)‘’ if (t) exists (though shouldn't)
                    (tag,val) = get_tag_val_warn(tag_val=tag_val,logger=_log,node_name=cfg_key)
                    if val == 'clear':
                        CFG[cfg_key] = dict() # clear all existing aliases
                        _log.debug('CFG arg cleared @%s ‘%s’={}',cfg.name,cfg_key)
                    else:
                        _log.warn("node ‘%s’ has unrecognized value in argument ‘%s’, expecting one of: %s"
                            ,       node.name,                              tag_val,'clear')
                # elif not args:
                    # _log.warn("node ‘%s’ is missing arguments in its child ‘%s’"
                        # ,           cfg_key,                          node.name)
                if len(args) > 1:
                    _log.warn("node ‘%s’ has extra arguments, only the 1st was used ‘%s’"
                        ,        cfg_key,                                {', '.join(args)})
                for node in node_parent.nodes: # 1. m mixedcase key_node value_arg pairs
                    key = node.name
                    if (args := node.args):
                        tag_val = args[0] #(t)‘’ if (t) exists (though shouldn't)
                        # val = tag_val.value if hasattr(tag_val,'value') else tag_val # ignore tag
                        if hasattr(tag_val,'value'):
                            val = clean_name(tag_val.value) # ignore tag
                            _log.warn("node ‘%s’ has unrecognized tag in argument ‘%s’"
                                ,      node.name,                               tag_val)
                        else:
                            val = clean_name(tag_val)
                        if val in CFG['coercion']:
                            CFG[    cfg_key][key] = val # mixedcase
                            _log.debug('CFG set to arg @%s ‘%s’=‘%s’'
                                ,                   cfg_key,key,val)
                        else:
                            _log.warn("node ‘%s’ has unrecognized value in argument ‘%s’, expecting one of: %s"
                                ,       node.name,                              tag_val,' '.join(CFG['coercion'].keys()))
                    elif not args:
                        _log.warn("node ‘%s’ is missing arguments in its child ‘%s’"
                            ,           cfg_key ,                          node.name)
                    if len(args) > 1:
                        _log.warn("node ‘%s’ has extra arguments in its child ‘%s’, only the 1st was used ‘%s’"
                            ,           cfg_key ,                         node.name   ,       {', '.join(args)})
                node = node_parent
                for (key,tag_val) in node.props.items(): # 2. m=mixedcase key=value pairs
                    if hasattr(tag_val,'value'): #‘=(t)‘’ if (t) exists (though shouldn't)
                        val = clean_name(tag_val.value) # ignore tag
                        _log.warn("node ‘%s’ has unrecognized tag  property ‘%s=%s’"
                            ,       node.name,                              key,tag_val)
                    else:
                        val = clean_name(tag_val)
                    # val = tag_val.value if hasattr(tag_val,'value') else tag_val
                    if  val in CFG['coercion']:
                        CFG[    cfg_key][key] = val # mixedcase
                        _log.debug('CFG set to prop @%s %s=%s'
                            ,                   cfg_key,key,val)
                    else:
                        _log.warn("node ‘%s’ has unrecognized value in property ‘%s=%s’, expecting one of: %s"
                            ,       node.name,                                  key,tag_val,' '.join(CFG['coercion'].keys()))
                # elif not node.props:
                    # _log.warn("node ‘%s’ is missing missing key=value properties",cfg_key)
    else:
        CFG = copy.deepcopy(DEF) # copy defaults to be able to reset values on config reload


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
