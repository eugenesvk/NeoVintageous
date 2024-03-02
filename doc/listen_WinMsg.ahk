#Requires AutoHotkey v2.0
Persistent 1	; This script doesn't declare hotkeys, so needs this to stop it from exiting

; Listen to mode messages from Sublime Text's NeoVintageous plugin on mode changes and view changes to always know the current state of editing mode and allow setting a keybinding conditional on that information
global nv_mode := 0 ; Sublime Text's plugin NeoVintageous' mode
/* To get mode name of each number, run the following in Sublime Text's console
from NeoVintageous.nv.modes import M_ANY, Mode as M
print(f"integer values for NeoVintageous modes")
for m in M_ANY:
  print(f"{m} = {m+0}")
*/

; A simple example could be:
; 1. show different message boxes on Ctrl+Alt+0 in Normal/Insert modes
#HotIf nv_mode = 1 and WinActive("ahk_exe sublime_text.exe")
!^0::msgbox('#hotif nv_mode = 1 (normal), real nv_mode=' nv_mode,"Sublime Text NeoVintageous")
#HotIf
#HotIf nv_mode = 2 and WinActive("ahk_exe sublime_text.exe")
!^0::msgbox('#hotif nv_mode = 2 (insert), real nv_mode=' nv_mode,"Sublime Text NeoVintageous")
#HotIf
; A more useful example:
  ; tap  key I to enter Insert mode
  ; hold key I to exit  Insert mode
  ; proper hold vs tap is unfortunately a complicated mechanic, see https://github.com/eugenesvk/Win.ahk/tree/modtap for an experimental implementation


; 2. Show tooltip in the top left corner on each mode/view change with the number of the old/new modes
; set your NeoVintageous.kdl config to
; post_mode_message Class="AutoHotkey" name="listen_WinMsg.ahk" mid="nv_a61171a06fc94216a3433cf83cd16e35";
msgIDtxt := "nv_a61171a06fc94216a3433cf83cd16e35" ; must be set to the same value in NeoVintageous
listen_to_NeoVintageous()
listen_to_NeoVintageous() {
  static msgID := DllCall("RegisterWindowMessage", "Str",msgIDtxt), MSGFLT_ALLOW := 1
  if winID_self:=WinExist(A_ScriptHwnd) { ; need to allow some messages through due to AHK running with UIA access https://stackoverflow.com/questions/40122964/cross-process-postmessage-uipi-restrictions-and-uiaccess-true
    isRes := DllCall("ChangeWindowMessageFilterEx" ; learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-changewindowmessagefilterex?redirectedfrom=MSDN
      , "Ptr",winID_self  	;i	HWND 		hwnd   	handle to the window whose UIPI message filter is to be modified
      ,"UInt",msgID       	;i	UINT 		message	message that the message filter allows through or blocks
      ,"UInt",MSGFLT_ALLOW	;i	DWORD		action
      , "Ptr",0)          	;io opt PCHANGEFILTERSTRUCT pChangeFilterStruct
    ToolTip(isRes '`t' 'ChangeWindowMessageFilterEx on self' '`n' msgID '`t' 'msgID',0,30,9)
    SetTimer () => ToolTip(,,, 9), -5*1000
  }
  OnMessage(msgID, setnv_mode, MaxThreads:=1)
  setnv_mode(wParam, lParam, msgID, hwnd) {
    global nv_mode
    nv_mode := lParam
    ToolTip(wParam " → " lParam "`nold → new mode (old mode can be unreliable)",0,0,10)
    SetTimer () => ToolTip(,,,10), -5*1000
  }
}
