# Retrievetheflag [misc]

## 問題概要

# Retrieve the flag
Sit back , relax and enjoy this audio since you are going to have to decrypt a lot of things soon.

`difficulty: easy` <br>
`author: Warrior`

## Flag
```
EHAX{looks@you##finally__found+_the%flag_or_did_you?}
```

## Solution
1. Listen to the audio provided in the challenge.

2. Use online tools to view the spectrogram of the audio(.wav file). Around 1:45 minutes into to the song the spectrogram will show `:DE9:D4@CC64E` which when decrypted using rot47 gives you the passphrase to the password protected gif . The passphrase is `isthiscorrect`

3. The gif is misleading as the actual flag is present in the metadata and the flag has been encrypted . After accessing the metadata a comment can be found `
JMFC{qttpx@dtz##knsfqqd__ktzsi+_ymj%kqfl_tw_ini_dtz?}
` . 

4. Using online tools like cyberchef (<https://gchq.github.io/CyberChef/>),use the rot13 bruteforce decrypt option to decrypt the text found in the metadata of the gif. The final flag is `EHAX{looks@you##finally__found+_the%flag_or_did_you?}`

---

## Writeup

# Writeup : Retrieve the flag

# Challenge Description
Sit back , relax and enjoy this audio since you are going to have to decrypt a lot of things soon.

# Tools used
1. Cyberchef/other online decryption tools.
2. Online spectral analysis tools(like decode (<https://www.dcode.fr/spectral-analysis>)), platforms like audacity.
3. online metadata viewers(<https://www.metadata2go.com/view-metadata>).

# Steps to solve the challenge
## 1. Analyzing the handouts
The handouts contained an audio file and .zip file which was password protected. It was clear that password for the .zip file had to be retrieved from the audio
## 2. Analyzing the audio
Well, this was an interesting audio seemed like a theme song which was lost over time.At about ```1:45 / 1min 45 seconds``` one could hear a random alien like sharp,high pitched noise/sound which clearly implied one had to use online tools like decode (or installed tools like audacity) to view the spectrogram (spectral analysis of the audio).

The spectal analysis of the audio file led us to the text ```:DE9:D4@CC64E``` .At first one might be tempted to use this as the password for the .zip file which had a flag.gif, but it became clearer after a failed attempt that this wasn't the password.This text was actually encrypted and had to decrypted.

For decryption one could use a platform like cyberchef(<https://gchq.github.io/CyberChef/>), this was a rot47 encrypted text which is one of the most commonly used ways of encrypting data in a mild way.The output after decrypting it was ```isthiscorrect```

## 3. Analyzing the flag.gif
Well as soon as you enter the password for the password protected file as ``` isthiscorrect```, you gain access to the flag.gif which is a high paced gif wherein i could see something like ```EHAX,{},IS```. Due to the gif being very high paced, one could not figure out all the words that are present in the gif.

Upon using each word obtained from each frame of the gif, one gets something like ```EHAX,WHERE,IS,THE,FLAG```. Upon bringing these words to what might be an ideal flag format as the format flag for this challenge wasnt mentioned you get something like ```EHAX{WHERE_IS__THE_FLAG}```.

Shockingly and well realising now that it wasn't the flag all along because you didnt even have the flag format, this ```EHAX{WHERE_IS_THE_FLAG}``` wasn't the flag

## 4. Moving Forward
Once i realised that the what i got before was a decoy flag, i straightaway resorted to viewing the metadata of the gif.

The metadata of the gif had something intriguing .
The comment present in the metadat is
```
JMFC{qttpx@dtz##knsfqqd__ktzsi+_ymj%kqfl_tw_ini_dtz?}
```
which can be decrypted using rot13 brute force.

# Flag
```EHAX{looks@you##finally__found+_the%flag_or_did_you?}```