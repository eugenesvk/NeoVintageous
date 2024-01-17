import logging

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
  Visual         	= auto(); X 	= Visual
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
  V              	=           X | S
  VVV            	=           V | VL | VB
  L              	=     I | C             | Lng
  MapN           	=	    I | C
  Map            	=	N |       V | S | O
  Action         	= N |       VVV
  Motion         	= N |       VVV   | O
  Event          	=     I                 | R | Action
M_EVENT = [Mode.Insert, Mode.Normal, Mode.Replace, Mode.Select, Mode.Visual, Mode.VisualBlock, Mode.VisualLine] # in Sublime's Python 3.8 Enum Flag doesn't support iteration on its members (added in 3.11)


mode_names = { # unique text abbreviations per mode (combinations are handled in the Mode enum)
  Mode.N   	: ['Ⓝ','N' 	,'normal'        	,NORMAL          	],
  Mode.I   	: ['ⓘ','I' 	,'insert'        	,INSERT          	],
  Mode.C   	: ['Ⓒ','C' 	,'command','cli' 	                 	],
  Mode.V   	: ['Ⓥ','V' 	,'visual'        	,VISUAL          	],
  Mode.VB  	: ['▋','VB'	,'visualblock'   	,VISUAL_BLOCK    	],
  Mode.VL  	: ['━','VL'	,'visualline'    	,VISUAL_LINE     	],
  Mode.S   	: ['Ⓢ','S' 	,'select'        	,SELECT          	],
  Mode.O   	: ['Ⓞ','O' 	,'operator'      	,OPERATOR_PENDING	],
  Mode.T   	: ['Ⓣ','T' 	,'terminal','job'	                 	],
  Mode.R   	: ['Ⓡ','R' 	,'replace'       	,REPLACE         	],
  Mode.L   	: ['Ⓛ','L' 	                 	                 	],
  Mode.X   	: ['Ⓧ','X' 	                 	                 	],
  Mode.Map 	: ['Ⓜ','M' 	,'map'           	                 	],
  Mode.MapN	: [        	 'map!'          	                 	],
}
#  Mode→  |Nor|Ins|Cmd|Vis|Sel|Opr|Term|Lng|
# ↓Cmd    +---+---+---+---+---+---+--- +---+
#   map   | • |   |   | • | • | • |    |   |
#   map!  |   | • | • |   |   |   |    |   |
# v map   |   |   |   | • | • |   |    |   |
# n map   | • |   |   |   |   |   |    |   |
# i map   |   | • |   |   |   |   |    |   |
# c map   |   |   | • |   |   |   |    |   |
# x map   |   |   |   | • |   |   |    |   |
# s map   |   |   |   |   | • |   |    |   |
# o map   |   |   |   |   |   | • |    |   |
# t map   |   |   |   |   |   |   | •  |   |
# l map   |   | • | • |   |   |   |    | • |
# Normal, Insert, Command-line, Visual, Select, Operator-pending, Terminal-Job, Lang-Arg

MODE_NAMES_OLD = { # ToDo: replace all with just enums, this is for temporary getting old names from the enums
  Mode.Insert         	: INSERT,
  Mode.InternalNormal 	: INTERNAL_NORMAL,
  Mode.Normal         	: NORMAL,
  Mode.OperatorPending	: OPERATOR_PENDING,
  Mode.Replace        	: REPLACE,
  Mode.Select         	: SELECT,
  Mode.Unknown        	: UNKNOWN,
  Mode.Visual         	: VISUAL,
  Mode.VisualBlock    	: VISUAL_BLOCK,
  Mode.VisualLine     	: VISUAL_LINE,
}
mode_names_rev = dict() # reverse mode dictionary for easier mapping of user strings to modes
for mode,mode_text in mode_names.items():
  if isinstance(mode_text, str):
    if   mode_text     in mode_names_rev:
      _log.debug(f" ‘{mode_text}’ is not unique, check ‘mode_names’")
    else:
      mode_names_rev  [mode_text]      = mode
  if isinstance(mode_text, list):
    for         mode_text_str in mode_text:
      if mode_text_str in mode_names_rev:
        _log.debug(f" ‘{mode_text_str}’ is not unique, check ‘mode_names’")
      else:
        mode_names_rev[mode_text_str]  = mode
# mode_names_rev { # print('mode_names_rev',mode_names_rev)
# Ⓥ         : <Mode.V: 72>,
# V          : <Mode.V: 72>,
# visual     : <Mode.V: 72>,
# mode_visual: <Mode.V: 72>, }

import re
resp  	= re.compile(r'\s+')
resubw	= re.compile(r'[-_]')
def text_to_modes(mode_string:str): # convert user mode input like 'NI' or 'normal' into enum entries
  mode = Mode(0)
  mode_list = resp.split(mode_string)
  for  mode_text in mode_list: # 'NI' or 'normal'
    mode_text_rep = resubw.sub('', mode_text.lower()) # 'Normal' → 'normal'
    if   mode_text     in mode_names_rev:
      mode     |= mode_names_rev[mode_text]
    elif mode_text_rep in mode_names_rev:
      mode     |= mode_names_rev[mode_text_rep]
    else: # 'NI' to 'N' and 'I'
      for  sym in mode_text:
        if sym in mode_names_rev:
          mode |= mode_names_rev[sym]
  if mode.name:
    return mode
  else:
    return None
def text_to_mode_alone(mode_string:str): # convert user mode input like 'N' or 'normal' into an enum entry
  modes = text_to_modes(mode_string)
  if modes and hasattr(Mode, modes.name): # got a single enum, not a combo
    return modes
  else:
    return None
