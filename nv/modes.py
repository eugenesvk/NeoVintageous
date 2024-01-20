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
class Mode(Flag):
  #↓ unique modes	          ↓ abbreviations
  Normal         	= auto(); N 	= Normal
  Insert         	= auto(); I 	= Insert
  Command        	= auto(); C 	= Command
  Visual         	= auto(); VV	= Visual
  VisualBlock    	= auto(); VB	= VisualBlock
  VisualLine     	= auto(); VL	= VisualLine
  Select         	= auto(); S 	= Select
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
  CmdTxt         	=     I                          | Motion
M = Mode # in Sublime's Py3.8 Enum Flag's members aren't iterable (need Py3.11)
M_EVENT  = [M.N,M.I    ,M.VV,M.VB,M.VL,M.S        ,M.R]
M_ANY    = [M.N,M.I,M.C,M.VV,M.VB,M.VL,M.S,M.O,M.T,M.R,M.Lng]
M_CMDTXT = [M.N,M.I    ,M.VV,M.VB,M.VL,M.S,M.O]


mode_names = { # unique text abbreviations per mode (combinations are handled in the Mode enum)
  Mode.N   	: ['Ⓝ','N'  	,'normal'                  	,NORMAL           	],
  Mode.I   	: ['ⓘ','I'  	,'insert'                  	,INSERT           	],
  Mode.C   	: ['Ⓒ','C'  	,'command','cli'           	                  	],
  Mode.VV  	: ['ⓋⓋ','VV'	,'visual'                  	,VISUAL           	],
  Mode.VB  	: ['▋','VB' 	,'visualblock','vblock'    	,VISUAL_BLOCK     	],
  Mode.VL  	: ['━','VL' 	,'visualline' ,'vline'     	,VISUAL_LINE      	],
  Mode.S   	: ['Ⓢ','S'  	,'select'                  	,SELECT           	],
  Mode.O   	: ['Ⓞ','O'  	,'operator'                	,OPERATOR_PENDING 	],
  Mode.T   	: ['Ⓣ','T'  	,'terminal','job'          	                  	],
  Mode.R   	: ['Ⓡ','R'  	,'replace'                 	,REPLACE          	],
  Mode.Lng 	: ['Ⓛ','L'  	,'language','lang'         	,'lng'            	],
  #        	  Combos    	                           	                  	#
  Mode.V   	: ['Ⓥ','V'  	,'vmap'                    	                  	],
  Mode.X   	: ['Ⓧ','X'  	,'xmap','Ⓥ³','V³','Ⓥ3','V3'	,'VVV','VLB','VBL'	],
  Mode.Map 	: ['Ⓜ','M'  	,'map'                     	                  	],
  Mode.MapN	: ['Ⓜ!','M!'	,'map!'                    	                  	],
}
MODE_HELP = """
┌────────┬─┬─┬─┬V┬V┬V┬─┬─┬─┬─┐
│   Mode→│N│I│C│V│L│B│S│O│T│L│
├↓Cmd────┼─┼─┼─┼─┼─┼─┼─┼─┼─┼─┤↓Icon
│  map   │•│ │ │•│•│•│•│•│ │ │Ⓜ
│  map!  │ │•│•│ │ │ │ │ │ │ │Ⓜ!
│v map   │ │ │ │•│•│•│•│ │ │ │Ⓥ
│x map   │ │ │ │•│•│•│ │ │ │ │Ⓧ
│l map   │ │•│•│ │ │ │ │ │ │•│none
│n map   │•│ │ │ │ │ │ │ │ │ │Ⓝ
│i map   │ │•│ │ │ │ │ │ │ │ │ⓘ
│c map   │ │ │•│ │ │ │ │ │ │ │Ⓒ
│        │ │ │ │•│ │ │ │ │ │ │ⓋⓋ
│        │ │ │ │ │•│ │ │ │ │ │━
│        │ │ │ │ │ │•│ │ │ │ │▋
│s map   │ │ │ │ │ │ │•│ │ │ │Ⓢ
│o map   │ │ │ │ │ │ │ │•│ │ │Ⓞ
│t map   │ │ │ │ │ │ │ │ │•│ │Ⓣ
│        │ │ │ │ │ │ │ │ │ │•│Ⓛ
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
      _log.error(f" ‘{mode_text}’ is not unique, check ‘mode_names’")
    else:
      mode_names_rev                   [mode_text    ]  = mode
      mode_clean_names_rev  [clean_name(mode_text    )] = mode
  if isinstance(mode_text, list): #['Ⓝ','N','normal',NORMAL]
    for         mode_text_str in mode_text:
      if mode_text_str in mode_names_rev:
        _log.error(f" ‘{mode_text_str}’ is not unique, check ‘mode_names’")
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
    _log.debug(f"parsed ‘{mode_str}’ into modes ‘{Mode.Any}’")
    return Mode.Any
  if not mode_str:
    _log.error(f"Expected a valid mode_str argument, not ‘{mode_str}’")
    return None
  if not (cfgT := type(mode_str)) is str:
    _log.error(f"Type of ‘{mode_str}’ should be str, not {cfgT}")
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
    _log.error(f"mode_str ‘{mode_str}’ has unrecognized modes ‘{mode_s_remain}’")
  if modes: # modes.name fails in py3.8?
    _log.debug(f"parsed ‘{mode_str}’ into modes ‘{modes}’")
    return modes
  else:
    _log.debug(f"no modes found in ‘{mode_str}’")
    return None

def text_to_mode_alone(mode_string:str): # convert user mode input like 'N' or 'normal' into an enum entry
  modes = text_to_modes(mode_string)
  if modes and hasattr(Mode, modes.name): # got a single enum, not a combo
    return modes
  else:
    return None
