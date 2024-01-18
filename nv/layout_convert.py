import sublime
import sublime_plugin

import NeoVintageous.dep.json5kit as json5kit # noqa: F401,F403
from NeoVintageous.dep.json5kit import Json5Node, Json5Array, Json5String # noqa: F401,F403
from NeoVintageous.plugin import PACKAGE_NAME

statusName	= f"07_{PACKAGE_NAME}"	# number defines the order of custom status bar statuses

import logging
log = logging.getLogger(__name__)
log.setLevel(logging.WARN)

from NeoVintageous.nv.log import LogToStatus
_l = LogToStatus()
_l.tag = statusName



from pathlib import Path
import re
import json

from NeoVintageous.nv.rc import cfgU
from NeoVintageous.nv.settings import get_config

def getUserKeymap(keymap_len) -> dict:
  win      	= sublime.active_window()
  view     	= win.active_view()
  cfg_fname	= cfgU.cfg_f.name

  if not hasattr(cfgU,'kdl') or (cfg := cfgU.kdl.get('keymap',None)) is None: # skip on initial import when Plugin API isn't ready, so no settings are loaded
    msg_error = f"no ‘keymap’ settings found in ‘{cfg_fname}’"
    # log.error(msg_error); _l.s(view, msg_error)
    log.info(msg_error) # config is optional
    return

  keymap = dict()
  for cfg_field in ['lower','upper']: # mandatory
    if (cfg_value := get_config('keymap'+'.'+cfg_field)):
      keymap[cfg_field] = cfg_value
    else:
      msg_error = f"‘keymap’ config group has no ‘{cfg_field}’ field (in ‘{cfg_fname}’)"
      log.error(msg_error); _l.s(view, msg_error)
      return
  for cfg_field in ['alias']: # optional
    keymap[cfg_field] = get_config('keymap'+'.'+cfg_field)

  low = re.sub(r'\s','',keymap['lower'])
  upp = re.sub(r'\s','',keymap['upper'])
  if not (ln := len(low)) == keymap_len:
    msg_error = f"‘keymap’ config group's ‘lower’ field should have ‘{keymap_len}’ characters, not ‘{ln}’ (in ‘{cfg_fname}’)"
    log.error(msg_error); _l.s(view, msg_error)
    return
  if not (ln := len(upp)) == keymap_len:
    msg_error = f"‘keymap’ config group's ‘upper’ field should have ‘{keymap_len}’ characters, not ‘{ln}’ (in ‘{cfg_fname}’)"
    log.error(msg_error); _l.s(view, msg_error)
    return

  return({"low":low,"upp":upp,"alias":keymap['alias']})

from NeoVintageous.nv.helper import Singleton, Symbol
from enum import Enum
class lyt(Enum):
  qwerty      = Symbol('qwerty')
  dvorak      = Symbol('dvorak')
  colemak     = Symbol('colemak')
  workman     = Symbol('workman')
  asset       = Symbol('asset')
  colemak_dh  = Symbol('colemak_dh')
  neo2        = Symbol('neo2')
  ru_pc       = Symbol('ru_pc')
  ru_mac      = Symbol('ru_mac')
  user        = Symbol('user')

class LayoutConverter:
  def __init__(self):
    self.isUser   = False
    self.isAlias  = False
    layout_str        = {
      lyt.qwerty      :{'low' : R'''`1234567890-=\ qwertyuiop[] asdfghjkl;' zxcvbnm,./'''
       ,                'upp' : R'''~!@#$%^&*()_+| QWERTYUIOP{} ASDFGHJKL:" ZXCVBNM<>?'''},
      lyt.dvorak      :{'low' : R'''`1234567890[]\ ',.pyfgcrl/= aoeuidhtns- ;qjkxbmwvz'''
       ,                'upp' : R'''~!@#$%^&*(){}| "<>PYFGCRL?+ AOEUIDHTNS_ :QJKXBMWVZ'''},
      lyt.colemak     :{'low' : R'''`1234567890-=\ qwfpgjluy;[] arstdhneio' zxcvbkm,./'''
       ,                'upp' : R'''~!@#$%^&*()_+| QWFPGJLUY:{} ARSTDHNEIO" ZXCVBKM<>?'''},
      lyt.workman     :{'low' : R'''`1234567890-=\ qdrwbjfup;[] ashtgyneoi' zxmcvkl,./'''
       ,                'upp' : R'''~!@#$%^&*()_+| QDRWBJFUPP{} ASHTGYNEOI" ZXMCVKL<>?'''},
      lyt.asset       :{'low' : R'''`1234567890-=\ qwjfgypul;[] asetdhnior' zxcvbkm,./'''
       ,                'upp' : R'''~!@#$%^&*()_+| QWJFGYPUL;{} ASETDHNIO:" ZXCVBKM<>?'''},
      lyt.colemak_dh  :{'low' : R'''`1234567890-=\ qwfpbjluy;[] arstgkneio' zxcdvmh,./'''
       ,                'upp' : R'''~!@#$%^&*()_+| QWFPBJLUY:{} ARSTGKNEIO" ZXCDVMH<>?'''},
      lyt.neo2        :{'low' : R'''^1234567890-`\ xvlcwkhgfqß´ uiaeosnrtdy üöäpzbm,.j'''
       ,                'upp' : R'''ˇ°§ℓ»«$€„“”—¸| XVLCWKHGFQẞ˜ UIAEOSNRTDY ÜÖÄPZBM–•J'''},
      lyt.ru_pc       :{'low' : R'''ё1234567890-=\ йцукенгшщзхъ фывапролджэ ячсмитьбю.'''
       ,                'upp' : R'''Ё!"№;%:?*()_+/ ЙЦУКЕНГШЩЗХЪ ФЫВАПРОЛДЖЭ ЯЧСМИТЬБЮ,'''},
      lyt.ru_mac      :{'low' : R''']1234567890-=ё йцукенгшщзхъ фывапролджэ ячсмитьбю/'''
       ,                'upp' : R'''[!"№;%,.;()_+Ё ЙЦУКЕНГШЩЗХЪ ФЫВАПРОЛДЖЭ ЯЧСМИТЬБЮ?'''},
    }
    for k,v in layout_str.items():
      v['low'] = v['low'].replace(' ','')
      v['upp'] = v['upp'].replace(' ','')
    keymap_len  = len(layout_str[lyt.qwerty]['low'])

    userKeymap = getUserKeymap(keymap_len)
    if userKeymap:
      layout_str[lyt.user] = userKeymap
      self.isUser = True
      if userKeymap['alias']:
        self.isAlias = True

    translations = dict() # generate translation dictionaries for use in str.translate(dict)
    for   layout_from in layout_str:
      translations[layout_from] = dict()
      for layout_to   in layout_str:
        string_from = layout_str[layout_from  ]['low'] + layout_str[layout_from ]['upp']
        string_to   = layout_str[layout_to    ]['low'] + layout_str[layout_to   ]['upp']
        translations[layout_from][layout_to] =  str.maketrans(string_from, string_to)
    self.layout_str   = layout_str
    self.layouts      = list(layout_str.keys())
    self.translations = translations

  def convert(self, src, layout_from, layout_to):
    view          = sublime.active_window().active_view()
    translations  = self.translations
    layouts       = self.layouts
    if not layout_from in layouts: # todo: or fail silently and return src?
      msg_error = f"‘{layout_from}’ invalid, must be one of '{layouts}')"
      log.error(msg_error); _l.s(view, msg_error)
      return None
    if not layout_to   in layouts:
      msg_error = f"‘{layout_to}’ invalid, must be one of '{layouts}')"
      log.error(msg_error); _l.s(view, msg_error)
      return None
    return src.translate(translations[layout_from][layout_to])
