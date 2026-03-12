import hashlib
import itertools
import string
import time
import sys
from pwn import *

def solve_pow(prefix):
    for length in itertools.count(1):
        for p in itertools.product(string.ascii_letters + string.digits, repeat=length):
            s = "".join(p)
            if hashlib.sha256((prefix + s).encode()).hexdigest().startswith('000000'):
                return s

io = remote('20.244.7.184', 4169)
io.recvuntil(b"sha256(")
prefix = io.recvuntil(b" +", drop=True).decode()
print("Solving PoW for", prefix)
s = solve_pow(prefix)
io.sendlineafter(b"PoW answer: ", s.encode())
print("PoW solved!")

io.interactive()
