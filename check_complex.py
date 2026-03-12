from pwn import *
import hashlib
import itertools
import string
import re

def solve_pow(prefix):
    for length in itertools.count(1):
        for p in itertools.product(string.ascii_letters + string.digits, repeat=length):
            s = "".join(p)
            if hashlib.sha256((prefix + s).encode()).hexdigest().startswith('000000'):
                return s

io = remote('20.244.7.184', 4169)
io.recvuntil(b"sha256(")
prefix = io.recvuntil(b" +", drop=True).decode()
s = solve_pow(prefix)
io.sendlineafter(b"PoW answer: ", s.encode())
io.recvuntil(b"> ")

io.sendline(b"probe 0.05j")
print("Complex probe:", io.recvuntil(b"> ").decode())

io.sendline(b"probe 0.1,0.2")
print("Vector probe:", io.recvuntil(b"> ").decode())
