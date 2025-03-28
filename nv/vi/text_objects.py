import re
import logging
import time
from datetime import datetime

from sublime import CLASS_EMPTY_LINE, CLASS_LINE_END, CLASS_LINE_START, CLASS_PUNCTUATION_END, CLASS_PUNCTUATION_START, CLASS_WORD_END, CLASS_WORD_START, IGNORECASE
from sublime import Region

from NeoVintageous.nv.log       import DEFAULT_LOG_LEVEL, TFMT
from NeoVintageous.nv.polyfill  import re_escape, view_find, view_find_in_range, view_indentation_level, view_indented_region, view_rfind_all
from NeoVintageous.nv.settings  import get_setting
from NeoVintageous.nv.utils     import get_insertion_point_at_b, next_non_blank, next_non_ws, prev_non_blank, prev_non_ws
from NeoVintageous.nv.vi.search import find_in_range, reverse_search_by_pt
from NeoVintageous.nv.vi.units  import word_starts
from NeoVintageous.nv.cfg_parse import clean_name
from NeoVintageous.nv           import cfg as nvcfg

from NeoVintageous.nv.rc import cfgU

_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)
if _log.hasHandlers(): # clear existing handlers, including sublime's
    logging.getLogger(__name__).handlers.clear()
    # _log.addHandler(stream_handler)
_L = True if _log.isEnabledFor(logging.KEY) else False


RX_ANY_TAG          	= r'</?([0-9A-Za-z-]+).*?>'
RX_ANY_TAG_NAMED_TPL	= r'</?({0}) *?.*?>'
RXC_ANY_TAG         	= re.compile(r'</?([0-9A-Za-z]+).*?>')
RX_ANY_START_TAG    	= r'<([0-9A-Za-z]+)(.*?)>' # According to the HTML 5 editor's draft, only 0-9A-Za-z characters can be used in tag names. TODO: This won't be enough in Dart Polymer projects, for example.
RX_ANY_END_TAG      	= r'</([0-9A-Za-z-]+).*?>'


ANCHOR_NEXT_WORD_BOUNDARY    	= CLASS_WORD_START | CLASS_PUNCTUATION_START | CLASS_LINE_END
ANCHOR_PREVIOUS_WORD_BOUNDARY	= CLASS_WORD_END   | CLASS_PUNCTUATION_END   | CLASS_LINE_START
WORD_REVERSE_STOPS           	= CLASS_WORD_START | CLASS_EMPTY_LINE        | CLASS_PUNCTUATION_START
WORD_END_REVERSE_STOPS       	= CLASS_WORD_END   | CLASS_EMPTY_LINE        | CLASS_PUNCTUATION_END
WORD_END_REVERSE_STOPS_NOSEP    = CLASS_WORD_END   | CLASS_EMPTY_LINE

from enum import auto, Flag, IntFlag
class TxtObj(Flag):
  #↓ unique modes             ↓ abbreviations
    Bracket  	= auto(); B 	= Bracket
    Quote    	= auto(); Q 	= Quote
    Sentence 	= auto(); S 	= Sentence
    Tag      	= auto(); T 	= Tag
    Word     	= auto(); W 	= Word
    BigWord  	= auto(); BW	= BigWord
    Paragraph	= auto(); P 	= Paragraph
    Indent   	= auto(); I 	= Indent
    BigIndent	= auto(); BI	= BigIndent
    Line     	= auto(); L 	= Line
TO = TxtObj
to_names_rev = dict() # reverse TO dict for easier mapping of user strings to text objects
for iTO in TxtObj:
    if   (to_text := clean_name(f"{iTO}".replace('TxtObj.',''))) in to_names_rev:
        _log.error(" ‘%s’ is not unique, check ‘TxtObj’ enum",to_text)
    else:
        to_names_rev[to_text] = iTO
# to_names_rev {'bigword':<TxtObj.BigWord: 32>,} # print('to_names_rev',to_names_rev)


# quote_sym = ['"',"'",'`','#','$','&','*','+',',','-','.','/',':',';','=','_','|','~','\\']
#                         ↑→ plugin github.com/wellle/targets.vim
PAIRS = {
    '"' 	: ((  '"',   '"')	, TO.Quote     ),
    "'" 	: ((  "'",   "'")	, TO.Quote     ),
    '`' 	: ((  '`',   '`')	, TO.Quote     ),
    '#' 	: ((  '#',   '#')	, TO.Quote     ), # {plugin https://github.com/wellle/targets.vim}
    '$' 	: ((  '$',   '$')	, TO.Quote     ), # {plugin https://github.com/wellle/targets.vim}
    '&' 	: ((  '&',   '&')	, TO.Quote     ), # {plugin https://github.com/wellle/targets.vim}
    '*' 	: ((  '*',   '*')	, TO.Quote     ), # {plugin https://github.com/wellle/targets.vim}
    '+' 	: ((  '+',   '+')	, TO.Quote     ), # {plugin https://github.com/wellle/targets.vim}
    ',' 	: ((  ',',   ',')	, TO.Quote     ), # {plugin https://github.com/wellle/targets.vim}
    '-' 	: ((  '-',   '-')	, TO.Quote     ), # {plugin https://github.com/wellle/targets.vim}
    '.' 	: ((  '.',   '.')	, TO.Quote     ), # {plugin https://github.com/wellle/targets.vim}
    '/' 	: ((  '/',   '/')	, TO.Quote     ), # {plugin https://github.com/wellle/targets.vim}
    ':' 	: ((  ':',   ':')	, TO.Quote     ), # {plugin https://github.com/wellle/targets.vim}
    ';' 	: ((  ';',   ';')	, TO.Quote     ), # {plugin https://github.com/wellle/targets.vim}
    '=' 	: ((  '=',   '=')	, TO.Quote     ), # {plugin https://github.com/wellle/targets.vim}
    '_' 	: ((  '_',   '_')	, TO.Quote     ), # {plugin https://github.com/wellle/targets.vim}
    '|' 	: ((  '|',   '|')	, TO.Quote     ), # {plugin https://github.com/wellle/targets.vim}
    '~' 	: ((  '~',   '~')	, TO.Quote     ), # {plugin https://github.com/wellle/targets.vim}
    '\\'	: (( '\\',  '\\')	, TO.Quote     ), # {plugin https://github.com/wellle/targets.vim}
    '(' 	: (('\\(', '\\)')	, TO.Bracket   ),
    ')' 	: (('\\(', '\\)')	, TO.Bracket   ),
    '[' 	: (('\\[', '\\]')	, TO.Bracket   ),
    ']' 	: (('\\[', '\\]')	, TO.Bracket   ),
    '{' 	: (('\\{', '\\}')	, TO.Bracket   ),
    '}' 	: (('\\{', '\\}')	, TO.Bracket   ),
    '<' 	: ((  '<',   '>')	, TO.Bracket   ),
    '>' 	: ((  '<',   '>')	, TO.Bracket   ),
    'b' 	: (('\\(', '\\)')	, TO.Bracket   ),
    'B' 	: (('\\{', '\\}')	, TO.Bracket   ),
    'p' 	: (None          	, TO.Paragraph ),
    's' 	: (None          	, TO.Sentence  ),
    't' 	: (None          	, TO.Tag       ),
    'W' 	: (None          	, TO.BigWord   ),
    'w' 	: (None          	, TO.Word      ),
    'I' 	: (None          	, TO.BigIndent ), # {not in Vim}
    'i' 	: (None          	, TO.Indent    ), # {not in Vim}
    'l' 	: (None          	, TO.Line      ),
}  # type: dict
PAIRS_LONG = { # add full names so that internal APIs do not depend on user abbreviations
    'paragraph'	: (None	, TO.Paragraph ),
    'sentence' 	: (None	, TO.Sentence  ),
    'tag'      	: (None	, TO.Tag       ),
    'bigword'  	: (None	, TO.BigWord   ),
    'word'     	: (None	, TO.Word      ),
    'bigindent'	: (None	, TO.BigIndent ), # {not in Vim}
    'indent'   	: (None	, TO.Indent    ), # {not in Vim}
    'line'     	: (None	, TO.Line      ),
}  # type: dict
PAIRS.update(PAIRS_LONG)
# for q in quote_sym:
    # PAIRS[q] = ((q,q),TO.Quote)
DEF = {'pairs':PAIRS
    ,'seekforward' : False # when looking for brackets, if the current text is NOT enclosed, but Targets plugin is enabled, seek the next pair of brackets
      # ⎀a(B)  with lowercase within ( will result in:
      # ⎀a(b)     True  SEEK_FORWARD
      # ⎀a(B)     False SEEK_FORWARD
    ,'steadycursor' : dict() # don't 'move' ⎀cursor to the changed punctuation
}
for key in (_STEADY_CURSOR_KEY := ['caselowerline','caselowerchar']):
    DEF['steadycursor'][key] = True

re_flags = 0
re_flags |= re.MULTILINE | re.IGNORECASE
re_sp = re.compile(r"\s", flags=re_flags)

import copy
CFG = copy.deepcopy(DEF) # copy defaults to be able to reset values on config reload

def reload_with_user_data_kdl() -> None:
    global CFG
    kdlv = nvcfg.CFG['pref']['kdlv']
    if hasattr(cfgU,'kdl') and (cfg := cfgU.kdl.get('textobject',None)): # skip on initial import when Plugin API isn't ready, so no settings are loaded
        _log.debug("@text_objects: Parsing config")
        replaced = [] # keep track of added values with the same label so as not to remove that label as instructed by a later config
        for node in cfgU.cfg_parse.children(cfg): # bracket "b" "B" d="()" ...
            (tag, val) = cfgU.cfg_parse.node_tag_val(node)
            cfg_key = val
            if tag:
                _log.warn("node ‘%s’ has unrecognized tag, skipping",node.name)
                continue
            if      val not in to_names_rev\
                and val not in DEF:
                _log.warn("node ‘%s’ has unrecognized name, skipping",node.name)
                continue

            if cfg_key == 'seekforward': # ⎀a(B) don't sub ⎀a(b) if false
                args = False
                for i,(arg,tag,val) in enumerate(cfgU.cfg_parse.arg_tag_val(node)):
                    args = True
                    if i == 0:
                        if tag: #(t)"(" if (t) exists (though shouldn't)
                            _log.warn("node ‘%s’ has unrecognized tag in argument ‘%s’"
                                ,      node.name,                                 arg)
                        if isinstance(val,bool):
                            CFG[cfg_key] = val
                        else:
                            _log.error("node ‘%s’ argument should be ‘true’ or ‘false’, not ‘%s’"
                                ,           node.name,                                   arg)
                    elif i > 0:
                        _log.warn("node ‘%s’ has extra arguments (only the 1st was used): ‘%s’...",cfg_key,arg)
                        break
                if not args:
                    _log.warn("node ‘%s’ is missing arguments",cfg_key)
                continue
            if cfg_key == 'steadycursor': # don't 'move' ⎀cursor to the changed punctuation
                for (arg,tag,val) in cfgU.cfg_parse.arg_tag_val(node): # Parse arguments, toggle all
                    # if tag:
                    #     _log.warn("node ‘%s’ has unrecognized tag in argument ‘%s’",node.name,arg)
                    if val == True:
                        for key in _STEADY_CURSOR_KEY:
                            CFG['steadycursor'][key] = True
                        continue
                    if val == False:
                        for key in _STEADY_CURSOR_KEY:
                            CFG['steadycursor'][key] = False
                        continue
                for (pkey,tag_val,tag,val) in cfgU.cfg_parse.prop_key_tag_val(node): # Parse properties, toggle per group ‘quote=true’
                    # if tag:
                        # _log.debug("node ‘%s’ has unrecognized value tag in property %s",cfg_key,pkey)
                    if not isinstance(val, bool):
                        _log.warn("node ‘%s’ has unrecognized value tag in property %s, expected ‘true’ or ‘false’",cfg_key,pkey)
                        continue
                    if (key := clean_name(pkey)) in _STEADY_CURSOR_KEY:
                        CFG['steadycursor'][key] = val
                        # _log.debug('CFG set to arg %s %s %s %s',cfg_key,pkey,text_obj,val)
                continue

            text_obj = to_names_rev[val]
            for (arg,tag,val) in cfgU.cfg_parse.arg_tag_val(node): # Parse arguments, −OLD pairs "b"
                # if tag:
                    # _log.debug("node ‘%s’ has unrecognized tag in argument %s",node.name,arg)
                if   val == 'clear':
                    lbl_remove = []
                    for lbl,(sep,txt_obj) in CFG['pairs'].items(): # clear default labels that are ...
                        if     lbl not in replaced   \
                           and lbl not in PAIRS_LONG \
                           and txt_obj == text_obj: # not replaced by user config and are not long names (LINE)
                            lbl_remove.append(lbl)
                    for lbl in lbl_remove:
                        _log.debug(f"clearing CFG ‘{cfg_key}’ pair: {CFG['pairs'].get(lbl,None)}")
                        CFG['pairs'].pop(lbl,None)
                    continue
                elif len(val) == 1:
                    pair = (re.escape(val[0]),re.escape(val[0])) # dupe symmetric pair like ''
                    lbl  =           (val[0] ,          val[0] )
                elif len(val) == 2:
                    pair = (re.escape(val[0]),re.escape(val[1])) # \( \)
                    lbl  =           (val[0] ,          val[1] )
                elif (_sp := re_sp.split(val)) and\
                    len(_sp) == 2:
                    pair = (re.escape(_sp[0]),re.escape(_sp[1])) # ="  "
                    lbl  =           (_sp[0] ,          _sp[1] )
                else:
                    _log.error("node ‘%s’ has unparseable argument %s\n  expecting a paired symbol or a space separated string",node.name,arg)
                    continue
                CFG['pairs']   [lbl[0]] = (pair,text_obj)
                CFG['pairs']   [lbl[1]] = (pair,text_obj)
                replaced.append(lbl[0])
                replaced.append(lbl[1])

            for (pkey,tag_val,tag,val) in cfgU.cfg_parse.prop_key_tag_val(node): # Parse properties, +NEW pairs d="()"
                # if tag:
                    # _log.debug("node ‘%s’ has unrecognized value tag in property %s",node.name,pkey)
                pair = None
                if       val is None\
                  or len(val) == 0 :
                    if val not in replaced:
                        CFG['pairs'].pop(pkey,None)
                        continue
                elif len(val) == 1:
                    pair = (re.escape(val[0]),re.escape(val[0])) # dupe symmetric pair like ''
                elif len(val) == 2:
                    pair = (re.escape(val[0]),re.escape(val[1])) # \( \)
                elif (_sp := re_sp.split(val)) and\
                    len(_sp) == 2:
                    pair = (re.escape(_sp[0]),re.escape(_sp[1])) # ="  "
                else:
                    _log.error("node ‘%s’ has unparseable property value %s=%s\n  expecting a paired symbol or a space separated string",node.name,pkey,tag_val)
                    continue
                CFG['pairs'][pkey] = (pair,text_obj) #
                replaced.append(pkey)
    else:
        CFG = copy.deepcopy(DEF) # copy defaults to be able to reset values on config reload

def is_at_punctuation(view, pt: int) -> bool:
    char = view.substr(pt) # FIXME Wrong if pt is at '\t'
    return (not (is_at_word(view, pt) or char.isspace() or char == '\n') and char.isprintable())


def is_at_word(view, pt: int) -> bool:
    char = view.substr(pt)

    return char.isalnum() or char == '_'


def is_at_space(view, pt: int) -> bool:
    return view.substr(pt).isspace()


def get_punctuation_region(view, pt: int) -> Region:
    start = view.find_by_class(pt + 1, forward=False, classes=CLASS_PUNCTUATION_START)
    end = view.find_by_class(pt, forward=True, classes=CLASS_PUNCTUATION_END)

    return Region(start, end)


def get_space_region(view, pt: int) -> Region:
    end = view.find_by_class(pt, forward=True, classes=ANCHOR_NEXT_WORD_BOUNDARY)

    return Region(previous_word_end(view, pt + 1), end)


def previous_word_end(view, pt: int) -> int:
    return view.find_by_class(pt, forward=False, classes=ANCHOR_PREVIOUS_WORD_BOUNDARY)


def current_word_start(view, pt: int) -> int:
    if is_at_punctuation(view, pt):
        return get_punctuation_region(view, pt).a
    elif is_at_space(view, pt):
        return get_space_region(view, pt).a

    return view.word(pt).a


def current_word_end(view, pt: int) -> int:
    if is_at_punctuation(view, pt):
        return get_punctuation_region(view, pt).b
    elif is_at_space(view, pt):
        return get_space_region(view, pt).b

    return view.word(pt).b


# https://vimhelp.appspot.com/motion.txt.html#word
# Used for motions in operations like daw and caw
def _a_word(view, pt: int, inclusive: bool = True, count: int = 1) -> Region:
    start = current_word_start(view, pt)
    end = pt

    if inclusive:
        end = word_starts(view, start, count=count, internal=True)

        # If there is no space at the end of our word text object, include any
        # preceding spaces. (Follows Vim behavior.)
        if (not view.substr(end - 1).isspace() and view.substr(start - 1).isspace()):
            start = prev_non_blank(view, start - 1) + 1

        # Vim does some inconsistent stuff here...
        if count > 1 and view.substr(end) == '\n':
            end += 1

        return Region(start, end)

    for x in range(count):
        end = current_word_end(view, end)

    return Region(start, end)


def big_word_end(view, pt: int) -> int:
    prev = pt
    while True:
        if is_at_punctuation(view, pt):
            pt = get_punctuation_region(view, pt).b
        elif is_at_word(view, pt):
            pt = current_word_end(view, pt)
        else:
            break

        if pt == prev:
            # Guards against run-away loops
            break

        prev = pt

    return pt


def big_word_start(view, pt: int) -> int:
    prev = pt
    while True:
        if is_at_punctuation(view, pt):
            pt = get_punctuation_region(view, pt).a - 1
        elif is_at_word(view, pt):
            pt = current_word_start(view, pt) - 1
        else:
            break

        if pt == prev:
            # Guards against run-away loops
            break

        prev = pt

    return pt + 1


# https://vimhelp.appspot.com/motion.txt.html#WORD
# Used for motions in operations like daW and caW
def a_big_word(view, pt: int, inclusive: bool = False, count: int = 1) -> Region:
    start, end = None, pt
    for x in range(count):
        if is_at_space(view, end):
            if start is None:
                start = get_space_region(view, pt).a

            if inclusive:
                end = big_word_end(view, get_space_region(view, end).b)
            else:
                end = get_space_region(view, end).b

        if is_at_punctuation(view, end):
            if start is None:
                start = big_word_start(view, end)

            end = big_word_end(view, end)

            if inclusive and is_at_space(view, end):
                end = get_space_region(view, end).b

        else:
            if start is None:
                start = big_word_start(view, end)

            end = big_word_end(view, end)

            if inclusive and is_at_space(view, end):
                end = get_space_region(view, end).b

    if start is None:
        return Region(end)

    return Region(start, end)


def _get_text_object_tag(view, s: Region, inclusive: bool, count: int) -> Region:
    # When the active cursor position is on leading whitespace before a tag on
    # the same line then the start point of the text object is the tag.
    line = view.line(get_insertion_point_at_b(s))
    tag_in_line = view_find_in_range(view, '^\\s*<[^>]+>', line.begin(), line.end())
    if tag_in_line:
        if s.b >= s.a and s.b < tag_in_line.end():
            if s.empty():
                s.a = s.b = tag_in_line.end()
            else:
                s.a = tag_in_line.end()
                s.b = tag_in_line.end() + 1

    begin_tag, end_tag, _ = find_containing_tag(view, s.begin())
    if not (begin_tag and end_tag):
        return s

    # The normal method is to select a <tag> until the matching </tag>. For "at"
    # the tags are included, for "it" they are excluded. But when "it" is
    # repeated the tags will be included (otherwise nothing would change).
    if not inclusive:
        if s and s == Region(begin_tag.end(), end_tag.begin()):
            inclusive = True

    if inclusive:
        return Region(begin_tag.a, end_tag.b)
    else:
        return Region(begin_tag.b, end_tag.a)


def _get_text_object_paragraph(view, s: Region, inclusive: bool, count: int) -> Region:
    return find_paragraph_text_object(view, s, inclusive, count)


def _get_text_object_bracket(view, s: Region, inclusive: bool, count: int, delims: tuple, seek_forward:bool=False) -> Region:
    start = get_insertion_point_at_b(s)
    opening = find_prev_lone_bracket(view, start, delims)

    start_next_bracket_pt = get_insertion_point_at_b(s)

    # Support for vim-targets In Pair and A Pair.
    if not opening and get_setting(view, 'enable_targets'):
        start = get_insertion_point_at_b(s)
        match = view_find(view, delims[0], start)
        if match and seek_forward:
            opening = find_prev_lone_bracket(view, match.begin(), delims)
            if opening:
                start_next_bracket_pt = max(start_next_bracket_pt, opening.end())

    if not opening:
        return s

    closing = find_next_lone_bracket(view, start_next_bracket_pt, delims)
    if not closing:
        return s

    if inclusive:
        return Region(opening.a, closing.b)

    a = opening.a + 1
    if view.substr(a) == '\n':
        a += 1

    b = closing.b - 1

    if b > a:
        line = view.line(b)

        if b == next_non_blank(view, line.a):
            row_a, col_a = view.rowcol(a - 1)
            row_b, col_b = view.rowcol(b + 1)
            if (row_b - 1) > row_a:
                line = view.full_line(view.text_point((row_b - 1), 0))

                return Region(a, line.b)

    return Region(a, b)


def _get_text_object_quote(view, s: Region, inclusive: bool, count: int, delims: tuple, seek_forward:bool=False) -> Region:
    line = view.line(s)

    delim_open = delims[0]
    delim_open = re_escape(delim_open)

    # FIXME: Escape sequences like \" are probably syntax-dependant.
    prev_quote = reverse_search_by_pt(view, r'(?<!\\\\)' + delim_open, start=line.a, end=   s.b)
    next_quote = find_in_range       (view, r'(?<!\\\\)' + delim_open, start=   s.b, end=line.b)

    if next_quote and not prev_quote:
        prev_quote = next_quote
        next_quote = find_in_range   (view, r'(?<!\\\\)' + delim_open, start=prev_quote.b, end=line.b)

    if not (prev_quote and next_quote):
        return s

    if inclusive:
        retReg = Region(prev_quote.a    , next_quote.b    )
    else:
        retReg = Region(prev_quote.a + 1, next_quote.b - 1)

    if not (contains_any_cursor := retReg.contains(s)):
        for sel in view.sel():
            if retReg.contains(sel):
                contains_any_cursor = True
    if not seek_forward and not contains_any_cursor: # if quotes don't cover cursor, do nothing unless seek forward is enabled
        return s

    return retReg


def _get_text_object_word(view, s: Region, inclusive: bool, count: int) -> Region:
    if s.size() == 1:
        pt = get_insertion_point_at_b(s)
    else:
        if s.b < s.a:
            pt = max(0, s.b - 1)
        else:
            pt = s.b

    w = _a_word(view, pt, inclusive=inclusive, count=count)
    if s.size() <= 1:
        return w

    if s.b >= s.a:
        return Region(s.a, w.b)

    return Region(s.a, w.a)


def _get_text_object_big_word(view, s: Region, inclusive: bool, count: int) -> Region:
    w = a_big_word(view, s.b, inclusive=inclusive, count=count)
    if s.size() <= 1:
        return w

    return Region(s.a, w.b)


def _get_text_object_sentence(view, s: Region, inclusive: bool, count: int) -> Region:
    sentence_start = view.find_by_class(s.b, forward=False, classes=CLASS_EMPTY_LINE)
    sentence_start_2 = reverse_search_by_pt(view, r'[.?!:]\s+|[.?!:]$', start=0, end=s.b)
    if sentence_start_2:
        sentence_start = (sentence_start + 1 if (sentence_start > sentence_start_2.b) else sentence_start_2.b)
    else:
        sentence_start = sentence_start + 1

    sentence_end = find_in_range(view, r'([.?!:)](?=\s))|([.?!:)]$)', start=s.b, end=view.size())
    if not sentence_end:
        return s

    if inclusive:
        return Region(sentence_start, sentence_end.b)
    else:
        return Region(sentence_start, sentence_end.b)


def _get_text_object_line(view, s: Region, inclusive: bool, count: int) -> Region:
    start, end = find_line_text_object(view, s)

    return Region(start, end)


def get_text_object_region(view, s: Region, text_object: str, inclusive: bool = False, count: int = 1, seek_forward=None) -> Region:
    if  seek_forward is None:
        seek_forward = CFG['seekforward']
    try:
        delims, type_ = CFG['pairs'][text_object]
    except KeyError:
        return s

    if   type_ == TO.Tag:
        return _get_text_object_tag      (view, s, inclusive, count)
    elif type_ == TO.Paragraph:
        return _get_text_object_paragraph(view, s, inclusive, count)
    elif type_ == TO.Bracket:
        return _get_text_object_bracket  (view, s, inclusive, count, delims, seek_forward)
    elif type_ == TO.Quote:
        return _get_text_object_quote    (view, s, inclusive, count, delims, seek_forward)
    elif type_ == TO.Word:
        return _get_text_object_word     (view, s, inclusive, count)
    elif type_ == TO.BigWord:
        return _get_text_object_big_word (view, s, inclusive, count)
    elif type_ == TO.Sentence:
        return _get_text_object_sentence (view, s, inclusive, count)
    elif type_ == TO.Line:
        return _get_text_object_line     (view, s, inclusive, count)
    elif type_ in (TO.Indent, TO.BigIndent): # A port of https://github.com/michaeljsmith/vim-indent-object. {not in Vim} Only inclusive indent-objects are countable, e.g., vai, vaI
        for _ in range(count if inclusive else 1):
            resolve_indent_text_object(view, s, inclusive, big=(type_ == TO.BigIndent))

    return s


def find_next_lone_bracket(view, start: int, items, unbalanced: int = 0):
    # TODO: Extract common functionality from here and the % motion instead of
    # duplicating code.
    new_start = start
    for i in range(unbalanced or 1):
        next_closing_bracket = find_in_range(
            view,
            items[1],
            start=new_start,
            end=view.size(),
            flags=IGNORECASE
        )

        if next_closing_bracket is None:
            # Unbalanced items; nothing we can do.
            return

        while view.substr(next_closing_bracket.begin() - 1) == '\\':
            next_closing_bracket = find_in_range(view, items[1],
                                                 start=next_closing_bracket.end(),
                                                 end=view.size(),
                                                 flags=IGNORECASE)
            if next_closing_bracket is None:
                return

        new_start = next_closing_bracket.end()

    if view.substr(start) == items[0][-1]:
        start += 1

    nested = 0
    while True:
        next_opening_bracket = find_in_range(view, items[0],
                                             start=start,
                                             end=next_closing_bracket.b,
                                             flags=IGNORECASE)
        if not next_opening_bracket:
            break

        nested += 1
        start = next_opening_bracket.end()

    if nested > 0:
        return find_next_lone_bracket(view, next_closing_bracket.end(),
                                      items,
                                      nested)
    else:
        return next_closing_bracket


def find_prev_lone_bracket(view, start: int, tags, unbalanced: int = 0): # TODO: Extract common functionality from here and the % motion instead of duplicating code.
    if view.substr(start) == (tags[0][1] if len(tags[0]) > 1 else tags[0]):
        if not unbalanced and view.substr(start - 1) != '\\':
            return Region(start, start + 1)
    new_start = start
    for i in range(unbalanced or 1):
        prev_opening_bracket     = reverse_search_by_pt(view,tags[0],start=0,end=new_start,flags=IGNORECASE)
        if prev_opening_bracket is None: # Unbalanced tags; nothing we can do
            return
        while view.substr(prev_opening_bracket.begin() - 1) == '\\':
            prev_opening_bracket = reverse_search_by_pt(view,tags[0],start=0,end=prev_opening_bracket.begin(),
                flags=IGNORECASE)
            if prev_opening_bracket is None:
                return
        new_start = prev_opening_bracket.begin()
    nested = 0
    while True:
        next_closing_bracket = reverse_search_by_pt(view,tags[1],start=prev_opening_bracket.a,end=start,flags=IGNORECASE)
        if not next_closing_bracket:
            break
        nested += 1
        start = next_closing_bracket.begin()
    if nested > 0:
        return find_prev_lone_bracket(view, prev_opening_bracket.begin(), tags, nested)
    else:
        return prev_opening_bracket


def find_paragraph_text_object(view, s: Region, inclusive: bool = True, count: int = 1) -> Region:
    # In Vim, `vip` will select an inner paragraph -- all the lines having the
    # same whitespace status of the current location. And a `vap` will select
    # both the current inner paragraph (either whitespace or not) and the next
    # inner paragraph (the opposite).
    begin = None
    end = s.a
    for _ in range(count):
        b1, e1 = find_inner_paragraph(view, end)
        b2, end = find_inner_paragraph(view, e1) if inclusive else (b1, e1)
        if begin is None:
            begin = b1

    if begin is None:
        return Region(end)

    return Region(begin, end)


def find_sentences_forward(view, start, count: int = 1, stop_nl:bool=False):
    def _find_sentence_forward(view, start: int):
        char = view.substr(start)
        if char == '\n':
            next_sentence = view.find('\\s+', start)
        else:
            nl = '(\\n)|' if stop_nl else '' # stop at ␤ as text sentences don't have them
            next_sentence = view.find(nl + '([\\.\\?\\!][\\)\\]"\']*\\s)', start)
        if next_sentence:
            return next_non_blank(view, next_sentence.b)
    start = start.b if isinstance(start, Region) else start
    new_start = start
    for i in range(count):
        next_sentence = _find_sentence_forward(view, new_start)
        if not next_sentence:
            break
        new_start = next_sentence
    if new_start != start:
        return Region(new_start)


def find_sentences_backward(view, start_pt: int, count: int = 1, stop_nl:bool=False) -> Region:
    """ stop_nl = stop at ␤ instead of jumping through a huge block just because there is no 'text sentence.'"""
    pt   = prev_non_ws(view, start_pt)
    sen  = Region(pt)
    prev = sen
    while True:
        sen = view.expand_by_class(sen, CLASS_LINE_END | CLASS_PUNCTUATION_END)
        if sen.a <= 0\
            or         (view.substr(sen.begin()    ) == '\n' and stop_nl)\
            or          view.substr(sen.begin() - 1) in ('.','\n','?','!'):
            if          view.substr(sen.begin() - 1) == '.'\
                and not view.substr(sen.begin()    ) == ' ':
                continue
            if prev == sen:
                break
            prev = sen
            if sen:
                pt = next_non_blank(view, sen.a)
                if pt < sen.b and pt != start_pt:
                    if view.substr(pt) == '\n':
                        if  pt +  1 != start_pt:
                            pt += 1
                    return Region(pt)
                if pt > 0:
                    continue
            return sen
    return sen


def find_inner_paragraph(view, initial_loc):
    """
    Take a location, as an integer.

    Returns a (begin, end) tuple of ints for the Vim inner paragraph
    corresponding to that location. An inner paragraph consists of a set of
    contiguous lines all having the same whitespace status (a line either
    consists entirely of whitespace characters or it does not).
    """
    # Determine whether the initial point lies in an all-whitespace line.
    def is_whitespace(region):
        return len(view.substr(region).strip()) == 0

    iws = is_whitespace(view.line(initial_loc))

    # Search backward finding all lines with similar whitespace status.
    # This will give use the value for begin.
    p = initial_loc
    while True:
        line = view.line(p)
        if is_whitespace(line) != iws:
            break
        elif line.begin() == 0:
            p = 0
            break

        p = line.begin() - 1

    begin = p + 1 if p > 0 else p

    # To get the value for end, we do the same thing, this time searching forward.
    p = initial_loc
    while True:
        line = view.line(p)
        if is_whitespace(line) != iws:
            break

        p = line.end() + 1

        if p >= view.size():
            break

    end = p

    return (begin, end)


def resolve_indent_text_object(view, s: Region, inclusive: bool = True, big: bool = False):
    # Look for the minimum indentation in the current visual region.
    idnt = 1000
    idnt_pt = None
    for line in view.lines(s):
        if not re.match('^\\s*$', view.substr(line)):
            level = view.indentation_level(line.a)
            if level < idnt:
                idnt = min(idnt, level)
                idnt_pt = line.a

    # If the selection has no indentation at all, find which indentation level
    # is the largest, the previous non blank before tphe cursor or the next non
    # blank after the cursor, and start the selection from that point.

    if idnt == 1000:
        pnb_pt = prev_non_ws(view, s.begin())
        pnb_indent_level = view_indentation_level(view, pnb_pt)

        nnb_pt = next_non_ws(view, s.end())
        nnb_indent_level = view_indentation_level(view, nnb_pt)

        if pnb_indent_level > nnb_indent_level:
            idnt_pt = s.a = s.b = pnb_pt
        elif nnb_indent_level > pnb_indent_level:
            idnt_pt = s.a = s.b = nnb_pt
        else:
            idnt_pt = pnb_pt

    if idnt == 0 and idnt_pt is not None:
        expanded = view.expand_by_class(s, CLASS_EMPTY_LINE)
        s.a = expanded.a
        s.b = expanded.b

        if not inclusive:
            # Case: ii and iI. Strip any leading whitespace.
            leading_ws = view_find(view, '\\s*', s.a)
            if leading_ws is not None:
                s.a = view.line(leading_ws.b).a

            s.b = prev_non_blank(view, s.b)
        elif big:
            # Case: aI. Add a line below.
            if view.substr(s.b) == '\n':
                s.b += 1

    elif idnt > 0 and idnt_pt is not None:
        indented_region = view_indented_region(view, idnt_pt, inclusive)

        if indented_region.begin() < s.begin():
            s.a = indented_region.begin()

        if indented_region.end() > s.end():
            s.b = indented_region.end()

        if inclusive:
            # Case: ai. Add a line above.
            s.a = view.line(view.text_point(view.rowcol(s.a)[0] - 1, 0)).a

            # Case: aI. Add a line below.
            if big:
                s.b = view.full_line(view.text_point(view.rowcol(s.b - 1)[0] + 1, 0)).b

    return s


def find_line_text_object(view, s: Region) -> tuple:
    line = view.line(s)
    line_content = view.substr(line)

    begin = line.begin()
    end = line.end()

    whitespace_match = re.match("\\s+", line_content)
    if whitespace_match:
        begin = begin + len(whitespace_match.group(0))

    return (begin, end)


# TODO: Move this to units.py.
def word_reverse(view, pt: int, count: int = 1, big: bool = False) -> int:
    t = pt
    for _ in range(count):
        t = view.find_by_class(t, forward=False, classes=WORD_REVERSE_STOPS)
        if t == 0:
            break

        if big:
            # Skip over punctuation characters.
            while not ((view.substr(t - 1) in '\n\t ') or (t <= 0)):
                t -= 1

    return t


# TODO: Move this to units.py.
def big_word_reverse(view, pt: int, count: int = 1) -> int:
    return word_reverse(view, pt, count, big=True)


# TODO: Move this to units.py.
def word_end_reverse(view, pt: int, count: int = 1, big: bool = False, nosep:bool=False) -> int:
    t = pt
    for i in range(count):
        if big:
            while not ((view.substr(t - 1) in '\n\t ') or (t <= 0)): # Skip over punctuation characters.
                t -= 1
        # `ge` should stop at the previous word end if starting at a space immediately after a word.
        if (i == 0 and view.substr(t    ).isspace()\
            and    not view.substr(t - 1).isspace()):
            continue

        if (    not view.substr(t    ).isalnum()\
            and not view.substr(t    ).isspace()\
            and     view.substr(t - 1).isalnum() and t > 0):
            pass
        else:
            if nosep:
                t = view.find_by_class(t, forward=False, classes=WORD_END_REVERSE_STOPS_NOSEP)
            else:
                t = view.find_by_class(t, forward=False, classes=WORD_END_REVERSE_STOPS      )

        if t == 0:
            break

    return max(t - 1, 0)


# TODO: Move this to units.py.
def big_word_end_reverse(view, pt: int, count: int = 1) -> int:
    return word_end_reverse(view, pt, count, big=True)


def next_end_tag(view, pattern: str = RX_ANY_TAG, start: int = 0, end: int = -1) -> tuple:
    # Args:
    #   view (sublime.View)
    #   pattern (str)
    #   start (int)
    #   end (int)
    #
    # Returns:
    #   tuple[Region, str, bool]
    #   typle[None, None, None]
    region = view.find(pattern, start, IGNORECASE)
    if region.a == -1:
        return None, None, None

    match = re.search(pattern, view.substr(region))
    if match:
        return (region, match.group(1), match.group(0).startswith('</'))

    return None, None, None


def previous_begin_tag(view, pattern: str, start: int = 0, end: int = 0) -> tuple:
    assert pattern, 'bad call'
    region = reverse_search_by_pt(view, pattern, start, end, IGNORECASE)
    if not region:
        return None, None, None

    match = re.search(pattern, view.substr(region))
    if match:
        return (region, match.group(1), match.group(0)[1] != '/')

    return None, None, None


def get_region_end(r: Region) -> dict:
    return {'start': r.end()}


def get_region_begin(r: Region) -> dict:
    return {'start': 0, 'end': r.begin()}


def get_closest_tag(view, pt: int):
    # Args:
    #   view (sublime.View)
    #
    # Returns:
    #   Region|None
    substr = view.substr
    while substr(pt) != '<' and pt > 0:
        pt -= 1

    if substr(pt) != '<':
        return None

    next_tag = view.find(RX_ANY_TAG, pt)
    if next_tag.a != pt:
        return None

    return next_tag


def find_containing_tag(view, start: int) -> tuple:
    # Args:
    #   view (sublime.View)
    #
    # Returns:
    #   tuple[Region, Region, str]
    #   tuple[None, None, None]
    closest_tag = get_closest_tag(view, start)

    if not closest_tag:
        return None, None, None

    if closest_tag.contains(start) and view.substr(closest_tag)[1] == '/':
        start = closest_tag.a

    end_region, tag_name = next_unbalanced_tag(
        view,
        search=next_end_tag,
        search_args={'pattern': RX_ANY_TAG, 'start': start},
        restart_at=get_region_end
    )

    if not end_region:
        return None, None, None

    begin_region, _ = next_unbalanced_tag(
        view,
        search=previous_begin_tag,
        search_args={
            'pattern': RX_ANY_TAG_NAMED_TPL.format(tag_name),
            'start': 0,
            'end': end_region.a
        },
        restart_at=get_region_begin
    )

    if not begin_region:
        return None, None, None

    return begin_region, end_region, tag_name


def next_unbalanced_tag(view, search=None, search_args={}, restart_at=None, tags: list = []) -> tuple:
    # Args:
    #   view (sublime.View)
    #   search (callable)
    #   search_args (dict)
    #   restart_at (callable)
    #   tags (list[str])
    #
    # Returns:
    #   tuple[Region, str]
    #   tuple[None, None]
    assert search and restart_at, 'wrong call'
    region, tag, is_end_tag = search(view, **search_args)

    if not region:
        return None, None

    if not is_end_tag:
        tags.append(tag)
        search_args.update(restart_at(region))

        return next_unbalanced_tag(view, search, search_args, restart_at, tags)

    if not tags or (tag not in tags):
        return region, tag

    while tag != tags.pop():
        continue

    search_args.update(restart_at(region))

    return next_unbalanced_tag(view, search, search_args, restart_at, tags)


def find_next_item_match_pt(view, s: Region):
    pt = get_insertion_point_at_b(s)

    # Note that some item targets are added later in relevant contexts, for
    # example the item targets <> are added only when in a HTML/XML context.
    # TODO Default targets should be configurable, see :h 'matchpairs'.
    targets = '(){}[]'

    # If in a HTML/XML context, check if the cursor position is within a valid
    # tag e.g. <name>, and find the matching tag e.g. if inside an opening tag
    # then find the closing tag, if in a closing tag find the opening one.
    if view.match_selector(0, 'text.(html|xml)'):
        # Add valid HTML/XML item targets.
        targets += '<>'

        # Find matching HTML/XML items, but only if cursor is within a tag.
        if view.substr(pt) not in targets:
            closest_tag = get_closest_tag(view, pt)
            if closest_tag:
                if closest_tag.contains(pt):
                    begin_tag, end_tag, _ = find_containing_tag(view, pt)
                    if begin_tag:
                        return begin_tag.a + 1 if end_tag.contains(pt) else end_tag.a + 1

    # Find the next item after or under the cursor.
    bracket = view_find(view, '|'.join(map(re_escape, targets)), pt)
    if not bracket:
        return

    # Only accept items found within the current cursor line.
    if bracket.b > view.line(pt).b:
        return

    target = view.substr(bracket)
    target_index = targets.index(target)
    targets_open = targets[::2]
    forward = True if target in targets_open else False

    if target in targets_open:
        target_pair = (targets[target_index], targets[target_index + 1])
    else:
        target_pair = (targets[target_index - 1], targets[target_index])

    accepted_selector = 'punctuation|text.plain|comment'

    if forward:
        counter = 0
        start = bracket.b
        while True:
            bracket = view_find(view, '|'.join(map(re_escape, target_pair)), start)
            if not bracket:
                return

            if view.match_selector(bracket.a, accepted_selector):
                if view.substr(bracket) == target:
                    counter += 1
                else:
                    if counter == 0:
                        return bracket.a

                    counter -= 1

            start = bracket.b
    else:
        # Note the use of view_rfind_all(), because Sublime doesn't have any
        # APIs to do reverse searches and finding *all* matches before a point
        # is easier and more effiecient, at least in a userland implemention.
        counter = 0
        start = bracket.a
        for bracket in view_rfind_all(view, '|'.join(map(re_escape, target_pair)), start):
            if view.match_selector(bracket.a, accepted_selector):
                if view.substr(bracket) == target:
                    counter += 1
                else:
                    if counter == 0:
                        return bracket.a

                    counter -= 1

            start = bracket.a
