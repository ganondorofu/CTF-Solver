# ehax_radio [forensics]

## 問題概要

# EHAX Radio
Tune into EHAX radio!

`difficulty: hard` <br>
`author: anonimbus`

## Flag
```
EH4X{br0_l0ck3d_1n}
```

## Solution
* .iq files can be analysed by replaying them.
* They can either be replayed (TX only) using a raspberrypi with the command `sendiq` from [rpitx](https://github.com/F5OEO/rpitx)
* The sample rate and freq are provided in the file as strings.
* * `./sendiq -s 250000 -f 101e6 -t u8 -p 7 -i ehaxradio.iq`
* * a SDR device like RTL-SDR will be needed to recieve (RX) the RF and listen in SDRSharp.
* Or the iq files can be converted into a wav file with [iqToSharp](https://github.com/Marcin648/iqToSharp)
* * `./iqToSharp -s 250000 -f 101e6 -i ehaxradio.iq -o ehaxradio.wav`
* After passing the correct frequency and sample rate, we can get the intelligible audio.
* After opening it in "baseband file player" in source tab of SDRSharp and playing it
* We get the flag in the FM RDS section of sectrum viewer.

## Making Challenge
* Getting the audio from yt and making it into wav
* Transfer the wav to rpi and run `./pifmrds -freq 101 -audio waitwait.wav`  from [rpitx](https://github.com/F5OEO/rpitx)
* Listen for freq 101 using rtl-sdr and record it using
* * `./rtl_sdr.exe -s 250000 -w 132000 -g 35 -f 101e6 ehaxradio.iq`
* * sample rate 250000; bandwidth 132000; gain 35; freq 101MHz