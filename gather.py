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

def do_probe(eps, count=20):
    vals = []
    for i in range(count):
        io.sendline(f"probe {eps}".encode())
        res = io.recvuntil(b"> ").decode()
        for line in res.split('\n'):
            line = line.strip()
            try:
                vals.append(float(line))
            except ValueError:
                pass
        io.sendline(b"reset")
        io.recvuntil(b"> ")
    print(f"PROBE {eps} results:", vals)
    return vals

do_probe(0.1)
do_probe(-0.1)
