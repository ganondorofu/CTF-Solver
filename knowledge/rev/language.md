# language [rev]

## Writeup

# WRITE-UP: Language
# Challenge Description: 
Speaking is not the only way to communicate.Try to find an important message hidden in this file. EHAX{words_joined_by_underscores}

# Tools used:
1. Binary Ninja (<https://cloud.binary.ninja/>)
2. UTF-8 Converter (<https://www.cogsci.ed.ac.uk/~richard/utf-8.html>)

# Steps to get the solution
## 1. Analyzing the Description
As soon as i read the description of the challenge, it was a bit clear that this challenge revolves around some concept of language and has a hidden message somewhere.This message could be a combination of strings, an output of a .txt file or anything.

## 2.Analyzing the exe file
Once the exe file was downloaded from the the challenge/handout, it was pretty clear that we need to find the source code.For this i resorted with Binary Ninja (<https://cloud.binary.ninja/>).

I switched to the pseudo C option available in binary ninja as it helped me view the code in c language.

Once i got to pseudo C i scrolled endlessly for a long time until i reached the end. There i saw the main function which gave me some hope about this challenge.

Upon analyzing the main function i saw that the content of flag.txt is retrieved once we input the right password. Using the string option/or seeing the set_password() function i saw that the password is set as ```EHAXISACTIVE```.What was annoying was the fact that that there was remote connection being made, no flag.txt in the handout, hence running the .exe file made no sense and that is where i realised that this was going to be a long task.

## 3. Moving forward
Well once i accepted the fact that maybe there was no error in how this challenge was presented, i started scrolling through the code again and again just to see if anything made sense.

After sometime, i realised that there were a lot of functions that were defined in the code but never called in the main function.All of these function definitions seemed as if they weren't default.

This is when a little hope arose that maybe i was on the right track to solve the challenge.

```Once i went over the description once more```, which stated something about a message being hidden, i reaalised that maybe it is the functions that have these hidden messages that we need to find out.
I started going over the functions which were being showed to me on the  a side tab/bar on binary ninja

I accessed the first 4 functions and saw that all of them were returning an UTF-8 value.Looked them and boom i got the letter E,H,A,X which when combined spells "EHAX".
```
int __init__path() __pure
14000147a  {
140001484      return 0x45; 
14000147a  }
int __check__path(int* RWD_DEFINED)
int* arg_8  {Frame offset 8}
int result  {Register rax}
int* RWD_DEFINED  {Register rcx}
140001538  {
140001548      arg_8 = &RWD_DEFINED[1];
14000154c      int result = *RWD_DEFINED;
14000154c      
140001550      if (!result)
14000155a          return result;
14000155a      
140001552      return 0x48;
140001538  }

int __MEMORY__path(int* __V16_f)
int* __V16_f  {Register rcx}
14000159d  {
1400015ad      if (*__V16_f >= 0)
1400015b6          return 0x41; 
1400015b6      
1400015af      return 1;
14000159d  }

int __STACK__path() __pure
1400015bd  {
1400015c7      return 0x58; 
1400015bd  }
```
``` 
0x45 -> 'E'
0x48 -> 'H'
0x41 -> 'A'
0x58 -> 'x'
```

This is when i realised that this challenge is more about finding these appropriate UTF values rather than obsessing with why isnt there a remote connection or a flag.txt in the handout.

## 4. Analyzing the functions
Using the tab on the binary ninja that displayed the function, i could infer that the functions with similar names maybe led us to one word and as the description stated that thwe flag is a combination of words.
Going in continuity i saw that there were a lot decoy type functions which werent returing any frutiful values and were used by the author just to put more obstacles in a challenge which was already a bit off from what i would have expected.

Once i accessed most functions (trust me the noting down so many values was a bit tedious task), i could see i got something like this
```  
int __path__cplusplus11() __pure
1400015c8  {
1400015d2      return 0x270a;
1400015c8  }

  
```
At first i had ignored the UTF values's which weren't corresponding to any English alphabet's, but then i ended up trying to check what does these random UTF-8 values like ```0x270a etc ``` corerespond to.These corresponded to emoji's.
i used online UTF-8 tools like (<https://www.cogsci.ed.ac.uk/~richard/utf-8.html>) to see what these UTF values corresponded to .


It was a  bit funny and annoying as to how there were random emoji's in continuity with english alphabets which were still making a bit of sense.

## 5. Using the description
Well after being stuck for a bit of time, i realized that maybe the description was my biggest clue. It repeatedly used the word ```LANGUAGE, something related to communication, speaking```.
That is when i realized that maybe these emoji's are bascially hand gestures which might correspond to english alphabets when translated using the ```SIGN LANGUAGE``` standard.
I opened up the sign language chart to see what does these emoji's correspond to

![alt text](https://www.ai-media.tv/wp-content/uploads/ASL_Alphabet.jpg "sign language")


Well , i was still stuck as the i could see that it was still obvious and a bit too many rabbit holes were involved. Maybe tht was the whole idea behind the challenge to make the players keep at it and keep trying to see the hurdles one may encounter when trying to decode a hand gestures of sign langauge as i couldsee that the were a lot of hand gestures which don't even have a corresponding emoji in computer systems.

That is when i realised that maybe a single emoji maybe used to denote more that a single  letter and i had to decode this on my own depending on which would fit well in order make the word make sense , or a different orientation of that specific emoji which may very well corespond to a letter for example:
```👈 when rotated corresponds to the letter 'l' ```

# flag
EHAX{every_languaue_very_special}

# In a nutshell
Well this challenge was something unique and invovled few too many decoys. The flag.txt was a decoy right from the beginning as the users werent given a handout flag.txt or a remote connection.This was a bit smart as but a little demanding too because at first i was dismissive of the fact that this challenge wasnt missing something.

The description is what was the biggest clue or as i could say something that may possibly point someone in the right direction, although it is rare that a challenge relies a bit too much on the description of the challenge.

The word ```hidden``` meant that the message was indeed hidden in the code, but not as strings. They were there as UTF-8 values.What helped was the fact that all the user defined functions were in a continuity and had similar names if they were being  used to form a word.

The emoji part was a bit tedious, after going through the description one could indeed realize that sign language was in play, but due to the non availability of some emoji's which very well correspond to english alphabets if interpreted as hand gestures, one had to keep at it in this challenge and decode whether this emoji say ```0x270a which corresponds to ✊```  which closely correspond to letter `a` and `e` .

All in all this challenge was a bit tedious to solve and required a user not to miss a single thing , and was one of those rare challenges where the description is REALLY coming into play.