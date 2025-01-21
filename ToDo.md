# ToDo
  - Add a select-first (select-without-extend) mode (~kak/hx)
# Keymap
  - add a Shifted function instead of Upper to also work with 9→( and [→{
  - change default keymap to ergonomic one (add a config to revert)
# Perf
  - cache hashes of all imported kdl files during the last config load and dump the consolidated cfgU file to disk so that next time all you'd need to do is caclulate hashes of 10 files instead of parsing them as KDL?
  - keymap generator: save source hash on generation to settings and on upgrade check if default keymap's hash changed, and if so, prompt the user and run generator again
# Plugins
  - check easymotion vs ST's acejump
# UI
  - add all commands to the command panel to have fuzzy search? (also has keybinds) or too much noise?
    - maybe add a config flag that would indicate which keybinding should be added?
# Misc
  - g0 g$ g^ motion commands not implemented for wrapped lines https://github.com/NeoVintageous/NeoVintageous/issues/757
  - inoremap not working https://github.com/NeoVintageous/NeoVintageous/issues/837
  - mark neovint as incompatible plugin in my fork
# BLOCKED by Sublime
  - keybinds: fix multilingual: single-key rebinds are still keycap based, so remapping ⇧4 from qwerty to russian means losing ; since that's what's mapped there, need to exclude this remap from user config or wait until ST implements proper physical key mapping https://github.com/sublimehq/sublime_text/issues/5976
  - F1 add my keybinds as HTML phantom/toolip? Or "menus" for mini-modes after a delay without action has passed
    - Sublime's minihtml isn't powerful enough to display KLE html, maybe a simple table?

# ?
  - simplify config keymap and have S-a everywhere instead of A to be consistent with S-f1
    - but need to retain the old A and <M-A> notation since user configs use it, so not worth it
  - add to space mode all various comment types 1,2,3,4,5
  - simpler layer-based keybinding format for simple keybinds that can be represented with a single symbol defined elsewhere?
  ```kdl
  layer_name blank=("non-whitespace space")"⠀" \
   §	1	2	  3	4	 5	6	7	  8	  9	 0	-	 "="	←=label
   ⎋	‽	⠀	  №	¤	 ⠀	‸	‽	  ⁂	  ⠀	 ⁀	⹀	 ⠀  	←=nomod
   ⠀	⠀	⠀	  ☰	𝌆	 ⠀	⎀	⠀	  ⠀	   	  	⸗	 ⠀  	←=⇧
   ˋ 🔅 🔆 🎛 ▦ 💡 ⇞ ◀◀  ▶⏸ ▶▶ 🔇 🔉 🔊 ⌦ ←=⌥
  ```
# Bugs
  - add delete// etc commands that I've remapped if can't make seletion-hx-like work
  - Surround does not handle alternate input methods https://github.com/NeoVintageous/NeoVintageous/issues/842
  - noremap ⭾ key fails, replace ⭾ with ␠
  - count doesn't persist through remaps
  `noremap t r` then `6 t` fails with carrying over 6 while `6 r` works in the original
  - ? remapped  d working incorrectly https://github.com/NeoVintageous/NeoVintageous/issues/820
‹.m› а	 e
‹.m› в	 b

+ resolved
  - (yes, without this mappings to й would not be recognized) is `SEQ['q'] += ['й']` really needed? seems to work without it, but how?
  - (no?) is there a way to allow direct remapping of й in neovintageous map without having to add sublime keymap?
  - convert all bindings to dictonaries of lists (partially done)
