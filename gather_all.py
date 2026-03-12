from pwn import *
import hashlib
import itertools
import string
import numpy as np

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

io.sendline(b"observe")
obs = io.recvuntil(b"> ").decode()
print("OBSERVE:", obs)

results = []
epsilons = np.linspace(0.01, 0.15, 50).tolist() + np.linspace(-0.15, -0.01, 50).tolist()
epsilons = [float(e) for e in epsilons]

for ep in epsilons:
    io.sendline(f"probe {ep}".encode())
    res = io.recvuntil(b"> ").decode()
    val = None
    for line in res.split('\n'):
        line = line.strip()
        try:
            val = float(line)
            results.append((ep, val))
            break
        except ValueError:
            pass
    if val is None:
        print("Failed to parse probe:", res)
    io.sendline(b"reset")
    io.recvuntil(b"> ")

with open("probes.csv", "w") as f:
    for ep, val in results:
        f.write(f"{ep},{val}\n")
    
print("Saved 100 probes to probes.csv")
