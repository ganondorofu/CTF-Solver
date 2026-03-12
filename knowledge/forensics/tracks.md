# Tracks [forensics]

## 問題概要

# Tracks
"The Track Not Taken"

`difficulty: easy` <br>
`author: stapat`

## Flag
```
EH4X{d00fen$hmirt7_l0v3ed_$t4cy}
```
## Solution
* Check for Audio tracks in .mp4 
* extract the audio tracks
* get the zips from the tracks
* by seeing the red channel of the qr code we get our password for the second zip
* now decoding the flag.txt with ROT6 , we get our flag

## Making challenge
why would someone not love phineas and ferb

---

## Writeup

# Tracks
Description - "The Track Not Taken"
## flag
```
EH4X{d00fen$hmirt7_l0v3ed_$t4cy}
```
## Solution 
We have `chall.mp4` which has 2 audio tracks.

## Steps
We can also see this by running:

```bash
$ ffmpeg -i chall.mp4
```

This reveals two audio streams with mappings `0:1` and `0:2`. Extracting them with:

```bash
$ ffmpeg -i chall.mp4 -map 0:1 -c copy audio1.mp3
$ ffmpeg -i chall.mp4 -map 0:2 -c copy audio2.mp3
```

After investigation, we saw that there are zips embedded in the audio tracks. Extracting them with:

```bash
$ binwalk -e audio1.mp3
$ binwalk -e audio2.mp3
```

One zip is locked, and one zip contains a PNG file with a QR code. After scanning the QR code, it says:

```
"not every QR should be scanned"
```

After more scanning, we noticed that there was color-based stenography. We got the text:

```
$t@cy*1245
```

Using this as the password for the other zip, we found a file `flag.txt` with:

```
YB4R{x00zyh$bgcln7_f0p3yx_$n4ws}
```

It looks like some ROT cipher. After decoding with ROT6, we got our flag:

```
EH4X{d00fen$hmirt7_l0v3ed_$t4cy}
```

## Binwalk Details

### audio2.mp3

```bash
$ binwalk -e audio2.mp3

DECIMAL       HEXADECIMAL     DESCRIPTION
899956        0xDBB74         Zip archive data, at least v2.0 to extract, compressed size: 2082, uncompressed size: 2642, name: qrf.png
902180        0xDC424         End of Zip archive, footer length: 22
```

### audio1.mp3

```bash
$ binwalk -e audio1.mp3

DECIMAL       HEXADECIMAL     DESCRIPTION
899956        0xDBB74         Zip archive data, encrypted at least v1.0 to extract, compressed size: 45, uncompressed size: 33, name: flag.txt
900161        0xDBC41         End of Zip archive, footer length: 22
```

## ffmpeg Output

```bash
$ ffmpeg -i chall.mp4

Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'chall.mp4':
  Metadata:
    major_brand     : isom
    minor_version   : 512
    compatible_brands: isomiso2avc1mp41
    encoder         : Lavf60.16.100
  Duration: 00:00:52.12, start: 0.000000, bitrate: 1220 kb/s
  Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p(tv, bt709, progressive), 640x360 [SAR 1:1 DAR 16:9], 935 kb/s, 25 fps, 25 tbr, 1000k tbn (default)
    Metadata:
      handler_name    : VideoHandler
      vendor_id       : [0][0][0][0]
      encoder         : Lavc61.19.100 libx264
  Stream #0:1[0x2](und): Audio: mp3 (mp4a / 0x6134706D), 48000 Hz, stereo, fltp, 138 kb/s (default)
    Metadata:
      handler_name    : SoundHandler
      vendor_id       : [0][0][0][0]
  Stream #0:2[0x3](und): Audio: mp3 (mp4a / 0x6134706D), 48000 Hz, stereo, fltp, 138 kb/s
    Metadata:
      handler_name    : SoundHandler
      vendor_id       : [0][0][0][0]

At least one output file must be specified.
```