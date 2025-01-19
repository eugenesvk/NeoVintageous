# A port of https://github.com/tpope/vim-abolish.
import re
import logging

from sublime import Selection, Region
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
def _coerce_to_dotcase         (string:str) -> str:
    return _coerce_to_snakecase(string).replace('_','.')
def _coerce_to_spacecase       (string:str) -> str:
    return _coerce_to_snakecase(string).replace('_',' ')
def _coerce_to_titlecase       (string:str) -> str:
    return _coerce_to_spacecase(string).title()
def _coerce_to_mixedcase       (string:str) -> str:
    return _coerce_to_titlecase(string).replace(' ','')
def _coerce_to_camelcase       (string:str) -> str:
    string=_coerce_to_titlecase(string).replace(' ','')
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

    },
    'steadycursor' : True,
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
            if (cfg_key:=node_parent.name) == 'steadycursor':
                # _log.debug(f"@plugin abolish: Parsing config {cfg_key}")
                args = [a for a in node_parent.getArgs((...,...))] if NeoVintageous.nv.cfg.KDLV == 2 else node_parent.args()
                if args: # 0. true
                    tag_val = args[0] #(t)‘’ if (t) exists (though shouldn't)
                    (tag,val) = get_tag_val_warn(tag_val=tag_val,logger=_log,node_name=cfg_key)
                    if not isinstance(val,bool):
                        _log.warn("node ‘%s’ has unrecognized value in argument ‘%s’, expecting one of: %s"
                            ,       cfg_key,                              tag_val,'clear')
                    else:
                        CFG[cfg_key] = val
                        _log.debug('CFG set to arg @%s ‘%s’=‘%s’'
                                ,             cfg.name,cfg_key,val)
                elif not args:
                    _log.warn("node ‘%s’ is missing arguments",cfg_key)
                if len(args) > 1:
                    _log.warn("node ‘%s’ has extra arguments, only the 1st was used ‘%s’"
                        ,        cfg_key,                                {', '.join(args)})

            if (cfg_key:=node_parent.name) == 'alias':
                # _log.debug(f"@plugin abolish: Parsing config {cfg_key}")
                args = [a for a in node_parent.getArgs((...,...))] if NeoVintageous.nv.cfg.KDLV == 2 else node_parent.args()
                if args: # 0. clear
                    tag_val = args[0] #(t)‘’ if (t) exists (though shouldn't)
                    (tag,val) = get_tag_val_warn(tag_val=tag_val,logger=_log,node_name=cfg_key)
                    if val == 'clear':
                        CFG[cfg_key].clear() # clear all existing aliases
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
                    args = [a for a in node.getArgs((...,...))] if NeoVintageous.nv.cfg.KDLV == 2 else node.args()
                    if args:
                        tag_val = args[0] #(t)‘’ if (t) exists (though shouldn't)
                        # val = tag_val.value if hasattr(tag_val,'value') else tag_val # ignore tag
                        if hasattr(tag_val,'value'):
                            val = clean_name(tag_val.value) # ignore tag
                            _log.warn("node ‘%s’ has unrecognized tag in argument ‘%s’"
                                ,      node.name,                               tag_val)
                        else:
                            val = clean_name(tag_val)
                        if val in DEF['coercion']:
                            CFG[    cfg_key][key] = val # mixedcase
                            _log.debug('CFG set to arg @%s ‘%s’=‘%s’'
                                ,                   cfg_key,key,val)
                        else:
                            _log.warn("node ‘%s’ has unrecognized value in argument ‘%s’, expecting one of: %s"
                                ,       node.name,                              tag_val,' '.join(DEF['coercion'].keys()))
                    elif not args:
                        _log.warn("node ‘%s’ is missing arguments in its child ‘%s’"
                            ,           cfg_key ,                          node.name)
                    if len(args) > 1:
                        _log.warn("node ‘%s’ has extra arguments in its child ‘%s’, only the 1st was used ‘%s’"
                            ,           cfg_key ,                         node.name   ,       {', '.join(args)})
                node = node_parent
                nprops = node.getProps((...,...)) if NeoVintageous.nv.cfg.KDLV == 2 else node.props.items()
                for key,tag_val in nprops: # 2. m=mixedcase key=value pairs
                    if hasattr(tag_val,'value'): #‘=(t)‘’ if (t) exists (though shouldn't)
                        val = clean_name(tag_val.value) # ignore tag
                        _log.warn("node ‘%s’ has unrecognized tag  property ‘%s=%s’"
                            ,       node.name,                              key,tag_val)
                    else:
                        val = clean_name(tag_val)
                    # val = tag_val.value if hasattr(tag_val,'value') else tag_val
                    if  val in DEF['coercion']:
                        CFG[    cfg_key][key] = val # mixedcase
                        _log.debug('CFG set to prop @%s %s=%s'
                            ,                   cfg_key,key,val)
                    else:
                        _log.warn("node ‘%s’ has unrecognized value in property ‘%s=%s’, expecting one of: %s"
                            ,       node.name,                                  key,tag_val,' '.join(DEF['coercion'].keys()))
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


import difflib
from difflib import SequenceMatcher, Differ
def diff_add(i,sel:Region,old,i1,i2,j1,j2) -> list:
    if   i1 >  old[i].end  (): # ignore ranges past end of selection
        _log.key("  +ignore %s > %s",i1,old[i].end())
        return
    elif i1 <= old[i].begin(): # move beginning and end
        a = b = j2-j1 # length of added text from the diff at strB
        _log.key("  +moved a,b by %s from %s,%s to %s,%s (ind%s i=%s,%s j=%s,%s sel=%s)"
                ,                    j2-j1,sel.begin(),sel.end()
                ,                    j2-j1+sel.begin(),sel.end()+j2-j1, i,i1,i2,j1,j2,sel)
        return [a,b]
    elif i1 <= old[i].  end(): # move               end
        b = j2-j1
        _log.key("+moved   b by %s",j2-j1)
        return [0,b]
def diff_rem(i,sel:Region,old,i1,i2) -> list:
    if   i1 >  old[i].  end(): # ignore ranges past end of selection
        _log.key("  −ignore %s > %s",i1,old[i].end())
        return
    elif i1 <= old[i].begin(): # move beginning and end
        a = -min(i2-i1, sel.begin()-i1) # on overlap, move to the left excluding the overlap
        b = -min(i2-i1, sel.end  ()-i1)
        _log.key("  −moved a,b by %s,%s from %s,%s to %s,%s (ind%s i=%s,%s sel=%s)"
                ,                      a,b, sel.begin(),sel.end()
                ,                      a +  sel.begin(),sel.end()+b, i,i1,i2,sel)
        return [a,b]
    elif i1 <= old[i].  end(): # move               end
        b = -min(i2-i1, sel.end  ()-i1)
        _log.key("-moved   b by %s",b)
        return [a,b]

from typing import List
def diff_same_pos(sels_inA:List[Region], selA:Selection,strA:str,strB:str) -> None:
    """Maintains the selection positions in strA given the diff to strB using SequenceMatcher from difflib
    selA has word range relative to other selections, needed to translate indices within a word to i within doc"""

    _log.key("sels_inA = %s¦%s\nselA = %s\nstrA = %s\nstrB = %s",type(sels_inA),sels_inA, selA,strA,strB)
    sels_inA_new = [[i.begin(),i.end()] for i in sels_inA] # copy same ranges in case there are no changes
    a = selA.begin()
    b = selA.end  ()
    s = SequenceMatcher(None, strA.lower(), strB.lower()) #  compares two sequences and identifies common and differing subsequences
    for tag, i1,i2, j1,j2 in s.get_opcodes(): # generates instructions (opcodes) for transforming one string into another
        _log.key("%s i%s–%s=‘%s’ j%s–%s=‘%s’"
            ,     tag, i1,i2,strA[i1:i2], j1,j2,strB[j1:j2])
        if   tag == "equal":
            pass
        elif tag == "insert": #additions in  string 2
            for i,sel in enumerate(sels_inA):
                if (new := diff_add(i,sel,sels_inA,a+i1,a+i2,j1,j2)):
                    _log.key("insert sel=%s new=%s",sel,new)
                    sels_inA_new[i][0] += new[0]
                    sels_inA_new[i][1] += new[1]
        elif tag == "delete": #removals from string 1
            for i,sel in enumerate(sels_inA):
                if (new := diff_rem(i,sel,sels_inA,a+i1,a+i2      )):
                    _log.key("delete sel=%s new=%s",sel,new)
                    sels_inA_new[i][0] += new[0]
                    sels_inA_new[i][1] += new[1]
        elif tag == "replace": #additions in  string 2
            len_s1 = (i2-i1)
            len_s2 = (j2-j1)
            len_diff = len_s2 - len_s1
            if   len_diff == 0: # 0 net changes
                _log.key("replace pass")
                pass
            elif len_diff  > 0: # + net change
                for i,sel in enumerate(sels_inA):
                    if new := diff_add(i,sel,sels_inA,a+i1             ,b+i2,j1 + len_diff+1,j2):
                        _log.key(f'replace +new={new}')
                        sels_inA_new[i][0] += new[0]
                        sels_inA_new[i][1] += new[1]
            elif len_diff  < 0: # − net change
                for i,sel in enumerate(sels_inA):
                    if new := diff_rem(i,sel,sels_inA,a+i1 - len_diff+1,b+i2,j1             ,j2):
                        _log.key("replace -new=%s",new)
                        sels_inA_new[i][0] += new[0]
                        sels_inA_new[i][1] += new[1]
        else:
            _log.error(f"unknown diff tag in diff_same_pos",tag, a+i1, b+i2, j1, j2)
    _log.key(f"sels_inA_new = {sels_inA_new}")
    return sels_inA_new

class nv_abolish_command(TextCommand):
    def run(self, edit, mode=None, count=None, register=None, to=None):
        try:
            to          = CFG['alias'   ][to]
        except KeyError:
            pass
        try:
            coerce_func = CFG['coercion'][to]
        except KeyError:
            return

        view_sel = self.view.sel()
        new_sels = []
        cur_sels = list(view_sel); cur_sels.reverse() # end→beg not to adjust for ∑inserts
        # sels_inA_new = [[i.begin(),i.end()] for i in cur_sels] # ranges for each current selection

        skip_sels_i = []  # don't touch selections in the same word twice
        for i,sel in enumerate(cur_sels):      # ⎀titleCase (0, 0)=‘’
            if i in skip_sels_i:
                continue
            sel_w   = self.view.word  (sel  ) #(0, 9)   (expand to word's ends)
            sel_w_s = self.view.substr(sel_w) #      =‘titleCase’
            repl    = coerce_func(sel_w_s)    #       ‘Title Case’
            aw      = sel_w.begin() # word's borders
            bw      = sel_w.end  ()

            if CFG['steadycursor']:
                sels_inA = [] # find all sels that this word contains not to lose them on edits
                for i,sel in enumerate(cur_sels):
                    if       sel.end  () <  aw: # selections are rev-sorted, so if they end before word begins, all subsequent ones will also be before
                        break
                    if aw <= sel.begin() <= bw or \
                       aw <= sel.end  () <= bw:
                        skip_sels_i.append(i)
                        sels_inA.append (sel)
                        view_sel.subtract(sel)
                        _log.key("− sel%s",sel)
                self.view.replace(edit, sel_w, repl)
                if sels_inA:
                    sels_inA_new = diff_same_pos(sels_inA=sels_inA, selA=sel_w,strA=sel_w_s,strB=repl)
                    _log.key("old %s\nnew %s",sels_inA,sels_inA_new)
                    for sel_inw in sels_inA_new:
                        view_sel.add     (Region(max(0,sel_inw[0]), max(0,sel_inw[1])))
                        _log.key("+ sel%s",sel_inw)
            else:
                new_sels.append(sel_w.begin())
                self.view.replace(edit, sel_w, repl)

        if CFG['steadycursor']:
            pass
            # new_sels_ = [Region(max(0,sels_inA_new[i][0]),max(0,sels_inA_new[i][1])) for i in range(len(cur_sels))]
            # set_selection(self.view, new_sels_)
        elif new_sels:
            set_selection(self.view, new_sels)
