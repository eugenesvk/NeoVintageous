SEQ = dict()

# ToDo: simplify config keymap and have S-a everywhere instead of A to be consistent with S-f1
  # but need to retain the old A and <M-A> notation since user configs use it, so not worth it
# ToDo: add a Shifted function instead of Upper to also work with 9→( and [→{
_sep = ' '
_mod2vim = {"⇧":"", "⎈":"C-", "⇧⎈":"C-", "⎇":"M-", "":""}
NAMED_KEY_ALIASES = {
  'enter' 	: 'cr',
  'return'	: 'cr',
  '⏎'     	: 'cr',
  '⌤'     	: 'cr',
  '↩'     	: 'cr',
  '▲'     	: 'up',
  '▼'     	: 'down',
  '◀'     	: 'left',
  '▶'     	: 'right',
  '⇟'     	: 'pagedown',
  '⇞'     	: 'pageup',
  '␈'     	: 'bs',
  '⌫'     	: 'bs',
  '␡'     	: 'del',
  '⌦'     	: 'del',
  '␠'     	: 'space',
  '␣'     	: 'space',
  '⭾'     	: 'tab',
  '↹'     	: 'tab',
  '⇤'     	: 'home',
  '⤒'     	: 'home',
  '↖'     	: 'home',
  '🏠'     	: 'home',
  '🏡'     	: 'home',
  '⌂'     	: 'home',
  '⇥'     	: 'end',
  '⤓'     	: 'end',
  '↘'     	: 'end',
  '⎋'     	: 'esc',
  '⧵'     	: 'bslash',
  '＼'     	: 'bslash',
  '﹨'     	: 'bslash',
  '⎀'     	: 'insert',
  'Ⓛ'     	: 'leader',
}


_letters = { # space-separated lists of keycaps
  "function"  	: {"keycaps":"1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20", "mods":[
    {"mLbl"   	: None ,"varLbl":"F"   ,"preVal":"<","valLbl":"f"  ,"posVal":">"},
    {"mLbl"   	: "⇧" ,"varLbl":"F"   ,"preVal":"<","valLbl":"S-f" ,"posVal":">"},
    #         	   ↑↓ requires manual "S-" since special keys don't get Capitalized
    {"mLbl"   	: "⇧⎈","varLbl":"F"  ,"preVal":"<","valLbl":"S-f" ,"posVal":">"},
    {"mLbl"   	: "⎈" ,"varLbl":"F"   ,"preVal":"<","valLbl":"f"  ,"posVal":">"},
    ]}        	,
  "number"    	: {"keycaps":"1 2 3 4 5 6 7 8 9 0","mods":[
    {"mLbl"   	: None,"preVal":"" ,"posVal":""},
    {"mLbl"   	: "⎈","preVal":"<","posVal":">"},
    ]}        	,
  "unimpaired"	: {"keycaps":"q w e r t y u i o p a s d f g h j k l z x c v b n m","mods":[
    {"mLbl"   	: None,"preVar":"[","preVal":"","valLbl":"[" ,"posVal":""},
    # {"mLbl" 	: "⎈","preVar":"["   ,"preVal":"","valLbl":"["  ,"posVal":""},
    {"mLbl"   	: "⇧","preVar":"["   ,"preVal":"","valLbl":"["  ,"posVal":""},
    {"mLbl"   	: None,"preVar":"]","preVal":"","valLbl":"]" ,"posVal":""},
    # {"mLbl" 	: "⎈","preVar":"]"   ,"preVal":"","valLbl":"]"  ,"posVal":""},
    {"mLbl"   	: "⇧","preVar":"]"   ,"preVal":"","valLbl":"]"  ,"posVal":""},
    ]}        	,
  "keypad"    	: {"keycaps":"1 2 3 4 5 6 7 8 9 0","mods":[
    {"mLbl"   	: None,"varLbl":"🔢","preVal":"<","valLbl":"k" ,"posVal":">"},
    ]}        	,
  "qwerty"    	: {"keycaps":"q w e r t y u i o p", "mods":[
    {"mLbl"   	: None , "preVal":"" ,"posVal":""},
    {"mLbl"   	: "⇧" , "preVal":"" ,"posVal":""},
    {"mLbl"   	:  "⎈", "preVal":"<","posVal":">"},
    {"mLbl"   	: "⇧⎈", "preVal":"<","posVal":">"},
    ]}        	,
  "asdf"      	: {"keycaps":"a s d f g h j k l", "mods":[
    {"mLbl"   	: None , "preVal":"" ,"posVal":""},
    {"mLbl"   	: "⇧" , "preVal":"" ,"posVal":""},
    {"mLbl"   	:  "⎈", "preVal":"<","posVal":">"},
    {"mLbl"   	: "⇧⎈", "preVal":"<","posVal":">"},
    ]}        	,
  "zxcv"      	: {"keycaps":"z x c v b n m", "mods":[
    {"mLbl"   	: None , "preVal":"" ,"posVal":""},
    {"mLbl"   	: "⇧" , "preVal":"" ,"posVal":""},
    {"mLbl"   	:  "⎈", "preVal":"<","posVal":">"},
    {"mLbl"   	: "⇧⎈", "preVal":"<","posVal":">"},
    ]}        	,
  "punct"     	: {"keycaps":"& @ ` : , $ . \" = - # % + ? ' { } ( ) [ ] ; / * ~ _ ^", "mods":[
    {"mLbl"   	: None , "preVal":"" ,"posVal":""},
    {"mLbl"   	: "⇧" , "preVal":"" ,"posVal":""},
    {"mLbl"   	:  "⎈", "preVal":"<","posVal":">"},
    {"mLbl"   	: "⇧⎈", "preVal":"<","posVal":">"},
    ]}        	,
  "sub_a"     	: {"keycaps":"q w e r t y u i o p a s d f g h j k l z x c v b n m","mods":[
    {"mLbl"   	: None,"preVar":"a","preVal":"","preVal":"a"},
    {"mLbl"   	: "⇧","preVar":"a","preVal":"","preVal":"a"},
    ]}        	,
  "sub_c"     	: {"keycaps":"q w e r t y u i o p a s d f g h j k l z x c v b n m","mods":[
    {"mLbl"   	: None,"preVar":"c","preVal":"","preVal":"c"},
    {"mLbl"   	: "⇧","preVar":"c","preVal":"","preVal":"c"},
    ]}        	,
  "sub_d"     	: {"keycaps":"q w e r t y u i o p a s d f g h j k l z x c v b n m","mods":[
    {"mLbl"   	: None,"preVar":"d","preVal":"","preVal":"d"},
    {"mLbl"   	: "⇧","preVar":"d","preVal":"","preVal":"d"},
    ]}        	,
  "sub_g"     	: {"keycaps":"q w e r t y u i o p a s d f g h j k l z x c v b n m","mods":[
    {"mLbl"   	: None,"preVar":"g","preVal":"","preVal":"g"},
    {"mLbl"   	: "⇧","preVar":"g","preVal":"","preVal":"g"},
    ]}        	,
  "sub_y"     	: {"keycaps":"q w e r t y u i o p a s d f g h j k l z x c v b n m","mods":[
    {"mLbl"   	: None,"preVar":"y","preVal":"","preVal":"y"},
    {"mLbl"   	: "⇧","preVar":"y","preVal":"","preVal":"y"},
    ]}        	,
  "sub_z"     	: {"keycaps":"q w e r t y u i o p a s d f g h j k l z x c v b n m","mods":[
    {"mLbl"   	: None,"preVar":"z","preVal":"","preVal":"z"},
    {"mLbl"   	: "⇧","preVar":"z","preVal":"","preVal":"z"},
    ]}        	,
  "symbol"    	: {"keycaps":list(NAMED_KEY_ALIASES.keys()),"mods":[
    {"mLbl"   	: None ,"varLbl":""   ,"preVal":"<","valLbl":""  ,"posVal":">"},
    {"mLbl"   	: "⇧" ,"varLbl":""   ,"preVal":"<","valLbl":"S-" ,"posVal":">"},
    #         	   ↑↓ requires manual "S-" since special keys don't get Capitalized
    {"mLbl"   	: "⇧⎈","varLbl":""  ,"preVal":"<","valLbl":"S-" ,"posVal":">"},
    {"mLbl"   	: "⎈" ,"varLbl":""   ,"preVal":"<","valLbl":""  ,"posVal":">"},
    {"mLbl"   	: "⎇" ,"varLbl":""   ,"preVal":"<","valLbl":""  ,"posVal":">"},
    ]}
}

from NeoVintageous.nv.layout_convert	import lyt, LayoutConverter
lyt_converter   = LayoutConverter()

for lbl, row in _letters.items():
  keycaps	= row["keycaps"].split(_sep) if (type(row["keycaps"]) == str) else row["keycaps"]
  mods   	= row["mods"]
  for mod in mods:
    modVar	= mod["mLbl"] if mod["mLbl"] else ''
    modVal	= _mod2vim[modVar]
    preVar	= mod["preVar"] if "preVar" in mod else ""
    varLbl	= mod["varLbl"] if "varLbl" in mod else ""
    preVal	= mod["preVal"] if "preVal" in mod else ""
    valLbl	= mod["valLbl"] if "valLbl" in mod else ""
    posVal	= mod["posVal"] if "posVal" in mod else ""
    # print(f"mod={mod}")
    # print(f"var= val= val_als= (key_vim= _als=)")
    for key in keycaps:
      if key in   NAMED_KEY_ALIASES:
        key_vim	= NAMED_KEY_ALIASES[key]
      else:
        key_vim	= key.upper() if "⇧" in modVar else key
      var      	= preVar + modVar + varLbl + key
      #        	  g        ⇧⎈      🔢      ◀   or a
      val      	= preVal + modVal + valLbl + key_vim  + posVal
      #        	  <        C-       S-      left or A   >
      SEQ[var] 	= [val]
      if lyt_converter.isAlias and\
         len(key_vim) == 1     and\
         not key_vim.isnumeric(): # exclude f1
        key_vim_als	= (lyt_converter.convert(key_vim, lyt.qwerty, lyt.user)).replace('\\','\\\\')
        val_als    	= preVal + modVal + valLbl + key_vim_als  + posVal
        SEQ[var]   	+= [val_als]
        # print(f"{var} {val} {val_als} ({key_vim} {key_vim_als}) ")

# ↓ SEQ dictionary ('quotes' omitted)
# lbl     list of allowed vim values
#   F1	: [<f1>]
# ⇧F1 	: [<S-f1>]
# ⎈F1 	: [<C-f1>]
#⇧⎈F1 	: [<C-S-f1>]
#   1 	: [1]
# 🔢1  	: [<k1>]
#   q 	: [q, й] (with user keymap's aliases)
# ⇧q  	: [Q, Й] (with user keymap's aliases)
#  ⎈a 	: [<C-a>]
# ⇧⎈p 	: [<C-P>]

# Manual bindings
# Keypad
SEQ['🔢/']	= ['<kdivide>']
SEQ['🔢=']	= ['<kenter>']
SEQ['🔢-']	= ['<kminus>']
SEQ['🔢*']	= ['<kmultiply>']
SEQ['🔢.']	= ['<kperiod>']
SEQ['🔢+']	= ['<kplus>']

# Unimpaired
SEQ['⎈['] 	= ['<C-[>']
SEQ['[␠'] 	= ['[<space>']
SEQ['[⇧[']	= ['[{']
SEQ['[⇧9']	= ['[(']
SEQ[']⇧]']	= [']}']
SEQ[']⇧0']	= ['])']
SEQ[']␠'] 	= [']<space>']

# subMode
SEQ['g⇧-'] 	= ['g_']
SEQ['⇧z⇧q']	= ['ZQ']
SEQ['⇧z⇧z']	= ['ZZ']

# other
SEQ['⇧[']	= ['{']
SEQ['⇧]'] = ['}']
SEQ['⇧9']	= ['(']
SEQ['⇧0'] = [')']
SEQ['⇧2'] = ['@']

# g mode
SEQ['g⇧3'] = ['g#']
SEQ['g⇧8'] = ['g*']

# Control chars
TAB      	= ['⭾','↹','<tab>']                 	# TAB
BACKSPACE	= ['␈','⌫','<bs>']                  	# BACKSPACE
HOME     	= ['⇤','⤒','↖','🏠','🏡','⌂','<home>']	# HOME
END      	= ['⇥','⤓','↘','<end>']             	# END
DEL      	= ['␡','⌦','<del>']                 	# DEL
ENTER    	= ['⏎','⌤','↩','<cr>']              	# ENTER
ESC      	= ['⎋','<esc>']                     	# ESC
BACKSLASH	= ['⧵','＼','﹨']                     	# BACKSLASH
SPACE    	= ['␠','␣','<space>']               	# SPACE
INSERT   	= ['⎀','<insert>']                  	# INSERT
LEADER   	= ['Ⓛ','<leader>']                  	# LEADER
for key in BACKSLASH:
  val                   = '<' + NAMED_KEY_ALIASES[key] + '>' # <bslash>
  SEQ[key + key]        = [val + val]
  SEQ[key + key + '⇧a'] = [val + val + 'A']

Z_LEFT = ['z<left>']
G_DOWN = ['g<down>']
G_UP = ['g<up>']
Z_RIGHT = ['z<right>']
CTRL_W_DOWN = ['<C-w><down>']
CTRL_W_RIGHT = ['<C-w><right>']
CTRL_W_LEFT = ['<C-w><left>']
CTRL_W_UP = ['<C-w><up>']

CTRL_ALT_P = ['<C-M-p>']
CTRL_BIG_B = ['<C-B>']
CTRL_BIG_F = ['<C-F>']
CTRL_BIG_P = ['<C-P>']
CTRL_DOT = ['<C-.>']
CTRL_HAT = ['<C-^>']
CTRL_HOME = ['<C-home>']
CTRL_K_CTRL_B = ['<C-k><C-b>']
CTRL_RIGHT_SQUARE_BRACKET = ['<C-]>']
CTRL_R_EQUAL = ['<C-r>=']
CTRL_W_B = ['<C-w>b']
CTRL_W_BACKSPACE = ['<C-w><bs>']
CTRL_W_BAR = ['<C-w><bar>']
CTRL_W_BIG_H = ['<C-w>H']
CTRL_W_BIG_J = ['<C-w>J']
CTRL_W_BIG_K = ['<C-w>K']
CTRL_W_BIG_L = ['<C-w>L']
CTRL_W_BIG_S = ['<C-w>S']
CTRL_W_BIG_W = ['<C-w>W']
CTRL_W_C = ['<C-w>c']
CTRL_W_COLON = ['<C-w>:']
CTRL_W_CTRL_6 = ['<C-w><C-6>']
CTRL_W_CTRL_B = ['<C-w><C-b>']
CTRL_W_CTRL_H = ['<C-w><C-h>']
CTRL_W_CTRL_J = ['<C-w><C-j>']
CTRL_W_CTRL_K = ['<C-w><C-k>']
CTRL_W_CTRL_L = ['<C-w><C-l>']
CTRL_W_CTRL_N = ['<C-w><C-n>']
CTRL_W_CTRL_O = ['<C-w><C-o>']
CTRL_W_CTRL_Q = ['<C-w><C-q>']
CTRL_W_CTRL_RIGHT_SQUARE_BRACKET = ['<C-w><C-]>']
CTRL_W_CTRL_S = ['<C-w><C-s>']
CTRL_W_CTRL_T = ['<C-w><C-t>']
CTRL_W_CTRL_UNDERSCORE = ['<C-w><C-_>']
CTRL_W_CTRL_V = ['<C-w><C-v>']
CTRL_W_CTRL_W = ['<C-w><C-w>']
CTRL_W_CTRL_X = ['<C-w><C-x>']
CTRL_W_EQUAL = ['<C-w>=']
CTRL_W_G = ['<C-w>g']
CTRL_W_GF = ['<C-w>gf']
CTRL_W_GREATER_THAN = ['<C-w>>']
CTRL_W_GT = ['<C-w>gt']
CTRL_W_G_BIG_F = ['<C-w>gF']
CTRL_W_G_BIG_T = ['<C-w>gT']
CTRL_W_H = ['<C-w>h']
CTRL_W_HAT = ['<C-w>^']
CTRL_W_J = ['<C-w>j']
CTRL_W_K = ['<C-w>k']
CTRL_W_L = ['<C-w>l']
CTRL_W_LESS_THAN = ['<C-w><lt>']
CTRL_W_MINUS = ['<C-w>-']
CTRL_W_N = ['<C-w>n']
CTRL_W_O = ['<C-w>o']
CTRL_W_PLUS = ['<C-w>+']
CTRL_W_Q = ['<C-w>q']
CTRL_W_RIGHT_SQUARE_BRACKET = ['<C-w>]']
CTRL_W_S = ['<C-w>s']
CTRL_W_T = ['<C-w>t']
CTRL_W_UNDERSCORE = ['<C-w>_']
CTRL_W_V = ['<C-w>v']
CTRL_W_W = ['<C-w>w']
CTRL_W_X = ['<C-w>x']
CTRL_X_CTRL_L = ['<C-x><C-l>']
CTRL_Y = ['<C-y>']


ALT_N = ['<M-n>']
BAR = ['<bar>']
COMMAND_BIG_B = ['<D-B>']
COMMAND_BIG_F = ['<D-F>']
COMMAND_BIG_P = ['<D-P>']
COMMAND_P = ['<D-p>']
EQUAL_EQUAL = ['==']
GCC = ['gcc']
GQGQ = ['gqgq']
GQQ = ['gqq']
GREATER_THAN = ['>']
GREATER_THAN_GREATER_THAN = ['>>']
GUGU = ['gugu']
GUU = ['guu']
G_BIG_U_BIG_U = ['gUU']
G_BIG_U_G_BIG_U = ['gUgU']
G_COMMA = ['g,']
G_SEMICOLON = ['g;']
G_TILDE = ['g~']
G_TILDE_G_TILDE = ['g~g~']
G_TILDE_TILDE = ['g~~']
LESS_THAN = ['<lt>']
LESS_THAN_LESS_THAN = ['<lt><lt>']
QUOTE_QUOTE = ["''"]
SHIFT_ENTER = ['<S-cr>']
YSS = ['yss']
ZERO = ['0']
ZUG = ['zug']
ZUW = ['zuw']
Z_DOT = ['z.']
Z_ENTER = ['z<cr>']
Z_EQUAL = ['z=']
Z_MINUS = ['z-']
