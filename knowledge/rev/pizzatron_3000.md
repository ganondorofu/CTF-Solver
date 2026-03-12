# Pizzatron 3000 [rev]

## 問題概要

# 🍕 Pizzatron 3000
I miss Club Penguin. Pizzatron 3000 was my favorite mini-game. I wish I could just flip a switch and be teleported back to my childhood, where Flash games still run.
Maybe my little puffle can help.

`difficulty: hard` <br>
`author: g1ow`

## Flag
```
EH4X{1_MI5S_F1A5H_G4M3S}
```

---

## Writeup

# **Pizzatron 3000 - Writeup**  

> *"I miss Club Penguin. Pizzatron 3000 was my favorite mini-game. I wish I could find it. Maybe my little puffle can help."*  

`author: g1ow`

## **Step 1: Extracting the Files**  
After extracting the provided ZIP file, we found multiple files, including `game.swf`, indicating that the challenge involved a Flash-based game.  

## **Step 2: Reading the Instructions**  
A text file within the extracted contents provided the following message:  

```
I named my puffle Dodo and suddenly he speaks...........
Dodo: "Play the game, edit the Pizzatron."
Dodo: "Listen to me carefully."
```

This hinted at both playing the game and modifying an element called "Pizzatron."  

## **Step 3: Playing the Game**  
Using **Ruffle**, a Flash emulator, we launched the game. The gameplay involved making pizzas for penguins. However, upon completing the game, we encountered a **broken button**, preventing further progress. This suggested there was more to uncover beyond just playing the game.  

## **Step 4: Decompiling the SWF File**  
Following the hint to "edit the Pizzatron," we used **JPEXS Free Flash Decompiler** to analyze the game files. Instead of attempting to fix the broken button, we searched for hidden content within the **text directory**.  

## **Step 5: Finding the Flag**  
During our search, we discovered a hidden flag embedded within the game's text files:  

```
EH4X{I_M1S5_61UBPENGUIN}
```

## **Conclusion**  
This challenge required extracting and analyzing a Flash game, interpreting hints, and using a decompiler to uncover hidden text. It demonstrated the importance of reverse-engineering game files to reveal secrets.  

**Flag:** `EH4X{I_M1S5_61UBPENGUIN}` 🎉