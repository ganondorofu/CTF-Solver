# Pizzatron 9000 [rev]

## 問題概要

# 🍕 Pizzatron 9000
I miss still Club Penguin. Pizzatron 3000 was my favorite mini-game. I wish I could just flip a switch and be teleported back to my childhood, where Flash games still run. Maybe my little puffle can help.

`difficulty: hard` 
`author: g1ow`

## Flag
```
EH4X{1_MI5S_F1A5H_G4M3S}
```

---

## Writeup

# 🍕 **Pizzatron 9000 - Writeup**  

> *I still miss Club Penguin. Pizzatron 3000 was my favorite mini-game. I wish I could just flip a switch and be teleported back to my childhood, where Flash games still worked. Maybe my little puffle can help.*  

`author: g1ow` 

---  


### **Step 1: Investigating the Game Files**  
To dig deeper, we decompiled the **SWF** file using **JPEXS Free Flash Decompiler** and searched for the flip switch in the game's code. Inside the **title frame**, we found the following snippet:  

```actionscript
function getCoins()
{
   if(coins == undefined)
   {
      coins = 0;
   }
   var _loc3_ = new Object();
   _loc3_.score = coins * 10;
   _loc3_.coins = coins;
   _root.showWindow("Game Over",_loc3_);
   _global.pizzatron_dl.stopGame(candyMODE);
   if(quit)
   {
      _global.pizzatron_dl.sendGameScore(candyMODE,"quit",_loc3_.score,_loc3_.coins);
   }
   else
   {
      _global.pizzatron_dl.sendGameScore(candyMODE,"lose",_loc3_.score,_loc3_.coins);
   }
}
if(_global.dlearning_learner_id == undefined)
{
   var SHELL = _global.getCurrentShell();
   _global.dlearning_learner_id = SHELL.getMyPlayerId();
}
stop();
com.clubpenguin.security.Security.doSecurityCheck(this._url,this._parent);
_root.LocaleText = com.clubpenguin.util.LocaleText;
var SHELL = _global.getCurrentShell();
var gameDirectory = com.clubpenguin.util.LocaleText.getGameDirectory();
var localeDirectory = "files/";
var loader = new MovieClipLoader();
loader.loadClip(gameDirectory + localeDirectory + "title.swf",title_mc.titlescreen_mc.titleImage);
title_mc.ui_play.text = _root.LocaleText.getText("ui_play");
title_mc.ui_instructions.text = _root.LocaleText.getText("title_instructions");
title_mc.titlescreen_mc.switch_mc.switch_handle.onRelease = function()
{
   if(candyMODE)
   {
      candyMODE = false;
      title_mc.titlescreen_mc.switch_mc.gotoAndStop(1);
   }
   else if("key" != "g1ow")
   {
      trace("Access Denied. Edit the code to enable Candy Mode.");
   }
   else
   {
      candyMODE = true;
      title_mc.titlescreen_mc.switch_mc.gotoAndStop(2);
      trace("Game mode: Candy Mode");
   }
};
var penguinColor = SHELL.getMyPlayerHex();
var colorObject = new Color(title_mc.titlescreen_mc.penguin_mc);
colorObject.setRGB(penguinColor);
candyMODE = false;
```  

### **Step 2: Analyzing the Code**  
From the decompiled code, we noticed that the **Candy Mode** switch had a built-in check:  

```actionscript
else if("key" != "g1ow")
{
   trace("Access Denied. Edit the code to enable Candy Mode.");
}
```

This condition **always evaluates to true**, meaning the game **never** enables Candy Mode. To bypass this restriction, we needed to **patch the code** by removing the check.  

### **Step 3: Patching the Code**  
By modifying the switch’s logic, we removed the condition that blocked Candy Mode:  

```actionscript
{
   if(candyMODE)
   {
      candyMODE = false;
      title_mc.titlescreen_mc.switch_mc.gotoAndStop(1);
   }
   else
   {
      candyMODE = true;
      title_mc.titlescreen_mc.switch_mc.gotoAndStop(2);
      trace("Game mode: Candy Mode");
   }
};
```  

### **Step 4: Enabling Candy Mode & Finding the Flag**  
After patching the code, the **flip switch** now worked as intended. We enabled **Candy Mode** and proceeded to **play the game**.  

Upon completing the game, an **audio clip** played, revealing the **flag**:  

```
EH4X{1_MI5S_F1A5H_G4M3S}
```

---  

## **Conclusion**  
This challenge required **reverse-engineering a Flash game**, identifying a **hidden restriction**, and **modifying the game logic** to unlock a secret mode. By patching the SWF file and playing the game in its modified state, we successfully retrieved the flag.  

**Flag:** `EH4X{1_MI5S_F1A5H_G4M3S}`