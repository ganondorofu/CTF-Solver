from pwn import *
import hashlib
import itertools
import string

def solve_pow(prefix):
    for length in itertools.count(1):
        for p in itertools.product(string.ascii_letters + string.digits, repeat=length):
            s = "".join(p)
            if hashlib.sha256((prefix + s).encode()).hexdigest().startswith('000000'):
                return s

io = remote('20.244.7.184', 4169)
io.recvuntil(b"sha256(")
prefix = io.recvuntil(b" +", drop=True).decode()
io.sendlineafter(b"answer: ", solve_pow(prefix).encode())
io.recvuntil(b"> ")

vals = []
for i in range(10):
    io.sendline(b"probe 0.1")
    res = io.recvuntil(b"> ").decode()
    for line in res.split('\n'):
        line = line.strip()
        try:
            vals.append(float(line))
        except ValueError:
            pass

print("10 probes in SAME universe:", vals)
io.sendline(b"reset")
io.recvuntil(b"> ")

vals2 = []
for i in range(10):
    io.sendline(b"probe 0.1")
    res = io.recvuntil(b"> ").decode()
    for line in res.split('\n'):
        line = line.strip()
        try:
            vals2.append(float(line))
        except ValueError:
            pass

print("10 probes in NEW universe:", vals2)
