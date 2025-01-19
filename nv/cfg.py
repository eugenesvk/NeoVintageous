import re
import logging
from typing  import Union
from pathlib import Path

import sublime
import sublime_plugin

import NeoVintageous.dep.kdl as kdl
import NeoVintageous.dep.kdl2 as kdl2
from NeoVintageous.nv.log import DEFAULT_LOG_LEVEL, TFMT
from NeoVintageous.plugin import PACKAGE_NAME

_log = logging.getLogger(__name__)
_log.setLevel(DEFAULT_LOG_LEVEL)
if _log.hasHandlers(): # clear existing handlers, including sublime's
    logging.getLogger(__name__).handlers.clear()
    # _log.addHandler(stream_handler)
_L = True if _log.isEnabledFor(logging.CFG) else False

_KDL_VERSION = 2

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
