# homework [misc]

## 問題概要

# Homework
Help me! `nc ipaddr port`

`difficulty: medium` <br>
`author: stapat, fakesinging`

## Flag
```
EH4X{7h4nk_y0u_h3lp1ng_m3_cu713}
```

## Solution
1. make a script for solving all the integrals

---

## Writeup

# Homework
Help me! `nc chall.ehax.tech 4242`
## flag
```
EH4X{7h4nk_y0u_h3lp1ng_m3_cu713}
```
## Solution 
we have to write a script to integrate all the functions provided , for best accuracy and precision i used scipy module 
the script goes as
```python
import socket
import re
from scipy.integrate import quad

def parse_integral(data):
    lines = [line.strip() for line in data.split('\n') if line.strip()]
    
    for i, line in enumerate(lines):
        if '∫' in line:
            try:
                upper = float(lines[i-1])
                lower = float(lines[i+1])
                equation = line.replace('∫', '').replace('dx', '').strip()
                return upper, lower, equation
            except Exception as e:
                print(f"Parsing error: {e}")
                return None, None, None
    return None, None, None

def parse_equation(eq):
    superscript_map = {
        '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
        '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9'
    }
    
    parts = re.findall(r'(\d+)x([⁰¹²³⁴⁵⁶⁷⁸⁹]+)', eq)
    if parts:
        coeff = int(parts[0][0])
        power = int(''.join(superscript_map[c] for c in parts[0][1]))
        return coeff, power
    return None, None

def solve_challenge():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('chall.ehax.tech', 4242))
    
    while True:
        data = ''
        while True:
            chunk = s.recv(4096).decode()
            if not chunk:
                break
            data += chunk
            if 'Answer:' in data:
                break
        
        print("\nReceived data:")
        print(data)
        
        if 'EH4X{' in data:
            print("Found flag!")
            break
        
        upper, lower, equation = parse_integral(data)
        if None in (upper, lower, equation):
            print("Failed to parse integral")
            break
        
        coeff, power = parse_equation(equation)
        if None in (coeff, power):
            print("Failed to parse equation")
            break
        def integrand(x):
            return coeff * x**power
        
        result, _ = quad(integrand, lower, upper)
        
        print(f"Integral: from {lower} to {upper} of {equation}")
        print(f"Coefficient: {coeff}, Power: {power}")
        print(f"Sending result: {result}")
        s.send(f"{result}\n".encode())
    
    s.close()

if __name__ == "__main__":
    solve_challenge()
```
### Script Explanation
* The parse_integral function:
it takes the integral notation (using the ∫ symbol)  and extracts the equation: upper limit, lower limit, and the equation
* The parse_equation function: it parses equations in the form of coefficient × x raised to some power and also handles superscript by converting them to normal numbers and returns coefficent and power 
* The solve_challenge funtion : it connects us to the server and uses scipy's quad to calculate integral and sends it to server

this script ran for 15-20 minutes solving 30k integrals and after that we got our flag

---

## 解法スクリプト: solve.py

```python
import socket
import re
from scipy.integrate import quad

def parse_integral(data):
    lines = [line.strip() for line in data.split('\n') if line.strip()]
    
    for i, line in enumerate(lines):
        if '∫' in line:
            try:
                upper = float(lines[i-1])
                lower = float(lines[i+1])
                equation = line.replace('∫', '').replace('dx', '').strip()
                return upper, lower, equation
            except Exception as e:
                print(f"Parsing error: {e}")
                return None, None, None
    return None, None, None

def parse_equation(eq):
    superscript_map = {
        '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
        '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9'
    }
    
    parts = re.findall(r'(\d+)x([⁰¹²³⁴⁵⁶⁷⁸⁹]+)', eq)
    if parts:
        coeff = int(parts[0][0])
        power = int(''.join(superscript_map[c] for c in parts[0][1]))
        return coeff, power
    return None, None

def solve_challenge():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('chall.ehax.tech', 4242))
    
    while True:
        data = ''
        while True:
            chunk = s.recv(4096).decode()
            if not chunk:
                break
            data += chunk
            if 'Answer:' in data:
                break
        
        print("\nReceived data:")
        print(data)
        
        if 'EH4X{' in data:
            print("Found flag!")
            break
        
        # Parse the integral
        upper, lower, equation = parse_integral(data)
        if None in (upper, lower, equation):
            print("Failed to parse integral")
            break
        
        # Parse the equation
        coeff, power = parse_equation(equation)
        if None in (coeff, power):
            print("Failed to parse equation")
            break
        
        # Calculate the integral
        def integrand(x):
            return coeff * x**power
        
        result, _ = quad(integrand, lower, upper)
        
        print(f"Integral: from {lower} to {upper} of {equation}")
        print(f"Coefficient: {coeff}, Power: {power}")
        print(f"Sending result: {result}")
        s.send(f"{result}\n".encode())
    
    s.close()

if __name__ == "__main__":
    solve_challenge()
```