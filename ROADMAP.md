## Legend

:heavy_check_mark: - done

:white_check_mark: - partially done

:rocket: - Sublime Text specific; Non-Vim

:sparkles: - additional sublime text functionality

:bug: - Buggy

:x: - Can't be implemented due to platform limitations

`[count]` - An optional number that may precede the command to multiply or iterate the command.

<details>
 <summary><strong>Table of Contents</strong> (click to expand)</summary>

- [Modes](#modes-vim-modes)
- [Editing and writing files](#editing-and-writing-files-editingtxt)
- [Commands for moving around](#commands-for-moving-around-motion-txt)
  - [Motions and operators](#motions-and-operators-operator)
  - [Left-right motions](#left-right-motions-left-right-motions)
  - [Text object selection](#text-object-selection-text-objects)
  - [Marks](#marks-mark-motions)
  - [Jumps](#jumps-jump-motions)
- [Scrolling the text in the window](#scrolling-the-text-in-the-window-scrolltxt)
- [Insert and Replace mode](#insert-and-replace-mode-inserttxt)
- [Deleting and replacing text](#deleting-and-replacing-text-changetxt)
- [Undo and Redo](#undo-and-redo-undotxt)
- [Repeating commands](#repeating-commands-repeattxt)
- [Using the Visual mode (selecting a text area)](#using-the-visual-mode-selecting-a-text-area-visualtxt)
- [Various remaining commands](#various-remaining-commands-varioustxt)
- [Command-line editing](#command-line-editing-cmdlinetxt)
- [Description of all options](#description-of-all-options-optionstxt)
- [Regexp patterns and search commands](#regexp-patterns-and-search-commands-patterntxt)
- [Key mapping and abbreviations](#key-mapping-and-abbreviations-maptxt)
- [Tags and special searches](#tags-and-special-searches-tagsrchtxt)
- [Commands for using multiple windows and buffers](#commands-for-using-multiple-windows-and-buffers-windowstxt)
- [Commands for using multiple tab pages](#commands-for-using-multiple-tab-pages-tabpagetxt)
- [Spell checking](#spell-checking-spelltxt)
- [Hide (fold) ranges of lines](#hide-fold-ranges-of-lines-fondtxt)
- [Plugins](#plugins)
  - [Abolish](#abolish-abolishtxt)
  - [Commentary](#commentary-commentarytxt)
  - [Highlighted Yank](#highlighted-yank-highlightedyank)
  - [Indent Object](#indent-object-indent-objecttxt)
  - [Multiple Cursors](#multiple-cursors-multiple-cursors)
  - [Sneak](#sneak-sneaktxt)
  - [Surround](#surround-surroundtxt)
  - [Targets](#targets)
  - [Unimpaired](#unimpaired-unimpairedtxt)
- [Completeness](#completeness)
- [Work in Progress](#work-in-progress)
- [F.A.Q.](#faq)
- [Known issues](#known-issues)

</details>

## Modes `|vim-modes|`

| Status             | Mode                  | Description
| :----------------- | :-------------------- | :----------
| :heavy_check_mark: | Insert mode           | `[count]i`
| :heavy_check_mark: | Normal mode           | `<Esc>`
| :heavy_check_mark: | Visual mode           | `v`
| :heavy_check_mark: | Visual line mode      | `[count]V`
| :heavy_check_mark: | Visual block mode     | `CTRL-V`
| :heavy_check_mark: | Replace mode          | `R`
| :heavy_check_mark: | Operator-pending mode | Like Normal mode, but after an operator command has start, and Vim is waiting for a `{motion}` to specify the text that the operator will work on.
| :heavy_check_mark: | Command-line mode     | `:`, `/`, `?`, `!`
| :rocket:           | Multiple-cursor mode  | `CTRL-N`, `gh`

## Editing and writing files `|editing.txt|`

| Status             | Command                          | Description
| :----------------- | :------------------------------- | :----------
| :heavy_check_mark: |`CTRL-G`, `:f[ile]`               | Prints the current file name
| :heavy_check_mark: |`:buffers`, `:files`, `:ls`       | List all the currently known file names
| :bug:              |`:e[dit]`                         | Edit the current file. This is useful to re-edit the current file, when it has been changed outside of Sublime.
| :heavy_check_mark: |`:e[dit]!`                        | Edit the current file always.  Discard any changes to the current buffer.
| :heavy_check_mark: |`:e[dit] {file}`                  | Edit `{file}`
| :heavy_check_mark: | `:ene[w]`                        | Edit a new, unnamed buffer
| :heavy_check_mark: | `CTRL-^`                         | Edit the alternate file
| :heavy_check_mark: | `gf`                             | Edit the file whose name is under or after the cursor
| :heavy_check_mark: | `{Visual}gf`                     | Same as "gf", but the highlighted text is used as the name of the file to edit
| :heavy_check_mark: | `gF`                             | Same as "gf", except if a number follows the file name, then the cursor is positioned on that line in the file
| :heavy_check_mark: | `{Visual}gF`                     | Same as "v_gf".

## Commands for moving around `|motion.txt|`

### Motions and operators `|operator|`

| Status             | Command   | Description
| :----------------- | :-------- | :----------
| :heavy_check_mark: | `c`       | change
| :heavy_check_mark: | `d`       | delete
| :heavy_check_mark: | `y`       | yank into register (does not change the text)
|                    | `~`       | swap case (only if 'tildeop' is set)
| :heavy_check_mark: | `g~`      | g~  swap case
| :heavy_check_mark: | `gu`      | gu  make lowercase
| :heavy_check_mark: | `gU`      | gU  make uppercase
| :heavy_check_mark: | `!`       | filter through an external program
|                    | `=`       | filter through 'equalprg' or C-indenting if empty
| :heavy_check_mark: | `gq`      | gq  text formatting
|                    | `gw`      | gw  text formatting with no cursor movement
|                    | `g?`      | g?  ROT13 encoding
| :heavy_check_mark: | `>`       | shift right
| :heavy_check_mark: | `<`       | shift left
| :x:                | `zf`      | zf  define a fold
|                    | `g@`      | g@  call function set with the 'operatorfunc' option

### Left-right motions `|left-right-motions|`

| Status             | Command                              | Description
| :----------------- | :----------------------------------- | -----------
| :heavy_check_mark: | `h`, `<Left>`, `CTRL-H`, `<BS>`      | `[count]` characters to the left. `|exclusive|` motion.

### Text object selection `|text-objects|`

| Status             | Command                       | Description
| :----------------- | :---------------------------- | -----------
| :heavy_check_mark: | `aw`                          | "a word", select `[count]` words
| :heavy_check_mark: | `iw`                          | "inner word", select `[count]` words
| :heavy_check_mark: | `aW`                          | "a WORD", select `[count]` WORDs
| :heavy_check_mark: | `iW`                          | "inner WORD", select `[count]` WORDs
| :heavy_check_mark: | `as`                          | "a sentence"
| :heavy_check_mark: | `is`                          | "inner sentence"
| :heavy_check_mark: | `ap`                          | "a paragraph", select `[count]` paragraphs
| :heavy_check_mark: | `ip`                          | "inner paragraph", select `[count]` paragraphs
| :heavy_check_mark: | `a]`, `a[`                    | "a `[]` block"
| :heavy_check_mark: | `i]`, `i[`                    | "inner `[]` block"
| :heavy_check_mark: | `a)`, `a(`, `ab`              | "a block", select blocks, from "[(" to the matching ')', including the '(' and ')'
| :heavy_check_mark: | `i)`, `i(`, `ib`              | "inner block", select blocks, from "[(" to the matching ')', excluding the '(' and ')'
| :heavy_check_mark: | `a>`, `a<`                    | "a <> block"
| :heavy_check_mark: | `i>`, `i<`                    | "inner <> block"
| :heavy_check_mark: | `at`                          | "a tag block"
| :heavy_check_mark: | `it`                          | "inner tag block"
| :heavy_check_mark: | `a}`, `a{`, `aB`              | "a Block", select blocks, from "[{" to the matching '}', including the '{' and '}'
| :heavy_check_mark: | `i}`, `i{`, `iB`              | "inner block", select blocks, from "[{" to the matching '}', excluding the '{' and '}'
| :heavy_check_mark: | `a"`, `a'`, `a{backtick}`     | Selects the text from the previous quote until the next quote
| :heavy_check_mark: | `i"`, `i'`, `i{backtick}`     | Like `a"`, `a'` and `a{backtick}`, but exclude the quotes

### Marks `|mark-motions|`

| Status             | Command                       | Description
| :----------------- | :---------------------------- | -----------
| :heavy_check_mark: | `m{a-zA-Z}`                   | Set mark `{a-zA-Z}` at cursor position.
| :heavy_check_mark: | `'{a-z}`  `{backtick}{a-z}`   | Jump to the mark `{a-z}` in the current buffer.
| :heavy_check_mark: | `'{A-Z}`  `{backtick}{A-Z}`   | To the mark `{A-Z}` in the file where it was set (not a motion command when in another file).
| :heavy_check_mark: | `:marks`                      | List all the current marks (not a motion command).

### Jumps `|jump-motions|`

| Status             | Command                       | Description
| :----------------- | :---------------------------- | -----------
| :heavy_check_mark: | `<Tab>`, `CTRL-I`             | Go to newer cursor position in jump list (not a motion command)
| :heavy_check_mark: | `CTRL-O`                      | Go to older cursor position in jump list (not a motion command)

## Scrolling the text in the window `|scroll.txt|`

| Status             | Command                          | Description
| :----------------- | :------------------------------- | :----------

## Insert and Replace mode `|insert.txt|`

| Status             | Command                          | Description
| :----------------- | :------------------------------- | :----------

## Deleting and replacing text `|change.txt|`

| Status             | Command                          | Description
| :----------------- | :------------------------------- | :----------
| :heavy_check_mark: | `~`                              | swap case

## Undo and Redo `|undo.txt|`

| Status             | Command                      | Description
| :------------------| :--------------------------- | -----------
| :heavy_check_mark: | `u`                          | Undo `[count]` changes
| :heavy_check_mark: | `CTRL-R`                     | Redo `[count]` changes which were undone
|                    | `U`                          | Undo all latest changes on one line, the line where the latest change was made

## Repeating commands `|repeat.txt|`

| Status             | Command                      | Description
| :------------------| :--------------------------- | -----------
| :heavy_check_mark: | `[count].`                   | Repeat last change, with count replaced with `[count]`
|                    | `@:`                         | Repeat last command-line `[count]` times
| :heavy_check_mark: | `q{0-9a-zA-Z"}`              | Record typed characters into register `{0-9a-zA-Z"}` (uppercase to append)
| :heavy_check_mark: | `q`                          | Stops recording
| :heavy_check_mark: | `@{0-9a-z"}`                 | Execute the contents of register `{0-9a-z"}` `[count]` times
|                    | `@{=*+}`                     | Execute the contents of register `{=*+}` `[count]` times
| :heavy_check_mark: | `@@`                         | Repeat the previous `@{0-9a-z":*}` `[count]` times

## Using the Visual mode (selecting a text area) `|visual.txt|`

| Status             | Command                       | Description
| :----------------- | :---------------------------- | -----------
| :heavy_check_mark: | `v`                           | Start Visual mode per character
| :heavy_check_mark: | `[count]V`                    | Start Visual mode linewise
| :heavy_check_mark: | `CTRL-V`                      | Start Visual mode blockwise
| :heavy_check_mark: | `gv`                          | Start visual mode with the same area as the previous area and the same mode
| :heavy_check_mark: | `gn`                          | Search forward for the last used search pattern, like with `n`, and start Visual mode to select the match.
| :heavy_check_mark: | `gN`                          | Like `gn` but searches backward, like with `N`
| :heavy_check_mark: | `o`                           | Go to other end of highlighted text
|                    | `O`                           | Like "o", but in Visual block mode the cursor moves to the other corner in the same line
| :heavy_check_mark: | `<Esc>`, `CTRL-C`             | Stop Visual mode

## Various remaining commands `|various.txt|`

| Status             | Command                      | Description
| :----------------- | :--------------------------- | -----------
| :heavy_check_mark: | `ga`                         | Print the ascii value of the character under the cursor in dec, hex and oct.
|                    | `:as[cii]`                   | Same as `ga`
| :heavy_check_mark: | `:sh[ell]`                   | This command starts a shell
| :heavy_check_mark: | `:!{cmd}`                    | Execute `{cmd}` with the shell
| :heavy_check_mark: | `:!!`                        | Repeat last `":!{cmd}"`
| :heavy_check_mark: | `:sil[ent] {command}`        | Execute `{command}` silently

## Command-line editing `|cmdline.txt|`

| Status             | Command                          | Description
| :----------------- | :------------------------------- | -----------
| :heavy_check_mark: | `<Left>`                         | cursor left
| :heavy_check_mark: | `<Right>`                        | cursor right
| :heavy_check_mark: | `<S-Left>`, `<C-Left>`           | cursor one WORD left
| :heavy_check_mark: | `<S-Right>`, `<C-Right>`         | cursor one WORD right
| :heavy_check_mark: | `CTRL-B`, `<Home>`               | cursor to beginning of command-line
| :heavy_check_mark: | `CTRL-E`, `<End>`                | cursor to end of command-line
| :heavy_check_mark: | `CTRL-H`, `<BS>`                 |
| :heavy_check_mark: | `<Del>`                          |
| :heavy_check_mark: | `CTRL-W`                         |
| :heavy_check_mark: | `CTRL-U`                         |
| :heavy_check_mark: | `CTRL-P`, `<up>`                 |
| :heavy_check_mark: | `CTRL-N`,, `<down>`              |
| :heavy_check_mark: | `CTRL-C`, `CTRL-[`, `<Esc>`      |
| :heavy_check_mark: | `<Tab>`                          |
| :heavy_check_mark: | `<S-Tab>`                        |

## Description of all options `|options.txt|`

| Status             | Command                                      | Description
| :------------------| :------------------------------------------- | -----------
|                    | `:se[t][!]`                                  | Show all options that differ from their default value
|                    | `:se[t][!] all`                              | Show all but terminal options
|                    | `:se[t] termcap`                             | Show all terminal options
|                    | `:se[t]! termcap`                            | Idem, but don't use multiple columns
| :heavy_check_mark: | `:se[t] {option}?`                           | Show value of `{option}`
| :heavy_check_mark: | `:se[t] {option}`                            | Toggle option: set, switch it on. Number or String option: show value.
| :heavy_check_mark: | `:se[t] no{option}`                          | Toggle option: Reset, switch it off
| :heavy_check_mark: | `:se[t] {option}!`, `:se[t] inv{option}`     | Toggle option: Invert value
|                    | `:se[t] {option}&`                           | Reset option to its default value
|                    | `:se[t] {option}&vi`                         | Reset option to its Vi default value
|                    | `:se[t] {option}&vim`                        | Reset option to its Vim default value
|                    | `:se[t] all&`                                | Set all options to their default value
| :heavy_check_mark: | `:se[t] {option}={value}`                    | Set string or number option to `{value}`
|                    | `:se[t] {option}:{value}`                    | Same as `:se[t] {option}={value}`
|                    | `:se[t] {option}+={value}`                   | Add the `{value}` to a number option, or append the `{value}` to a string option.
|                    | `:se[t] {option}^={value}`                   | Multiply the `{value}` to a number option, or prepend the `{value}` to a string option.
|                    | `:se[t] {option}-={value}`                   | Subtract the `{value}` from a number option, or remove the `{value}` from a string option, if it is there.

Some options "proxy" to Sublime Text settings. This means that the option uses the underlying Sublime Text setting . Changing the option, changes the underlying Sublime Text setting. See blog post on [NeoVintageous Options](https://blog.gerardroche.com/2023/06/05/neovintageous-options/).

| Status             | Option                       | Type      | Default
| :------------------| :--------------------------- | :-------- | :------
| :heavy_check_mark: | `'autoindent'` `'ai'`        | `string`  | `auto_indent` st setting
| :white_check_mark: | `'belloff'` `'bo'`           | `string` | `''`; accepts 'all'
| :heavy_check_mark: | `'equalalways'`              | `boolean` | On
| :heavy_check_mark: | `'expandtab'` `'et'`         | `boolean` | `translate_tabs_to_spaces` st setting
| :heavy_check_mark: | `'hlsearch'` `'hls'`         | `boolean` | On
| :heavy_check_mark: | `'ignorecase'` `'ic'`        | `boolean` | Off
| :heavy_check_mark: | `'incsearch'` `'is'`         | `boolean` | On
| :heavy_check_mark: | `'list'`                     | `boolean` | `draw_white_space` st setting
| :heavy_check_mark: | `'magic'`                    | `boolean` | On
| :heavy_check_mark: | `'menu'`                     | `boolean` | On
| :heavy_check_mark: | `'minimap'`                  | `boolean` | On
| :heavy_check_mark: | `'modeline'` `'ml'`          | `boolean` | On
| :heavy_check_mark: | `'modelines'` `'mls'`        | `number`  | 5
| :heavy_check_mark: | `'number'` `'nu'`            | `boolean` | `line_numbers` st setting
| :heavy_check_mark: | `'relativenumber'` `'rnu'`   | `boolean` | `relative_line_numbers` st setting
| :heavy_check_mark: | `'scrolloff'` `'so'`         | `number`  | `scroll_context_lines` st setting
| :white_check_mark: | `'shell'`                    | `string`  | `$SHELL` or `"sh"`, Win32: `"cmd.exe"`
| :heavy_check_mark: | `'sidebar'`                  | `boolean` | On
|                    | `'sidescrolloff'` `'siso'`   | `number`  | 5
| :heavy_check_mark: | `'smartcase'` `'scs'`        | `boolean` | Off
| :heavy_check_mark: | `'spell'`                    | `boolean` | `spell_check` st setting
| :heavy_check_mark: | `'statusbar'`                | `boolean` | On
| :heavy_check_mark: | `'tabstop'` `'ts'`           | `number`  | `tab_size` st setting
| :heavy_check_mark: | `'textwidth'` `'tw'`         | `number` | `wrap_width` st setting
| :heavy_check_mark: | `'winaltkeys'` `'wak'`       | `string` | `menu`
| :heavy_check_mark: | `'wrap'`                     | `boolean` | `word_wrap` st setting
| :heavy_check_mark: | `'wrapscan'` `'ws'`          | `boolean` | On

## Regexp patterns and search commands `|pattern.txt|`

| Status             | Command                          | Description
| :----------------- | :------------------------------- | :----------

## Key mapping and abbreviations `|map.txt|`

| Status             | Command                          | Description
| :----------------- | :------------------------------- | :----------

## Tags and special searches `|tagsrch.txt|`

| Status             | Command                          | Description
| :----------------- | :------------------------------- | :----------

## Commands for using multiple windows and buffers `|windows.txt|`

### 3. Opening and closing a window

| Status             | Command                                                      | Description
| :----------------- | :----------------------------------------------------------- | :----------
| :heavy_check_mark: | `CTRL-W s`, `CTRL-W S`, `CTRL-W CTRL-S`, `:sp[lit] [file]`   | Split current window in two
| :heavy_check_mark: | `CTRL-W CTRL-V`, `CTRL-W v`, `:vs[plit] [file]`              | Like `|:split|`, but split vertically
| :heavy_check_mark: | `CTRL-W n`, `CTRL-W CTRL-N`, `:new`                          | Create a new window and start editing an empty file in it
| :heavy_check_mark: | `:new {file}`, `:sp[lit] {file}`                             | Create a new window and start editing file `{file}` in it
| :heavy_check_mark: | `:vne[w] [file]`                                             | Like `|:new|`, but split vertically
|                    | `:sv[iew] [file]`                                            | Same as `":split"`, but set 'readonly' option for this buffer
|                    | `:sf[ind] {file}`                                            | Same as `":split"`, but search for `{file}` in 'path' like in `|:find|`
| :heavy_check_mark: | `CTRL-W CTRL-^`, `CTRL-W ^`                                  | Split the current window in two and edit the alternate file
| :heavy_check_mark: | `CTRL-W :`                                                   | Does the same as typing `|:|` - enter a command line
| :heavy_check_mark: | `:q[uit]`, `:q[uit]`, `CTRL-W q`, `CTRL-W CTRL-Q`            | Quit the current window
| :heavy_check_mark: | `:q[uit]!`, `:q[uit]!`                                       | Quit the current window
| :heavy_check_mark: | `:clo[se][!]`, `:clo[se][!]`, `CTRL-W c`                     | Close the current window
| :heavy_check_mark: | `CTRL-W CTRL-C`                                              | You might have expected that CTRL-W CTRL-C closes the current window, but that does not work, because the CTRL-C cancels the command
|                    | `:hid[e]`, `:hid[e]`                                         | Quit the current window, unless it is the last window on the screen
|                    | `:hid[e] {cmd}`                                              | Execute `{cmd}` with 'hidden' is set
| :heavy_check_mark: | `:on[ly][!]`, `:on[ly][!]`, `CTRL-W o`, `CTRL-W CTRL-O`      | Make the current window the only one on the screen

### 4. Moving cursor to other windows

| Status             | Command                                                      | Description
| :----------------- | :----------------------------------------------------------- | :----------
| :heavy_check_mark: | `CTRL-W <Down>`, `CTRL-W CTRL-J`, `CTRL-W j`                 | Move cursor to Nth window below current one
| :heavy_check_mark: | `CTRL-W <Up>`, `CTRL-W CTRL-K`, `CTRL-W k`                   | Move cursor to Nth window above current one
| :heavy_check_mark: | `CTRL-W <Left>`, `CTRL-W CTRL-H`, `CTRL-W <BS>`, `CTRL-W h`  | Move cursor to Nth window left of current one
| :heavy_check_mark: | `CTRL-W <Right>`, `CTRL-W CTRL-L`, `CTRL-W l`                | Move cursor to Nth window right of current one
| :heavy_check_mark: | `CTRL-W w`, `CTRL-W CTRL-W`                                  | Move cursor to window below/right of the current one
| :heavy_check_mark: | `CTRL-W W`                                                   | Move cursor to window above/left of current one
| :heavy_check_mark: | `CTRL-W t`, `CTRL-W CTRL-T`                                  | Move cursor to top-left window
| :heavy_check_mark: | `CTRL-W b`, `CTRL-W CTRL-B`                                  | Move cursor to bottom-right window
| :heavy_check_mark: | `CTRL-W p`, `CTRL-W CTRL-P`                                  | Go to previous (last accessed) window
| :heavy_check_mark: | `CTRL-W P`                                                   | Go to preview window

## Commands for using multiple tab pages `|tabpage.txt|`

| Status             | Command                          | Description
| :----------------- | :------------------------------- | :----------

## Spell checking `|spell.txt|`

| Status             | Command                          | Description
| :----------------- | :------------------------------- | :----------

## Hide (fold) ranges of lines `|fond.txt|`

| Status             | Command                          | Description
| :----------------- | :------------------------------- | :----------

## Plugins

| Plugin              | Status             | Original Vim Plugin | Notes
| :------------------ | :----------------- | :------------------ | :----
| Abolish             | :white_check_mark: | [vim-abolish](https://github.com/tpope/vim-abolish) |
| Commentary          | :white_check_mark: | [vim-commentary](https://github.com/tpope/vim-commentary) |
| Highlighted Yank    | :heavy_check_mark: | [vim-highlightedyank](https://github.com/machakann/vim-highlightedyank) |
| Indent Object       | :white_check_mark: | [vim-indent-object](https://github.com/michaeljsmith/vim-indent-object) |
| Multiple Cursors    | :heavy_check_mark: | [vim-multiple-cursors](https://github.com/terryma/vim-multiple-cursors) |
| Sneak               | :white_check_mark: | [vim-sneak](https://github.com/justinmk/vim-sneak) | [Disabled by default](https://github.com/NeoVintageous/NeoVintageous/issues/731)
| Surround            | :white_check_mark: | [vim-surround](https://github.com/tpope/vim-surround) |
| Targets             | :white_check_mark: | [vim-targets](https://github.com/wellle/targets.vim) |
| Unimpaired          | :white_check_mark: | [vim-unimpaired](https://github.com/tpope/vim-unimpaired) |

Suggestions for future implementation.

| Plugin | Original Vim Plugin | Notes
| ------ | ------------------- | -----
| Hop | [hop.nvim](https://github.com/phaazon/hop.nvim) | Re https://github.com/NeoVintageous/NeoVintageous/issues/808
| WhichKey | [vim-which-key](https://github.com/liuchengxu/vim-which-key) | Re https://github.com/NeoVintageous/NeoVintageous/issues/758
| SurroundAny | | Re https://github.com/NeoVintageous/NeoVintageous/issues/743
| YankStackAndRing | | Re https://github.com/NeoVintageous/NeoVintageous/issues/337
| XkbSwitch | [vim-xkbswitch](https://github.com/lyokha/vim-xkbswitch) | Re https://github.com/NeoVintageous/NeoVintageous/issues/276
| EasyMotion | [vim-easymotion](https://github.com/easymotion/vim-easymotion) | Re https://github.com/NeoVintageous/NeoVintageous/issues/276

### Abolish `|abolish.txt|`

A port of [vim-abolish](https://github.com/tpope/vim-abolish).

| Status             | Command           | Description
| :------------------| :---------------- | :----------
| :heavy_check_mark: | `cr{algorithm}`   | Case mutating algorithms
|                    | `:Abolish`        | Search and substitute
|                    | `:Subvert`        | More concise syntax for search and substitute

### Commentary `|commentary.txt|`

A port of [vim-commentary](https://github.com/tpope/vim-commentary).

| Status             | Command           | Description
| :------------------| :---------------- | :----------
| :heavy_check_mark: | `gc{motion}` | Comment or uncomment lines that `{motion}` moves over
| :heavy_check_mark: | `gc` | Comment or uncomment `[count]` lines
| :heavy_check_mark: | `{Visual}gc` | Comment or uncomment the highlighted lines
| :heavy_check_mark: | `gc` | Text object for a comment (operator pending mode only)
|                    | `gcgc` or `gcu` | Uncomment the current and adjacent commented lines.

### Highlighted Yank `|highlightedyank|`

Inspired by [vim-highlightedyank](https://github.com/machakann/vim-highlightedyank).

### Indent Object `|indent-object.txt|`

A port of [vim-indent-object](https://github.com/michaeljsmith/vim-indent-object).

| Status             | Command           | Description
| :----------------- | :---------------- | :----------
| :heavy_check_mark: | `<count>ai` | (A)n (I)ndentation level and line above.
| :heavy_check_mark: | `<count>ii` | (I)nner (I)ndentation level (no line above).
| :heavy_check_mark: | `<count>aI` | (A)n (I)ndentation level and lines above/below.
| :heavy_check_mark: | `<count>iI` | (I)nner (I)ndentation level (no lines above/below).

### Multiple Cursors `|multiple-cursors|`

Inspired by [vim-multiple-cursors](https://github.com/terryma/vim-multiple-cursors).

### Sneak `|sneak.txt|`

A port of [vim-sneak](https://github.com/justinmk/vim-sneak).

NORMAL-MODE

| Status             | Command           | Description
| :----------------- | :---------------- | :----------
| :heavy_check_mark: | `s{char}{char}` | Go to the next occurrence of `{char}{char}`
| :heavy_check_mark: | `S{char}{char}` | Go to the previous occurrence of `{char}{char}`
| :heavy_check_mark: | `s{char}<Enter>` | Go to the next occurrence of `{char}`
| :heavy_check_mark: | `S{char}<Enter>` | Go to the previous occurrence of `{char}`
| :heavy_check_mark: | `s<Enter>` | Repeat the last Sneak.
| :heavy_check_mark: | `S<Enter>` | Repeat the last Sneak, in reverse direction.
| :heavy_check_mark: | `;` | Go to the `[count]`th next match
| :heavy_check_mark: | `,` or `\` | Go to the `[count]`th previous match
|                    | `s` | Go to the `[count]`th next match
|                    | `S` | Go to the `[count]`th previous match
|                    | `[count]s{char}{char}` | Invoke sneak-vertical-scope
|                    | `[count]S{char}{char}` | Invoke backwards sneak-vertical-scope
| :heavy_check_mark: | `{operator}z{char}{char}` | Perform `{operator}` from the cursor to the next occurrence of `{char}{char}`
| :heavy_check_mark: | `{operator}Z{char}{char}` | Perform `{operator}` from the cursor to the previous occurrence of `{char}{char}`

VISUAL-MODE

| Status             | Command           | Description
| :----------------- | :---------------- | :----------
| :heavy_check_mark: | `s{char}{char}` | Go to the next occurrence of `{char}{char}`
| :heavy_check_mark: | `Z{char}{char}` | Go to the previous occurrence of `{char}{char}`
| :heavy_check_mark: | `s{char}<Enter>` | Go to the next occurrence of `{char}`
| :heavy_check_mark: | `Z{char}<Enter>` | Go to the previous occurrence of `{char}`
| :heavy_check_mark: | `s<Enter>` | Repeat the last Sneak.
| :heavy_check_mark: | `Z<Enter>` | Repeat the last Sneak, in reverse direction.
| :heavy_check_mark: | `;` | Go to the `[count]`th next match
| :heavy_check_mark: | `,` or `\` | Go to the `[count]`th previous match
|                    | `s` | Go to the `[count]`th next match
|                    | `S` | Go to the `[count]`th previous match

LABEL-MODE

| Status              | Command               | Description
| :------------------ | :-------------------- | :----------
|                     | `<Space>` or `<Esc>`  | Exit `|sneak-label-mode|` where the cursor is.
|                     | `<Tab>`               | Label the next set of matches.
|                     | `<BS>` or `<S-Tab>`   | Label the previous set of matches.

### Surround `|surround.txt|`

A port of [vim-surround](https://github.com/tpope/vim-surround).

| Status              | Command           | Description
| :------------------ | :---------------- | :----------
| :heavy_check_mark:  | `cs` | Change surroundings.
| :heavy_check_mark:  | `ds` | Delete surroundings.
| :heavy_check_mark:  | `ys` | Yank and change surroundings.
| :heavy_check_mark:  | `yss` | Operates on current line, ignoring whitespace.
| :heavy_check_mark:  | `{Visual}S` | With an argument wraps the selection.
|                     | `cS` - Change surroundings and put on own line.
|                     | `yS` - Yank and change surroundings and put on own line.

### Targets

Inspired by [targets.vim](https://github.com/wellle/targets.vim).

### Unimpaired `|unimpaired.txt|`

A port of [vim-unimpaired](https://github.com/tpope/vim-unimpaired).

| Status              | Command           | Description
| :------------------ | :---------------- | :----------
|                     | `[a` | `:previous`
|                     | `]a` | `:next`
|                     | `[A` | `:first`
|                     | `]A` | `:last`
| :heavy_check_mark:  | `[b` | `:bprevious`
| :heavy_check_mark:  | `]b` | `:bnext`
| :heavy_check_mark:  | `[B` | `:bfirst`
| :heavy_check_mark:  | `]B` | `:blast`
| :heavy_check_mark:  | `[l` | `:lprevious`
| :heavy_check_mark:  | `]l` | `:lnext`
|                     | `[L` | `:lfirst`
|                     | `]L` | `:llast`
|                     | `[<C-L>` | `:lpfile`
|                     | `]<C-L>` | `:lnfile`
|                     | `[q` | `:cprevious`
|                     | `]q` | `:cnext`
|                     | `[Q` | `:cfirst`
|                     | `]Q` | `:clast`
|                     | `[<C-Q>` | `:cpfile` (Note that `<C-Q>` only works in a terminal if you disable
|                     | `]<C-Q>` | `:cnfile` flow control: stty -ixon)
| :heavy_check_mark:  | `[t` | `:tprevious`
| :heavy_check_mark:  | `]t` | `:tnext`
| :heavy_check_mark:  | `[T` | `:tfirst`
| :heavy_check_mark:  | `]T` | `:tlast`
|                     | `[<C-T>` | `:ptprevious`
|                     | `]<C-T>` | `:ptnext`
|                     | `[f` | Go to the file preceding the current one alphabetically in the current file's directory.  In the quickfix window, equivalent to `:colder`.
|                     | `]f` | Go to the file succeeding the current one alphabetically in the current file's directory.  In the quickfix window, equivalent to `:cnewer`.
| :heavy_check_mark:  | `[n` | Go to the previous SCM conflict marker or diff/patch hunk.  Try `d[n` inside a conflict.
| :heavy_check_mark:  | `]n` | Go to the next SCM conflict marker or diff/patch hunk.
| :heavy_check_mark:  | `[<Space>` | Add `[count]` blank lines above the cursor.
| :heavy_check_mark:  | `]<Space>` | Add `[count]` blank lines below the cursor.
| :heavy_check_mark:  | `[e` | Exchange the current line with `[count]` lines above it.
| :heavy_check_mark:  | `]e` | Exchange the current line with `[count]` lines below it.
|                     | `>p` | Paste after linewise, increasing indent.
|                     | `>P` | Paste before linewise, increasing indent.
|                     | `<p` | Paste after linewise, decreasing indent.
|                     | `<P` | Paste before linewise, decreasing indent.
|                     | `=p` | Paste after linewise, reindenting.
|                     | `=P` | Paste before linewise, reindenting.

Option Toggling

| Status              | On    | Off   | Toggle | Option
| :------------------ | :---- | :---- | :----- | :-----
|                     | `[ob` | `]ob` | `yob`  | `'background'` (dark is off, light is on)
| :heavy_check_mark:  | `[oc` | `]oc` | `yoc`  | `'cursorline'`
| :x:                 | `[od` | `]od` | `yod`  | `'diff'` (actually `:diffthis` / `:diffoff`)
| :heavy_check_mark:  | `[oh` | `]oh` | `yoh`  | `'hlsearch'`
| :heavy_check_mark:  | `[oi` | `]oi` | `yoi`  | `'ignorecase'`
| :heavy_check_mark:  | `[ol` | `]ol` | `yol`  | `'list'`
| :heavy_check_mark:  | `[on` | `]on` | `yon`  | `'number'`
| :heavy_check_mark:  | `[or` | `]or` | `yor`  | `'relativenumber'`
| :heavy_check_mark:  | `[os` | `]os` | `yos`  | `'spell'`
| :x:                 | `[ot` | `]ot` | `yot`  | `'colorcolumn'` ("+1" or last used value)
| :x:                 | `[ou` | `]ou` | `you`  | `'cursorcolumn'`
| :x:                 | `[ov` | `]ov` | `yov`  | `'virtualedit'`
| :heavy_check_mark:  | `[ow` | `]ow` | `yow`  | `'wrap'`
| :x:                 | `[ox` | `]ox` | `yox`  | `'cursorline'` `'cursorcolumn'` (x as in crosshairs)

## Completeness

This is list of mainly small edge cases or low priority enhancements. They are listed here instead of having dedicated opened issues.

* [ ] Allow `<` and literal space " " in mappings
* [ ] Implement `[(` go to `[count]` previous unmatched '('. |exclusive| motion.
* [x] #860 (**Implemented in 1.29.0**)
* [x] #861 (**Implemented in 1.29.0**)
* [x] #858 (**Implemented in 1.29.0**)
* [x] Implement `[count]` for `N` after `#` (**Implemented in 1.27.0**)
* [x] Implement `[count]` for `N` after `*` (**Implemented in 1.27.0**)
* [x] #904  (**Implemented in 1.31.0**)
* [ ] Implement `[count]` for `a(,` `[count]a)`, and `[count]ab`
* [ ] Implement `[count]` for `a[` and `[count]a]`
* [ ] Implement `[count]` for `i(,` `[count]i)`, and `[count]ib`
* [ ] Implement `[count]` for `i[` and `[count]i]`
* [x] Implement `[count]` for `n` after `#` (**Implemented in 1.27.0**)
* [x] Implement `[count]` for `n` after `*` (**Implemented in 1.27.0**)
* [ ] Implement `[count]` for `v`
* [ ] Implement `[{` go to `[count]` previous unmatched '{'. |exclusive| motion.
* [ ] Implement `])` go to `[count]` next unmatched ')'. |exclusive| motion.
* [ ] Implement `]}` go to `[count]` next unmatched '}'. |exclusive| motion.
* [ ] Implement `g*`, `g#`, etc.
* [x] ~`X` on empty line should delete line `x\n|\nx` -> `X` -> `x\n|x`~
* [x] ~`d$` on empty line should not ring visual bell~
* [x] ~`d0` on empty line should not ring visual bell~
* [x] ~`d^` on empty line should not ring visual bell~
* [ ] `gJ`
* [x] ~`gU` noop should do visual bell~
* [ ] `gqip` should move cursor to last line of block
* [x] ~`gu` noop should do visual bell~
* [ ] `ip` and `ap`, should enter VISUAL LINE mode
* [ ] `iw`, `aW`, `iW`, `as`, `is`, etc., when in VISUAL LINE, should enter VISUAL characterwise
* [ ] Add alias `<C-S-{char}>` => `<C-{uppercase}>`
* [ ] Add alias `<D-S-{char}>` => `<D-{uppercase}>`
* [ ] Add alias `<M-S-{char}>` => `<M-{uppercase}>`

## Work in Progress

See also [Part 1](#404), [Part 2](#711), and [Part 3](#854)

* [x] #924 (**Implemented in 1.32.0**)
* [ ] https://github.com/NeoVintageous/NeoVintageous/discussions/927
* [ ] All private settings should have a consistent prefix
* [ ] Rework mode handling to work like Vim #385 #374 https://github.com/NeoVintageous/NeoVintageous/commit/239b3bf69b52728cb2177b3ec6297ed3168fb346
* [ ] Remove deprecations

## F.A.Q.

## Known issues

Description | Issue | Sublime Text Issue
----------- | ----- | ------------------
Can't move cursor left and right in visual line mode | #640 | sublimehq/sublime_text/issues/3033
Goto symbol within a file automatically enters visual mode | #54 | sublimehq/sublime_text#3032
Window status is flaky | | sublimehq/sublime_text#627
Spell checking commands are flaky | | sublimehq/sublime_text#2539
Wrap Lines regression >=4061 | #774 | sublimehq/sublime_text#3177
Symbol jumping does not select text |  #753 | sublimehq/sublime_text#3032
Interactive command line prompts | #157 |