# Skeleton [forensics]

## 問題概要

# Skeleton
skeleton is the structure, flag format: `EH4X{string}`
<br>
[Handout](https://drive.google.com/file/d/1QVMQ7kYg2rA4LuX_najEzCs3gv68fK4Q/view?usp=sharing)

`difficulty: hard` <br>
`author: stapat`
## Hints 
1. Peek through those WINDOWS, and you shall see the skeleton.

## Flag
```
EH4X{c4l0rie}
```
## Solution
1. mount the .iso file and examine it in QdirStat or WinDirStat (preffered)
2. you can now see the string which was mentioned 
3. the string is ```c4l0rie```
![image](https://github.com/user-attachments/assets/c5d85334-4f3a-4316-8d85-5ea36f83c8b6)

# Making the challenge
* files can be classified according to thier sizes and file types , so i did the same

---

## Writeup

# Skeleton
skeleton is the structure, flag format: `EH4X{string}`
<br>
[Handout](https://drive.google.com/file/d/1QVMQ7kYg2rA4LuX_najEzCs3gv68fK4Q/view?usp=sharing)

## Flag
```
EH4X{c4l0rie}
```
## Solution
* firstly i mounted the iso file and looked at it and saw some folders related to the human skeleton , did everything possible 
* only got fake flags or random texts , then i noticed that in a folder there were several files with same extension but in between them were some with different extensions 
* and the description also mentioned the word `structure` so i started looking for softwares to analyze file structure and found softwares like `QdirStat` and `KdirStat` and `WinDirStat` , i used WinDirStat 
* when i opened it up i didnt get a string but it was something which i knew i was close , so i studied about this software and it depends on screen resolution . after chaning multiple resolutions 
* i got a string which was `c4l0rie` , i wrapped it in EH4X{....}

![image](https://github.com/user-attachments/assets/c5d85334-4f3a-4316-8d85-5ea36f83c8b6)