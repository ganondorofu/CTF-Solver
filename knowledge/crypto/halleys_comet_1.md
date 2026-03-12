# Halley's Comet 1 [crypto]

## 問題概要

# Halley's Comet 1
My friend just went through a devastating breakup. Unable to cope, he vanished one night. Looking up at the night sky, I saw something extraordinary—a comet blazing across the heavens, but it wasn’t just any comet. Somehow, he was on it, searching for his lost love. The comet wasn’t following a typical path; its motion seemed deliberate, almost mathematical, as if it was tracing some secret cosmic equation.

At times, the comet would slow down, and I’d see a plume of red smoke rising from it. Each time this happened, I marked down the distance from Earth and the time. Was he trying to send me a message?

Help me find his ex.

`difficulty: easy` <br>
`author: stapat`

## Flag
```
EH4X{1_f0und_my_ex_0n_s0me_0ther_c0met_!et5_g0_there}
```

## Solution
* convert the .enc data from hex to readable values
* make a script to get any of the coordinate x or y from the distances given
* convert the value to ascii character
* you get the flag

## Making challenge
astronomy is fun

---

## Writeup

## Halley's Comet 1
Description - Description - My friend just went through a devastating breakup. Unable to cope, he vanished one night. Looking up at the night sky, I saw something extraordinary—a comet blazing across the heavens, but it wasn’t just any comet. Somehow, he was on it, searching for his lost love. The comet wasn’t following a typical path; its motion seemed deliberate, almost mathematical, as if it was tracing some secret cosmic equation.

At times, the comet would slow down, and I’d see a plume of red smoke rising from it. Each time this happened, I marked down the distance from Earth and the time. Was he trying to send me a message?

Help me find his ex.
## Flag
```
EH4X{1_f0und_my_ex_0n_s0me_0ther_c0met_!et5_g0_there}
```
## what we can infer
"looking up"- using ceil to round off the numbers

"distance" - must include some coordinates (x,y)

"Help me find his X" - we have to find one coordinate

## Solution

1. got the equation as -25x^2+289y^2=7225
2. converted the distances from hex and after writing a easy script to find a coordinate
3. we get some values which look like ascii values
4. after converting we get the flag
### scripts and data
```
[72.0961247992752][75.2159750756074][54.43261921497142][91.8634649562688][128.30719786598667][51.31957679032161][99.14993364879552][106.4377752492037][50.28228274926973][122.05805811241227][114.76808268315789][104.3554114701973][99.14993364879552][113.72672582154982][126.22409631821287][99.14993364879552][105.39658175845544][125.1825656410845][99.14993364879552][50.28228274926973][114.76808268315789][99.14993364879552][119.97512718004725][50.28228274926973][113.72672582154982][105.39658175845544][99.14993364879552][50.28228274926973][121.01658498251572][108.52022916677012][105.39658175845544][118.93368510765652][99.14993364879552][103.31426508591258][50.28228274926973][113.72672582154982][105.39658175845544][121.01658498251572][99.14993364879552][34.75923118035172][105.39658175845544][121.01658498251572][55.47065061439946][99.14993364879552][107.4789912681257][50.28228274926973][99.14993364879552][121.01658498251572][108.52022916677012][105.39658175845544][118.93368510765652][105.39658175845544][130.39035086468598]
```
```python
import math as m
import random
with open('mapping.enc', 'r') as file:
    content = file.read()
d=[[float(value)] for value in content.strip('[]\n').split('][')]
#-25x^2+289y^2=7225
flag=''
for i in d:
    d2=pow(i[0],2)
    x2=(289*d2-7225)/314
    flag=flag+chr(int(m.sqrt(m.ceil(x2))))
    # print(int(m.sqrt(m.ceil(x2)))) ascii values
print(flag)


```

---

## 解法スクリプト: soln.py

```python
import math as m
import random
with open('mapping.enc', 'r') as file:
    content = file.read()
d=[[float(value)] for value in content.strip('[]\n').split('][')]
print(d)
#-25x^2+289y^2=7225
flag=''
for i in d:
    d2=pow(i[0],2)
    x2=(289*d2-7225)/314
    flag=flag+chr(int(m.sqrt(m.ceil(x2))))
    # print(int(m.sqrt(m.ceil(x2)))) ascii values
print(flag)
```