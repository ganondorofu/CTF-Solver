# MBR_Shenanigans [forensics]

## 問題概要

# MBR Shenanigans
Welcome to EHAX bootloader.

`difficulty: hard` <br>
`author: anonimbus`
## Flag
```
EH4X{b00t2boop}
```

## Solution
* boot using `qemu-system-i386 -fda disk.img -s -S &`
* attach gdb using `gdb -ix gdb_init_real_mode.txt -ex 'set tdesc filename target.xml' -ex 'target remote localhost:1234'`
* from the frames we can see that `bx=0xCAFE`
* if we set our bx register to 0xCAFE by `set $bx = 0xCAFE`
* and continue, we get our flag

# Making Challenge
bhai mat hi pucho toh achha hai