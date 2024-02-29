import logging
import re
from typing import Union

from NeoVintageous.nv.cfg_parse import clean_name

from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL
_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)

INSERT          	= 'mode_insert'
INTERNAL_NORMAL 	= 'mode_internal_normal'
NORMAL          	= 'mode_normal'
OPERATOR_PENDING	= 'mode_operator_pending'
REPLACE         	= 'mode_replace'
SELECT          	= 'mode_select'
UNKNOWN         	= 'mode_unknown'
VISUAL          	= 'mode_visual'
VISUAL_BLOCK    	= 'mode_visual_block'
VISUAL_LINE     	= 'mode_visual_line'

from enum import auto, Flag, IntFlag
class Mode(IntFlag):
  #↓ unique modes	          ↓ abbreviations
  Normal         	= auto(); N 	= Normal
  Insert         	= auto(); I 	= Insert
  Visual         	= auto(); VV	= Visual
  VisualBlock    	= auto(); VB	= VisualBlock
  VisualLine     	= auto(); VL	= VisualLine
  Select         	= auto(); S 	= Select
  Command        	= auto(); C 	= Command
  OperatorPending	= auto(); O 	= OperatorPending
  Terminal       	= auto(); T 	= Terminal
  Replace        	= auto(); R 	= Replace
  Lng            	= auto()
  Empty          	= auto()
  Unknown        	= auto()
  InternalNormal 	= auto()
  #↓ combo       	abbreviations
  X              	=           VV| VL| VB
  V              	=           X | S
  L              	=     I | C                | Lng
  MapN           	=     I | C
  Map            	= N |       X | S | O
  Action         	= N |       X
  Motion         	= N |       X     | O
  Event          	=     I                | R       | Action
  Any            	= Map | MapN           | T | Lng
  CmdTxt         	=     I                          | Map
  def __format__(self, spec):
    """ print an icon of a (group of) mode(s) like f"{Mode.N:®} or :i"""
    ret = ''
    s_remain = self
    if spec in ['®','i','icon','img','image']:
      if s_remain == Mode.Map           : # group modes
        ret += 'Ⓜ'
        s_remain ^= (s_remain & Mode.Map) # cut off all the modes that are part of the group
      if s_remain == Mode.MapN          :
        ret += 'Ⓜ!'
        s_remain ^= (s_remain & Mode.MapN)
      if s_remain == Mode.V             :
        ret += 'Ⓥ'
        s_remain ^= (s_remain & Mode.V)
      if s_remain == Mode.X             :
        ret += 'Ⓧ'
        s_remain ^= (s_remain & Mode.X)
      if s_remain & Mode.Normal         : # individual modes
        ret += "Ⓝ"
        s_remain ^= Mode.Normal
      if s_remain & Mode.Insert         :
        ret += "ⓘ"
        s_remain ^= Mode.Insert
      if s_remain & Mode.Command        :
        ret += "Ⓒ"
        s_remain ^= Mode.Command
      if s_remain & Mode.Visual         :
        ret += "ⓋⓋ"
        s_remain ^= Mode.Visual
      if s_remain & Mode.VisualBlock    :
        ret += "▋"
        s_remain ^= Mode.VisualBlock
      if s_remain & Mode.VisualLine     :
        ret += "━"
        s_remain ^= Mode.VisualLine
      if s_remain & Mode.Select         :
        ret += "Ⓢ"
        s_remain ^= Mode.Select
      if s_remain & Mode.OperatorPending:
        ret += "Ⓞ"
        s_remain ^= Mode.OperatorPending
      if s_remain & Mode.Terminal       :
        ret += "Ⓣ"
        s_remain ^= Mode.Terminal
      if s_remain & Mode.Replace        :
        ret += "Ⓡ"
        s_remain ^= Mode.Replace
      if s_remain & Mode.Lng            :
        ret += "Ⓛ"
        s_remain ^= Mode.Lng
      if s_remain & Mode.InternalNormal :
        ret += ""
        s_remain ^= Mode.InternalNormal
      if s_remain & Mode.Unknown        :
        ret += "❓"
        s_remain ^= Mode.Unknown
      if s_remain & Mode.Empty          :
        ret += "␀"
        s_remain ^= Mode.Empty
      if s_remain                       :
        ret += "{s_remain.name}"
        s_remain = Mode(0)
      if ret:
        return ret
    return f"{self.name}"
M = Mode # in Sublime's Py3.8 Enum Flag's members aren't iterable (need Py3.11)
M_EVENT  = [M.N,M.I    ,M.VV,M.VB,M.VL,M.S        ,M.R]
M_ANY    = [M.N,M.I,M.C,M.VV,M.VB,M.VL,M.S,M.O,M.T,M.R,M.Lng]
M_CMDTXT = [M.N,M.I    ,M.VV,M.VB,M.VL,M.S,M.O]


mode_names = { # unique text abbreviations per mode (combinations are handled in the Mode enum)
  Mode.N   	: [f"{M.N:®}",'N'    	,'normal'                  	,NORMAL           	],
  Mode.I   	: [f"{M.I:®}",'I'    	,'insert'                  	,INSERT           	],
  Mode.C   	: [f"{M.C:®}",'C'    	,'command','cli'           	                  	],
  Mode.VV  	: [f"{M.VV:®}",'VV'  	,'visual'                  	,VISUAL           	],
  Mode.VB  	: [f"{M.VB:®}",'VB'  	,'visualblock','vblock'    	,VISUAL_BLOCK     	],
  Mode.VL  	: [f"{M.VL:®}",'VL'  	,'visualline' ,'vline'     	,VISUAL_LINE      	],
  Mode.S   	: [f"{M.S:®}",'S'    	,'select'                  	,SELECT           	],
  Mode.O   	: [f"{M.O:®}",'O'    	,'operator'                	,OPERATOR_PENDING 	],
  Mode.T   	: [f"{M.T:®}",'T'    	,'terminal','job'          	                  	],
  Mode.R   	: [f"{M.R:®}",'R'    	,'replace'                 	,REPLACE          	],
  Mode.Lng 	: [f"{M.Lng:®}",'L'  	,'language','lang'         	,'lng'            	],
  #        	  Combos             	                           	                  	#
  Mode.V   	: [f"{M.V:®}",'V'    	,'vmap'                    	                  	],
  Mode.X   	: [f"{M.X:®}",'X'    	,'xmap','Ⓥ³','V³','Ⓥ3','V3'	,'VVV','VLB','VBL'	],
  Mode.Map 	: [f"{M.Map:®}",'M'  	,'map'                     	                  	],
  Mode.MapN	: [f"{M.MapN:®}",'M!'	,'map!'                    	                  	],
}
MODE_HELP = f"""
┌────────┬─┬─┬─┬V┬V┬V┬─┬─┬─┬─┐
│   Mode→│N│I│C│V│L│B│S│O│T│L│
├↓Cmd────┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┤↓Icon
│  map   │•│ │ │•│•│•│•│•│ │ │{M.Map:®}
│  map!  │ │•│•│ │ │ │ │ │ │ │{M.MapN:®}
│v map   │ │ │ │•│•│•│•│ │ │ │{M.V:®}
│x map   │ │ │ │•│•│•│ │ │ │ │{M.X:®}
│l map   │ │•│•│ │ │ │ │ │ │•│none
│n map   │•│ │ │ │ │ │ │ │ │ │{M.N:®}
│i map   │ │•│ │ │ │ │ │ │ │ │{M.I:®}
│c map   │ │ │•│ │ │ │ │ │ │ │{M.C:®}
│        │ │ │ │•│ │ │ │ │ │ │{M.VV:®}
│        │ │ │ │ │•│ │ │ │ │ │{M.VL:®}
│        │ │ │ │ │ │•│ │ │ │ │{M.VB:®}
│s map   │ │ │ │ │ │ │•│ │ │ │{M.S:®}
│o map   │ │ │ │ │ │ │ │•│ │ │{M.O:®}
│t map   │ │ │ │ │ │ │ │ │•│ │{M.T:®}
│        │ │ │ │ │ │ │ │ │ │•│{M.Lng:®}
└────────┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┘
Normal Insert Command-line Visual Visual-Linewise Visual-Blockwise Select Operator-pending Terminal-Job Lang-Arg
"""

MODE_NAMES_OLD = { # ToDo: replace all with just enums, this is for temporary getting old names from the enums
  Mode.Normal         	: NORMAL,
  Mode.Insert         	: INSERT,
  Mode.Visual         	: VISUAL,
  Mode.VisualBlock    	: VISUAL_BLOCK,
  Mode.VisualLine     	: VISUAL_LINE,
  Mode.Select         	: SELECT,
  Mode.OperatorPending	: OPERATOR_PENDING,
  Mode.Replace        	: REPLACE,
  Mode.InternalNormal 	: INTERNAL_NORMAL,
  Mode.Unknown        	: UNKNOWN,
}
mode_names_rev = dict() # reverse mode dictionary for easier mapping of user strings to modes
mode_clean_names_rev = dict() # with clean names for easier clean text name matching
for mode,mode_text in mode_names.items():
  # Mode.N  ['Ⓝ','N','normal',NORMAL]
  if isinstance(mode_text, str): #'N'
    if   mode_text     in mode_names_rev:
      _log.error(" ‘%s’ is not unique, check ‘mode_names’",mode_text)
    else:
      mode_names_rev                   [mode_text    ]  = mode
      mode_clean_names_rev  [clean_name(mode_text    )] = mode
  if isinstance(mode_text, list): #['Ⓝ','N','normal',NORMAL]
    for         mode_text_str in mode_text:
      if mode_text_str in mode_names_rev:
        _log.error(" ‘%s’ is not unique, check ‘mode_names’",mode_text_str)
      else:
        mode_names_rev                 [mode_text_str]  = mode
        mode_clean_names_rev[clean_name(mode_text_str)] = mode
# mode_names_rev { # print('mode_names_rev',mode_names_rev)
# Ⓥ         : <Mode.V: 72>,
# V          : <Mode.V: 72>,
# visual     : <Mode.V: 72>,
# mode_visual: <Mode.V: 72>, }
mode_names_sort           	= list(mode_names_rev      .keys())
mode_clean_names_sort     	= list(mode_clean_names_rev.keys())
mode_names_sort      .sort	(key=len,reverse=True)
mode_clean_names_sort.sort	(key=len,reverse=True)
re_flags = 0
re_flags |= re.MULTILINE | re.IGNORECASE
mode_names_re      	= re.compile("|".join(re.escape(x) for x in mode_names_sort      ), flags=re_flags)
mode_clean_names_re	= re.compile("|".join(re.escape(x) for x in mode_clean_names_sort), flags=re_flags)

def text_to_modes(mode_str:Union[str,None]):
  """convert an abbreviated mode string ‘mode_normalIvb’ to mode enum ‘M.Normal|M.Insert|M.VisualBlock’"""
  if mode_str is None:
    _log.debug("parsed ‘%s’ into modes ‘%s’",mode_str,Mode.Any)
    return Mode.Any
  if not mode_str:
    _log.error("Expected a valid mode_str argument, not ‘%s’",mode_str)
    return None
  if not (cfgT := type(mode_str)) is str:
    _log.error("Type of ‘%s’ should be str, not ‘%s’",mode_str,cfgT)
    return None

  modes = Mode(0)
  mode_s = clean_name(mode_str)
  mode_s_list = [] # mode_names_re has longest→shortest regex match to avoid N from matching mode_Normal
  mode_s_list.extend([i for i in mode_clean_names_re.findall(mode_s)])
  for mode_s_match in mode_s_list:
    if (mode := mode_clean_names_rev.get(mode_s_match,None)):
      modes |= mode
  if (mode_s_remain := mode_clean_names_re.sub('', mode_s)):
    # mode_s_list_up = [i.upper() for i in mode_s_list if len(i) == 1]
    _log.error("mode_str ‘%s’ has unrecognized modes ‘%s’",mode_str,mode_s_remain)
  if modes: # modes.name fails in py3.8?
    _log.debug("parsed ‘%s’ into modes ‘%s’",mode_str,modes)
    return modes
  else:
    _log.debug("no modes found in ‘%s’",mode_str)
    return None

def text_to_mode_alone(mode_string:str): # convert user mode input like 'N' or 'normal' into an enum entry
  modes = text_to_modes(mode_string)
  if modes and hasattr(Mode, modes.name): # got a single enum, not a combo
    return modes
  else:
    return None


def mode_full_to_abbrev(mode_full:str,i=1):
  if not mode_full or len(mode_full) == 1:
    return mode_full
  return mode_names[mode_names_rev[mode_full]][i] # mode_names = {Mode.N:['Ⓝ','N','normal',NORMAL]

def mode_group_sort(modes:Union[list,M], filler:str='') -> list:
  """group individual modes (VV+VB+VL=V) and sort to move NIV first"""
  sort_order   = [[M.Map,M.N],[M.I],[M.V,M.X,M.VV]]
  m_enum = M(0)
  if   isinstance(modes, list):
    for m in modes: # convert to enum
      m_enum |= mode_names_rev.get(m,M(0))
  elif isinstance(modes, M):
    m_enum = modes
  else:
    print(f"Modes should be of type list or Mode, not ‘{type(modes)}’")
    return []

  mode_l_sort = []
  filler = '' # '_'
  for   mgroup in sort_order: # move grouped then NIV modes first, ordered
    isFill = True # if no single mode from a group matches, add a filler
    for m in mgroup:
      mode_sym = mode_names[m][0]
      if m in m_enum:
        mode_l_sort += [mode_sym]
        m_enum      ^= m      # remove
        isFill       = False  # don't add filler since at least 1 from mode group matched
    if isFill:
      mode_l_sort += [filler]
  for m in M_ANY: # TODO: m_enum iteration fails in py3.8
    if m & m_enum:
      mode_sym = mode_names[m][0]
      mode_l_sort += [mode_sym] # add the remaining modes
  # print(f"from {modes} to {mode_l_sort}")
  return (mode_l_sort,m_enum)
