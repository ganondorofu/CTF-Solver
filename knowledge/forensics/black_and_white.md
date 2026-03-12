# black_and_white [forensics]

## 問題概要

# Black and white

everything seems black and white, if you can see

`difficulty: medium`
`author: benzo`

## Flag
```
EH4X{BLACK_AINT_WHITE_BRUH}
```

## Writeup
[click here](./writeup)

---

## Writeup

# Black and White

## Description

> **Everything seems black and white, if you can see.**

---

## Solution

Given `handout.zip`, when unzipped twice, it produces an `out` folder containing  **5000 files** . Each file contains  **400 lines** , with each line having  **400 binary digits (0 or 1)** .

If we treat each file as a  **400x400 matrix** , we can visualize it as an image:

* `0` represents  **black** .
* `1` represents  **white** .

Using the following script, we generate **5000 images** from these binary matrices:

### **Solution Script** ([Download](./solution.py))

```python
import numpy as np
import cv2

# Extract out directory from the given zip file
# Run this solution.py in the same directory as the 'out' directory

for i in range(5000):
    f = open(f"./out/flag_{i+1}", "r")
    img_arr = np.array([[255 if int(z) == 1 else 0 for z in x.split(" ")] for x in f.read().split("\n")[:-1]], np.uint8)
    cv2.imwrite(f"./img/flag_{i+1}.jpg", img_arr)
    print(f"Made image {i+1}...")
```

(it'll take some time to run, also create img directory before running it)

After generating all the 5000 images, we manually inspect them in a file viewer. **One of these images (flag_3384.jpg) contains the flag text.**

![ehax ctf - black and white writeup](./img/flag.png)

Hence we get our flag:  `EH4X{BLACK_AINT_WHITE_BRUH}`

---

## 解法スクリプト: solution.py

```python
import numpy as np
import cv2


# extract out directory from given zip file
# run this solution.py in same directory as out directory

for i in range(5000):
    f = open(f"./out/flag_{i+1}", "r")
    img_arr = np.array([[255 if int(z) == 1 else 0  for z in x.split(" ")] for x in f.read().split("\n")[:-1]], np.uint8)
    cv2.imwrite(f"./img/flag_{i+1}.jpg", img_arr)
    print(f"Made image {i+1}...")

# Check image flag_3384.jpg after making image for all given grids
```