# A port of https://github.com/tpope/vim-surround.

import re
import logging

from sublime import Region
from sublime_plugin import TextCommand

from NeoVintageous.nv.plugin          import register, register_text
from NeoVintageous.nv.polyfill        import view_find
from NeoVintageous.nv.utils           import InputParser, translate_char
from NeoVintageous.nv.vi              import seqs
from NeoVintageous.nv.vi.cmd_base     import ViOperatorDef, translate_action
from NeoVintageous.nv.vi.search       import reverse_search
from NeoVintageous.nv.vi              import text_objects
from NeoVintageous.nv.vi.text_objects import get_text_object_region, TO
from NeoVintageous.nv.modes           import INSERT, INTERNAL_NORMAL, NORMAL, OPERATOR_PENDING, REPLACE, SELECT, UNKNOWN, VISUAL, VISUAL_BLOCK, VISUAL_LINE
from NeoVintageous.nv.vim             import enter_normal_mode, run_motion

from NeoVintageous.nv.rc import cfgU

from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL
_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)

__all__ = ['nv_surround_command']


class nv_surround_command(TextCommand):
    def run(self, edit, action, **kwargs):
        if   action == 'replace':
            _do_replace(self.view, edit, **kwargs)
        elif action == 'delete':
            _do_delete (self.view, edit, **kwargs)
        elif action == 'add':
            _do_add    (self.view, edit, **kwargs)


@register(seqs.SEQ['ys'], (NORMAL,))
@register_text(['SurroundAdd','Surroundys'], (NORMAL,))
class Surroundys(ViOperatorDef):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos     = True
        self.repeatable       = True
        self.motion_required  = True
        self.input_parser     = InputParser(InputParser.AFTER_MOTION)

    @property
    def accept_input(self) -> bool:
        if not self.inp:
            return True
        if self.inp[0] in CFG['function'] or self.inp.lower().startswith('<c-f>'): # Function
            return self.inp[-1] != '\n'
        (_,target_to) = text_objects.CFG['pairs'].get(self.inp[0],(None,None))
        if target_to == TO.Tag or self.inp[0] == '<': # Tag
            return _should_tag_accept_input(self.inp)
        return False

    def accept(self, key: str) -> bool:
        self.inp += translate_char(key)
        return True

    def translate(self, view):
        return translate_action(view,'nv_surround',{'action':'add','replacement':self.inp})


@register(seqs.YSS, (NORMAL,))
@register_text(['SurroundAddLine','Surroundyss'],seqs.YSS, (NORMAL,), icon='+━+')
class Surroundyss(Surroundys):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.motion_required = False
        self.input_parser = InputParser(InputParser.IMMEDIATE)

    def translate(self, view):
        return translate_action(view, 'nv_surround', {
            'action': 'ys',
            'motion': {
                'motion': 'nv_vi_select_text_object',
                'motion_args': {
                    'mode': INTERNAL_NORMAL,
                    'count': 1,
                    'inclusive': False,
                    'text_object': 'line'
                }
            },
            'replacement': self.inp
        })


@register(seqs.SEQ['⇧s'], (VISUAL, VISUAL_LINE, VISUAL_BLOCK))
@register_text(['SurroundAddVis','SurroundS'], (VISUAL, VISUAL_LINE, VISUAL_BLOCK), icon='')
class SurroundS(Surroundys):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.motion_required = False
        self.input_parser = InputParser(InputParser.IMMEDIATE)


@register(seqs.SEQ['ds'], (NORMAL, OPERATOR_PENDING))
@register_text(['SurroundDel','Surroundds'], (NORMAL, OPERATOR_PENDING), icon='🢔ᵡ🢖')
class Surroundds(ViOperatorDef):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True
        self.repeatable = True
        self.input_parser = InputParser(InputParser.IMMEDIATE)

    # TODO Fix ds should not accept input
    @property
    def accept_input(self) -> bool:
        single = len(self.inp) == 1
        tag = re.match('<.*?>', self.inp)

        return not (single or tag)

    def accept(self, key: str) -> bool:
        self.inp += translate_char(key)

        return True

    def translate(self, view):
        return translate_action(view,'nv_surround',{'action':'delete','target':self.inp})


@register(seqs.SEQ['cs'], (NORMAL, OPERATOR_PENDING))
@register_text(['SurroundRepl','Surroundcs'], (NORMAL, OPERATOR_PENDING), icon='🢔🗘🢖')
class Surroundcs(ViOperatorDef):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True
        self.repeatable = True
        self.input_parser = InputParser(InputParser.IMMEDIATE)

    @property
    def accept_input(self) -> bool:
        if not self.inp:
            return True
        if len(self.inp) < 2: # Requires at least two characters, a target and a replacement.
            return True

        (_,target_to) = text_objects.CFG['pairs'].get(self.inp[1],(None,None))
        if target_to == TO.Tag or self.inp[1] == '<': # Tag
            return _should_tag_accept_input(self.inp[1:])

        return False

    def accept(self, key: str) -> bool:
        self.inp += translate_char(key)

        return True

    def translate(self, view):
        return translate_action(view,'nv_surround',{'action':'replace','target':self.inp[0]
            ,'replacement':self.inp[1:]})

DEF = {
    'punctuationmarks' : {
        '(': ('(', ')'),
        ')': ('(', ')'),
        '{': ('{', '}'),
        '}': ('{', '}'),
        '[': ('[', ']'),
        ']': ('[', ']'),
        '<': ('<', '>'),
        '>': ('<', '>'),
    },
    'punctuationalias' : {
        'b': ')',
        'B': '}',
        'r': ']',
        'a': '>',
    },
    'function' : {
        'f':  '',
        'F': ' ',
    },
    'appendspacetochars' : '({[',
    'steadycursor' : dict(),
    'seekforward' : False, # when looking for brackets, if the current text is NOT enclosed, but Targets plugin is enabled, seek the next pair of brackets
      # ⎀a(b)  with surround delete of ( will result in:
      # ⎀ab       True  SEEK_FORWARD
      # ⎀a(b)     False SEEK_FORWARD
}
for key in (_STEADY_CURSOR_KEY := ['add','replace','delete']):
    DEF['steadycursor'][key] = True
DEF['punctuationmarksopen'] = set()
for _,mark_pair in DEF['punctuationmarks'    ].items(): # add opening brackets
    pair_open = mark_pair[0]
    (_,target_to) = text_objects.CFG['pairs'].get(pair_open,(None,None))
    if target_to == TO.Bracket:
        DEF           ['punctuationmarksopen'].add(pair_open)

VALID_TARGETS_DEF  = 'ra@' # Delete targets
VALID_TARGETS_DEF += '\'"`b()B{}[]<>t.,-_;:#~*\\/|+=&$' # targets for plugin github.com/wellle/targets.vim
#IilpsWw plugin targets excluded
import copy
CFG = copy.deepcopy(DEF) # copy defaults to be able to reset values on config reload
VALID_TARGETS = copy.deepcopy(VALID_TARGETS_DEF)

resp = re.compile(r'\s+')
def reload_with_user_data_kdl() -> None:
    if hasattr(cfgU,'kdl') and (nest := cfgU.kdl.get('plugin'  ,None))\
        and                    (cfg  :=     nest.get('surround',None)): # skip on initial import when Plugin API isn't ready, so no settings are loaded
        global CFG, VALID_TARGETS
        for node_parent in cfg.nodes: # 'punctuation_marks'
            # 1. Parse node child args: {‘ ‘’; “ “”;}
            # 2. Parse node properties:  ‘=‘’  “=“”
            if (cfg_key:=node_parent.name) == 'punctuationmarks':
                # _log.debug(f"@plugin surround: Parsing config {cfg_key}")
                for node in node_parent.nodes: # 1. ‘ ‘’ key_node value_arg pairs
                    key = node.name
                    if (args := node.args):
                        tag_val = args[0] #(t)‘’ if (t) exists (though shouldn't)
                        # val = tag_val.value if hasattr(tag_val,'value') else tag_val # ignore tag
                        if hasattr(tag_val,'value'):
                            val = tag_val.value # ignore tag
                            _log.warn("node ‘%s’ has unrecognized tag in argument ‘%s’"
                                ,      node.name,                               tag_val)
                        else:
                            val = tag_val
                        _warn = ''
                        if     (_len := len(val)    ) == 2:
                            CFG[    cfg_key][key] = (val[0]    ,val[1]    ) # ‘    ’
                            _log.debug('CFG set to arg @%s %s=(%s %s)'
                                ,                  cfg_key,key,val[0],val[1])
                        else:
                            _warn     = f"node ‘{node.name}’ ‘{key}’ should have an argument of length 2, not ‘{_len}’"
                            v_split = resp.split(val)
                            if (_len := len(v_split)) == 2:
                                _warn = ''
                                CFG[cfg_key][key] = (v_split[0],v_split[1]) # `'   '
                                _log.debug('CFG set to arg v_split @%s %s=(%s %s)'
                                    ,                       cfg_key,key,v_split[0],v_split[1])
                            else:
                                _warn = f"node ‘{node.name}’ ‘{key}’ should have an argument of 2 space-separated substrings, not ‘{_len}’"
                        if _warn:
                            _log.warn(_warn)
                    elif not args:
                        _log.warn("node ‘%s’ is missing arguments in its child ‘%s’"
                            ,           cfg_key ,                          node.name     )
                    if len(args) > 1:
                        _log.warn("node ‘%s’ has extra arguments in its child ‘%s’, only the 1st was used ‘%s’"
                            ,           cfg_key ,                         node.name   ,       {', '.join(args)})
                node = node_parent
                for (key,tag_val) in node.props.items(): # 2. ‘=‘’ key=value pairs
                    if hasattr(tag_val,'value'): #‘=(t)‘’ if (t) exists (though shouldn't)
                        val = tag_val.value # ignore tag
                        _log.warn("node ‘%s’ has unrecognized tag  property ‘%s=%s’"
                            ,       node.name,                              key,tag_val)
                    else:
                        val = tag_val
                    # val = tag_val.value if hasattr(tag_val,'value') else tag_val
                    _warn = ''
                    if     (_len := len(val)    ) == 2:
                        CFG[    cfg_key][key] = (val[0]    ,val[1]    ) # ‘    ’
                        _log.debug('CFG set to prop @%s %s=(%s %s)'
                            ,                   cfg_key,key,val[0],val[1])
                    else:
                        _warn     = f"node ‘{node.name}’ ‘{key}’ should have a value of length 2, not ‘{_len}’"
                        v_split = resp.split(val)
                        if (_len := len(v_split)) == 2:
                            _warn = ''
                            CFG[cfg_key][key] = (v_split[0],v_split[1]) # `'   '
                            _log.debug('CFG set to prop v_split @%s %s=(%s %s)'
                                ,                   cfg_key,key,v_split[0],v_split[1])
                        else:
                            _warn = f"node ‘{node.name}’ ‘{key}’ should have a value of 2 space-separated substrings, not ‘{_len}’"
                    if _warn:
                        _log.warn(_warn)
                # if not node.props:
                    # _log.warn(f"node ‘{cfg_key}’ is missing key=value properties")

            if (cfg_key:=node_parent.name) == 'punctuationalias':
                # _log.debug(f"@plugin surround: Parsing config {cfg_key}")
                if node_parent.get('clear',None):
                    CFG[cfg_key].clear()
                for arg in node_parent.args:          # Parse arguments, only 'clear' is valid, ignore others
                    tag = arg.tag   if hasattr(arg,'tag'  ) else ''
                    val = arg.value if hasattr(arg,'value') else arg
                    # if tag:
                        # _log.debug("node ‘%s’ has unrecognized tag in argument %s",node.name,arg)
                    if   val == 'clear':
                        CFG[cfg_key].clear()
                        break # only 'clear' is valid, ignore others
                    else:
                        # _log.error("node ‘%s’ has unparseable argument %s\n  expecting a ‘clear’, other values are set as properties or child nodes",node.name,arg)
                        continue
                for node in node_parent.nodes: # 1. d (  key_node value_arg pairs
                    key = node.name
                    if key == 'clear':
                        continue # already cleared separately, don't clear our own values
                    if (args := node.args):
                        tag_val = args[0] #(t)"(" if (t) exists (though shouldn't)
                        # val = tag_val.value if hasattr(tag_val,'value') else tag_val # ignore tag
                        if hasattr(tag_val,'value'):
                            val = tag_val.value # ignore tag
                            _log.warn("node ‘%s’ has unrecognized tag in ‘%s’ argument ‘%s’"
                                ,        node.name,                       key,        tag_val)
                        else:
                            val = tag_val
                        CFG[cfg_key][key] = val
                        _log.debug('CFG set to arg @%s %s=%s',cfg_key,key,val)
                    elif not args:
                        _log.warn("node ‘%s’ is missing arguments in its child ‘%s’"
                            ,         cfg_key ,                                 node.name)
                    if len(args) > 1:
                        _log.warn("node ‘%s’ has extra arguments in its child ‘%s’, only the 1st was used ‘%s’"
                            ,         cfg_key ,                                node.name,{', '.join(args)})
                node = node_parent
                for (key,tag_val) in node.props.items(): # 2. d=(   key=value pairs
                    if hasattr(tag_val,'value'): #(t)"(" if (t) exists (though shouldn't)
                        val = tag_val.value # ignore tag
                        _log.warn("node ‘%s’ has unrecognized tag  property ‘%s=%s’"
                            ,       node.name,                              key,tag_val)
                    else:
                        val = tag_val
                    # val = tag_val.value if hasattr(tag_val,'value') else tag_val
                    CFG[cfg_key][key] = val
                    _log.debug('CFG set to prop @%s %s=%s'
                        ,                   cfg_key,key,val)
                # if not node.props:
                    # _log.warn(f"node ‘{cfg_key}’ is missing key=value properties")

            if (cfg_key:=node_parent.name) == 'function':
                for arg in node_parent.args:          # Parse arguments
                    tag = arg.tag   if hasattr(arg,'tag'  ) else ''
                    val = arg.value if hasattr(arg,'value') else arg
                    if   val == 'clear':
                        CFG[cfg_key].clear()
                    else:
                        if not len(val) == 1:
                            _log.error("node ‘%s’ has an invalid argument %s\n  expected a single character, got length ‘%s’",node_parent.name,arg,len(val))
                            continue
                        if   tag.lower() in  ['␠','␣','s','sp','space']:
                            CFG[cfg_key][val] = ' '
                        elif tag:
                            _log.warn("node ‘%s’ has an argument %s with an invalid tag %s\n  valid tags are ‘%s’",node_parent.name,arg,tag,'␠ ␣ s sp space')
                        else:
                            CFG[cfg_key][val] = ''

            if (cfg_key:=node_parent.name) == 'steadycursor':
                _log.debug("@plugin surround: Parsing config ‘%s’",cfg_key)
                for node in node_parent.nodes: # 1. add true  key_node value_arg pairs
                    key = node.name
                    if (args := node.args):
                        tag_val = args[0] #(t)true if (t) exists (though shouldn't)
                        # val = tag_val.value if hasattr(tag_val,'value') else tag_val # ignore tag
                        if hasattr(tag_val,'value'):
                            val = tag_val.value # ignore tag
                            _log.warn("node ‘%s’ has unrecognized tag in  ‘%s’ argument ‘%s’"
                                ,       node.name,                          key, tag_val)
                        else:
                            val = tag_val
                        if key in _STEADY_CURSOR_KEY:
                            CFG[cfg_key][key] = val
                            _log.debug('CFG set to arg @%s %s=%s',cfg_key,key,val)
                        else:
                            _log.warn("node ‘%s’ has unrecognized property ‘%s=%s’"
                                ,       cfg_key,                          key, val)
                    elif not args:
                        _log.warn("node ‘%s’ is missing arguments in its child ‘%s’"
                            ,       cfg_key,                              node.name)
                    if len(args) > 1:
                        _log.warn("node ‘%s’ has extra arguments in its child ‘%s’, only the 1st was used ‘%s’"
                            ,       cfg_key,                             node.name,            {', '.join(args)})
                node = node_parent
                for (key,tag_val) in node.props.items(): # 2. add=true   key=value pairs
                    if hasattr(tag_val,'value'): #(t)true if (t) exists (though shouldn't)
                        val = tag_val.value # ignore tag
                        _log.warn("node ‘%s’ has unrecognized tag  property ‘%s=%s’"
                            ,      node.name,                               key,tag_val)
                    else:
                        val = tag_val
                    # val = tag_val.value if hasattr(tag_val,'value') else tag_val
                    if key in _STEADY_CURSOR_KEY:
                        CFG[cfg_key][key] = val
                        _log.debug('CFG set to prop @%s %s=%s',cfg_key,key,val)
                    else:
                        _log.warn("node ‘%s’ has unrecognized property ‘%s=%s’"
                            ,       node.name,                         key,val)
                # if not node.props:
                    # _log.warn(f"node ‘{cfg_key}’ is missing key=value properties")

            if (cfg_key:=node_parent.name) == 'appendspacetochars': # )}]
                # _log.debug(f"@plugin surround: Parsing config {cfg_key}")
                node = node_parent
                if (args := node.args):
                    if not isinstance(args[0],str):
                        _log.error("node ‘%s’ argument should be a string, not ‘%s’",node.name,type(args[0]))
                    else:
                        CFG[cfg_key] = args[0]
                if not args:
                    _log.warn("node ‘%s’ is missing arguments",cfg_key)
                if len(args) > 1:
                    _log.warn("node ‘%s’ has extra arguments, only the 1st was used ‘%s’",cfg_key,{', '.join(args)})
            if (cfg_key:=node_parent.name) == 'seekforward': # ⎀a(b) don't delete () if false
                # _log.debug(f"@plugin surround: Parsing config {cfg_key}")
                node = node_parent
                if (args := node.args):
                    if not isinstance(args[0],bool):
                        _log.error("node ‘%s’ argument should be ‘true’ or ‘false’, not ‘%s’"
                            ,           node.name,                                   args[0])
                    else:
                        CFG[cfg_key] = args[0]
                if not args:
                    _log.warn("node ‘%s’ is missing arguments"
                        ,          cfg_key)
                if len(args) > 1:
                    _log.warn("node ‘%s’ has extra arguments, only the 1st was used ‘%s’"
                        ,          cfg_key,                               ', '.join(args))
        VALID_TARGETS += "".join(((val:=CFG['punctuationmarks'][k])[0]+val[1]) for k in CFG['punctuationmarks']) # add marks
        VALID_TARGETS += "".join(       CFG['punctuationalias'].keys()) # add aliases
        VALID_TARGETS  = set(VALID_TARGETS) # leave unique values
        for _,mark_pair in CFG['punctuationmarks'    ].items(): # add opening brackets
            pair_open = mark_pair[0]
            (_,target_to) = text_objects.CFG['pairs'].get(pair_open,(None,None))
            if target_to ==TO.Bracket:
                CFG           ['punctuationmarksopen'].add(pair_open)

    else: # reset config to defaults
        CFG = copy.deepcopy(DEF)
        VALID_TARGETS = copy.deepcopy(VALID_TARGETS_DEF)

# Expand target punctuation marks:
  # (){}[]<> represent themselves/their counterparts
  # bBra     aliases for )}]>     )}mirror Vim; ]> are arbitrary and subject to change
  # '"`      quote marks and their counterparts are the same
def _expand_targets(target: str) -> tuple:
    target = _resolve_target_aliases(target) # 'a' to '>'

    return CFG['punctuationmarks'].get(target, (target, target)) # '>' to a tuple of (< , >) or self


def _resolve_target_aliases(target: str) -> str:
    return CFG['punctuationalias'].get(target, target) # 'a' to '>' or self

# )}]> wraps the text in the appropriate pair of characters
# bBra aliases
# ({[  wraps the text and appends space to the inside
#    < is different, used for tags
def _expand_replacements(target: str) -> tuple:
    if (pad := CFG['function'].get(target[0],None)): # Function replacement
        return (target[1:].strip() + '('+pad, pad+')')
    if target.lower().startswith('<c-f>'):
        return ('(' + target[5:].strip() + ' ', ')')

    # Tag replacement
    (_,target_to) = text_objects.CFG['pairs'].get(target[0],(None,None))
    if target_to == TO.Tag or target[0] == '<' and len(target) >= 3:
        append = prefix = ''

        if target.lower().startswith('<c-t>'):
            target = '<' + target[5:]
            append = prefix = '\n'

        # Attributes are stripped in the closing tag. The first character if
        # "t", which is an alias for "<", is replaced too.
        if target[-1] == '\n':
            target = target[0:-1] + '>'

        replacement_a = '<' + target[1:] + append
        replacement_b = prefix + '</' + target[1:].strip()[:-1].strip().split(' ', 1)[0] + '>'

        return (replacement_a, replacement_b)

    # Pair replacement
    target = _resolve_target_aliases(target)
    append_addition_space = True if target in CFG['appendspacetochars'] else False
    begin, end = _expand_targets(target)
    if append_addition_space:
        begin = begin + ' '
        end   =         ' ' + end

    return (begin, end)


from sublime import Region
def _rsynced_regions_transformer(view, f, _res_view_sel_reverse:list=[]) -> None:
    sels = reversed(list(view.sel())) # end→beg not to adjust for ∑inserts

    view_sel = view.sel()
    for i,sel in enumerate(sels):
        view_sel.subtract(sel)

        (new_sel, (edit_count_beg,edit_count_end)) = f(view, sel)
        if not isinstance(new_sel, Region):
            raise TypeError('sublime.Region required')

        if _res_view_sel_reverse: # adjust old cursor pos by count of chars inserted @ beg
            old_sel = _res_view_sel_reverse[i]
            (a,b) = old_sel.to_tuple() # → this region as a tuple (a,b)
            if old_sel.end() < new_sel.begin(): # seek forward edited after the cursor, so the cursor stays
                old_sel_adjusted = Region(               a,               b)
            else:
                old_sel_adjusted = Region(edit_count_beg+a,edit_count_beg+b)
            view_sel.add(old_sel_adjusted)
        else: # or don't adjust anything and just select the new region
            view_sel.add(new_sel)


def _do_replace(view, edit, mode: str, target: str, replacement: str, count=None, register=None) -> None:
    if not target and replacement:
        return
    if len(target) != 1:
        return
    if len(replacement) >= 3: # Replacements must be 1 character long or at least 3 characters for tags
        (_,target_to) = text_objects.CFG['pairs'].get(replacement[0],(None,None))
        if (not replacement[ 0] ==  '<' and not target_to == TO.Tag) or \
            not replacement[-1] in ('>','\n'):
            return
    elif len(replacement) != 1:
        return

    # Targets.
    target_open, target_close = _expand_targets(target) # 'a' or '>' to a tuple of (< , >)

    # Replacements
    replacement_open, replacement_close = _expand_replacements(replacement)

    def _f(view, s):
        if mode == INTERNAL_NORMAL:
            (_,target_to) = text_objects.CFG['pairs'].get(target,(None,None))
            if target_to == TO.Tag:
                target_tag_open, target_tag_close = ('<[^>]+>', '<\\/[^>]+>')
                region_begin = None
                region_end = view.find(target_tag_close, s.b)
                if region_end:
                    region_begin = reverse_search(view, target_tag_open, end=region_end.begin(), start=0)
            else:
                region_begin, region_end = _get_regions_for_target(view, s, target_open)

            if not (region_end and region_begin):
                return (s, (0,0))

            replacement_a = replacement_open

            # You may specify attributes here and they will be stripped from the closing tag. If replacing a tag, its attributes are kept in the new tag. End your input with > to discard the those attributes.
            if target_to == TO.Tag and replacement[-1] == '\n':
                match = re.match('<([^ >]+)(.*)>', view.substr(region_begin))
                if match:
                    if replacement_open[-1] == '\n':
                        replacement_a = replacement_open[:-2] + match.group(2) + '>\n'
                    else:
                        replacement_a = replacement_open[:-1] + match.group(2) + '>'

            # It's important that the regions are replaced in reverse because otherwise the buffer size would be reduced by the number of characters replaced and would result in an off-by-n bugs.
            view.replace(edit, region_end  , replacement_close)
            view.replace(edit, region_begin, replacement_a    )
            repl_count_end = len(replacement_close) - region_end.size()
            repl_count_beg = len(replacement_a    ) - region_begin.size()

            return (Region(region_begin.begin()), (repl_count_beg,repl_count_end))

        return (s, (0,0))

    _res_view_sel_reverse = list()    # save cursor pos as they might be reset elsewhere
    if CFG['steadycursor']['replace']:
        sels = reversed(list(view.sel())) # end→beg not to adjust for ∑replacements
        for sel in sels:
            _res_view_sel_reverse.append(sel)

    _rsynced_regions_transformer(view, _f, _res_view_sel_reverse)


def _do_delete(view, edit, mode: str, target: str, count=None, register=None) -> None:
    if not target:
        return
    if len(target) != 1:
        return
    (_,target_to) = text_objects.CFG['pairs'].get(target,(None,None))
    if target_to and target_to in [TO.Word,TO.BigWord,TO.Sentence,TO.Paragraph]: # nothing to delete, so noop
        return
    if target not in VALID_TARGETS:
        return

    should_trim_contained_whitespace = True if target in CFG['punctuationmarksopen'] else False # Trim contained whitespace for opening punctuation mark targets.
    target_open, target_close = _expand_targets(target) # Targets 'a' or '>' to a tuple of (< , >)

    def _f(view, s):
        if mode == INTERNAL_NORMAL:
            if target_to == TO.Tag: # a pair of HTML or XML tags
                # TODO test dst works when cursor position is inside tag begin <a|bc>x -> dst -> |x
                # TODO test dst works when cursor position is inside tag end   <abc>x</a|bc> -> dst -> |x
                region_end   = view.find     (   '<\\/.*?>',              s.b)
                region_begin = reverse_search(view, '<.*?>', start=0, end=s.b)
            else:
                region_begin, region_end = _get_regions_for_target(view, s, target_open)
                if should_trim_contained_whitespace and           (region_begin and region_end):
                    region_begin, region_end = _trim_regions(view, region_begin,    region_end)

            if not (region_begin and region_end):
                return (s, (0,0))

            # It's important that the regions are replaced in reverse because otherwise the buffer size would be reduced by the number of characters replaced and would result in an off-by-one bug.
            view.replace(edit,   region_end  , '')
            view.replace(edit,   region_begin, '')
            del_count_end = -1 * region_end  .size()
            del_count_beg = -1 * region_begin.size()

            return (Region(region_begin.begin()), (del_count_beg,del_count_end))

        return (s, (0,0))

    _res_view_sel_reverse = list()    # save cursor pos as they might be reset elsewhere
    if CFG['steadycursor']['delete']:
        sels = reversed(list(view.sel())) # end→beg not to adjust for ∑deletes
        for sel in sels:
            _res_view_sel_reverse.append(sel)

    _rsynced_regions_transformer(view, _f, _res_view_sel_reverse)


def _get_regions_for_target(view, s: Region, target: str) -> tuple:
    text_object = get_text_object_region(view, s, target, inclusive=True, seek_forward=CFG['seekforward'])
    if not text_object:
        return (None, None)

    begin = Region(text_object.begin(), text_object.begin() + 1)
    end = Region(text_object.end(), text_object.end() - 1)

    return (begin, end)


def _view_rfind(view, sub: str, start: int, end: int, flags: int = 0):
    match = reverse_search(view, sub, start, end, flags)
    if match is None or match.b == -1:
        return None

    return match


def _trim_regions(view, start: Region, end: Region) -> tuple:
    start_ws = view_find(view, '\\s*.', start_pt=start.end())
    if start_ws and start_ws.size() > 1:
        start = Region(start.begin(), start_ws.end() - 1)

    end_ws = _view_rfind(view, '.\\s*', start=start.end(), end=end.begin())
    if end_ws and end_ws.size() > 1:
        end = Region(end_ws.begin() + 1, end.end())

    return (start, end)


from typing import List, Union
def _do_add(view, edit, mode: str = None, motion=None, replacement: str = '"', count: int = 1, register=None) -> None:
    def _surround(view, edit, s, replacement: str) -> List[int]:
        replacement_open, replacement_close = _expand_replacements(replacement) #< > for >
        if replacement_open.startswith('<'):
            ins_count_end = view.insert(edit, s.b, replacement_close)
            ins_count_beg = view.insert(edit, s.a, replacement_open)
            return (ins_count_beg,ins_count_end)

        if mode == VISUAL_LINE:
            replacement_open = replacement_open + '\n'
            replacement_close = replacement_close + '\n'

        ins_count_end = view.insert(edit, s.end(), replacement_close)
        ins_count_beg = view.insert(edit, s.begin(), replacement_open)
        return (ins_count_beg,ins_count_end) # count actual # of inserted chars to be able to calculate old cursor position

    def f(view, s):
        if mode == INTERNAL_NORMAL:
            (ins_count_end,ins_count_beg) = _surround(view, edit, s, replacement)
            return (Region(s.begin()), (ins_count_end,ins_count_beg))
        elif mode in (VISUAL, VISUAL_LINE, VISUAL_BLOCK):
            (ins_count_end,ins_count_beg) = _surround(view, edit, s, replacement)
            return (Region(s.begin()), (ins_count_end,ins_count_beg))
        return s

    if not motion and not view.has_non_empty_selection_region():
        enter_normal_mode(view, mode)
        raise ValueError('motion required')

    _res_view_sel_reverse = list()    # save cursor pos as they are reset in run_motion
    if CFG['steadycursor']['add']:
        sels = reversed(list(view.sel())) # end→beg not to adjust for ∑inserts
        for sel in sels:
            _res_view_sel_reverse.append(sel)

    if mode == INTERNAL_NORMAL:
        run_motion(view, motion) # add a Word object to selection (moving to Word's end)
        #eg {'motion':'nv_vi_select_text_object','motion_args':{'count':1,'inclusive':False,'mode':'mode_internal_normal','text_object':'w'}}

    if replacement:
        _rsynced_regions_transformer(view, f, _res_view_sel_reverse)

    enter_normal_mode(view, mode)


def _should_tag_accept_input(inp: str) -> bool:
    if inp.lower().startswith('<c-t>'):
        return not re.match('<[Cc]-t>.*?[\n>]', inp)

    return not inp[-1] in ('>', '\n')
