import re
import logging
from typing  import Union
from pathlib import Path

import sublime
import sublime_plugin

from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL, TFMT
from NeoVintageous.plugin import PACKAGE_NAME

_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)
if _log.hasHandlers(): # clear existing handlers, including sublime's
    logging.getLogger(__name__).handlers.clear()
    # _log.addHandler(stream_handler)
_L = True if _log.isEnabledFor(logging.CFG) else False

KDLV = 2

re_count = re.compile(r"[№⌗×⋅cn](\d+)")
re_subl_tag = re.compile(r"subl|sublime|st")
re_filetype = re.compile(r"[\s,]+")
_keybind_prop = {
  'desc':['d','des','desc','description','inf','info'],
  'icon':['i','icn','icon','img','image'],
  'type':['t','type'],
  'file':['ft','filetype'],
  'defk':['defk','default_key','≝k'],
  'defc':['defc','default_cmd','≝c'],
  }

DEF = dict()
DEF['res_tag'] = list() # internal command description tags, exclude these when parsing a sublime command so that it doesn't get arguments it can't understand
for dkey,key_abbrev in _keybind_prop.items(): # 'type':['t','type']
  for val in key_abbrev:                      #          t   type
    DEF['res_tag'].append(val)
DEF['var_def'] = ['‘','’']
DEF['general'] = {}
DEF['gen_def'] = { # todo: replace float with int when kdl-py issue is fixed
  # clean name                    	: dict(type   default value	 old/internal key name
  'defaultmode'                   	: dict(t=str ,v="normal"   	,key='default_mode'                       ),
  'resetmodewhenswitchingtabs'    	: dict(t=bool,v=False      	,key='reset_mode_when_switching_tabs'     ),
  'highlightedyank'               	: dict(t=bool,v=True       	,key='highlighted_yank'                   ),
  'highlightedyankduration'       	: dict(t=float,v=1000      	,key='highlighted_yank_duration'          ),
  'highlightedyankstyle'          	: dict(t=str ,v="fill"     	,key='highlighted_yank_style'             ),
  'searchcurstyle'                	: dict(t=str ,v="fill"     	,key='search_cur_style'                   ),
  'searchincstyle'                	: dict(t=str ,v="fill"     	,key='search_inc_style'                   ),
  'searchoccstyle'                	: dict(t=str ,v="fill"     	,key='search_occ_style'                   ),
  'bell'                          	: dict(t=str ,v="blink"    	,key='bell'                               ),
  'bellcolorscheme'               	: dict(t=str ,v="dark"     	,key='bell_color_scheme'                  ),
  'autonohlsearchonnormalenter'   	: dict(t=bool,v=True       	,key='auto_nohlsearch_on_normal_enter'    ),
  'enableabolish'                 	: dict(t=bool,v=True       	,key='enable_abolish'                     ),
  'enablecommentary'              	: dict(t=bool,v=True       	,key='enable_commentary'                  ),
  'enablemultiplecursors'         	: dict(t=bool,v=True       	,key='enable_multiple_cursors'            ),
  'enablesneak'                   	: dict(t=bool,v=True       	,key='enable_sneak'                       ),
  'enablesublime'                 	: dict(t=bool,v=True       	,key='enable_sublime'                     ),
  'enablesurround'                	: dict(t=bool,v=True       	,key='enable_surround'                    ),
  'enabletargets'                 	: dict(t=bool,v=True       	,key='enable_targets'                     ),
  'enableunimpaired'              	: dict(t=bool,v=True       	,key='enable_unimpaired'                  ),
  'usectrlkeys'                   	: dict(t=bool,v=True       	,key='use_ctrl_keys'                      ),
  'usesuperkeys'                  	: dict(t=bool,v=True       	,key='use_super_keys'                     ),
  'handlekeys'                    	: dict(t=dict,v={}         	,key='handle_keys'                        ),
  'iescapejj'                     	: dict(t=bool,v=True       	,key='i_escape_jj'                        ),
  'iescapejk'                     	: dict(t=bool,v=True       	,key='i_escape_jk'                        ),
  'nvⓘ⎋←ii'                       	: dict(t=bool,v=True       	,key='nvⓘ_⎋←ii'                          ),
  'nvⓘ⎋←;i'                       	: dict(t=bool,v=True       	,key='nvⓘ_⎋←;i'                          ),
  'usesysclipboard'               	: dict(t=bool,v=True       	,key='use_sys_clipboard'                  ),
  'clearautoindentonesc'          	: dict(t=bool,v=True       	,key='clear_auto_indent_on_esc'           ),
  'autocompleteexitfrominsertmode'	: dict(t=bool,v=True       	,key='auto_complete_exit_from_insert_mode'),
  'multicursorexitfromvisualmode' 	: dict(t=bool,v=False      	,key='multi_cursor_exit_from_visual_mode' ),
  'lspsave'                       	: dict(t=bool,v=False      	,key='lsp_save'                           ),
  'shellsilent'                   	: dict(t=bool,v=False      	,key='shell_silent'                       ),
  'showmarksingutter'             	: dict(t=bool,v=True       	,key='show_marks_in_gutter'               ),
  'sneakuseicscs'                 	: dict(t=float,v=1         	,key='sneak_use_ic_scs'                   ),
  'exitwhenquittinglastwindow'    	: dict(t=[bool,str],v=True 	,key='exit_when_quitting_last_window'     ),
  'source'                        	: dict(t=str ,v=''         	,key='source'                             ),
  'autoswitchinputmethod'         	: dict(t=bool,v=False      	,key='auto_switch_input_method'           ),
  'autoswitchinputmethoddefault'  	: dict(t=str ,v=''         	,key='auto_switch_input_method_default'   ),
  'autoswitchinputmethodgetcmd'   	: dict(t=str ,v=''         	,key='auto_switch_input_method_get_cmd'   ),
  'autoswitchinputmethodsetcmd'   	: dict(t=str ,v=''         	,key='auto_switch_input_method_set_cmd'   ),
}

import copy
CFG = copy.deepcopy(DEF) # copy defaults to be able to reset values on config reload
