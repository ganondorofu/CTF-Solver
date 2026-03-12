# math-moves [rev]

## 問題概要

# Math-Moves
`author:g1ow`

`difficulty: hard`

My sister's BF'S knows the best sequence of dance moves.
How do I even move?

flag_format = EH4X{move1_move2_move3_move4}

 https://drive.google.com/file/d/1Pq90FdDZm41JYs5AeBoKmw_w0pX5AqNq/view?usp=drive_link

---

## Writeup

# Math-Moves - EHAX CTF Writeup

## Challenge Overview

We’re given a compiled Python executable, `math-moves.exe`, which appears to be a 2×2 sliding puzzle game. The challenge description hints at using BFS (Breadth-First Search) to find a sequence of moves. However, the actual puzzle movement logic is hidden within a mysterious `moves.dll` file. Our goal is to reverse engineer this DLL and determine the correct inputs to solve the puzzle.

---

## Step 1: Extracting the Source Code

Since the executable was compiled using **PyInstaller**, we can extract the original Python files using **pyinstxtractor**:

```bash
python pyinstxtractor.py math-moves.exe
```

This extracts a directory called `math-moves.exe_extracted`, where we find `math-moves.pyc`. Decompiling this `.pyc` file using [PyLingual](https://www.pylingual.io/) reveals the full source code.

---

## Step 2: Understanding the Input Handling

The decompiled Python code contains the following function that handles user input:

```python
def handle_input():
    try:
        input_value = float(entry.get())
        moves = {UP_VALUE: 'up', DOWN_VALUE: 'down', LEFT_VALUE: 'left', RIGHT_VALUE: 'right'}
        for val, direction in moves.items():
            if abs(input_value - val) < 0.001:
                move_empty_space(direction)
                break
        if is_solved():
            messagebox.showinfo('Congratulations!', 'Puzzle solved!')
    except ValueError:
        print('Invalid input. Please enter a float.')
```

This function maps **float inputs** to movement directions. The `moves` dictionary is populated with values retrieved from `moves.dll`. Since the game logic relies on external movement values, we must reverse engineer `moves.dll` to determine the correct moves.

---

## Step 3: Reversing the DLL

Disassembling `moves.dll` in **IDA Pro** or **Ghidra** reveals the following C-like function:

```c
double get_1_value() {
    double sum = 0.0;
    for (int n = 1; n <= 5; n++) {
        sum += (tgamma(n + 2) / (pow(n, 3) + 2 * n + 1)) * pow(log(n + 3), 2) * exp(-n / 3);
    }
    return obfuscate(sum);
}

int main() {
    double up_value = get_up_value();
    printf("UP value: %.4f\n", up_value);

    double m_value = get_1_value();
    printf("M value: %.4f\n", m_value);

    return 0;
}
```

The function `get_1_value()` applies a complex mathematical transformation before calling `obfuscate()`, making it difficult to deduce values statically. However, by dynamically executing the DLL and extracting runtime values, we can retrieve the movement values.

---

## Step 4: Extracting Movement Values

By executing the DLL and applying the deobfuscation formula:

```python
def deobfuscate(value):
    return round(value / 42, 4)
```

We obtain the following movement values:

```
UP = 13.7015  
DOWN = 878.6  
LEFT = 4.0  
RIGHT = 9.1757  
```

---

## Step 5: Solving the Puzzle

The puzzle starts in a shuffled state:

```
3  1
2  0  (empty space)
```

We need to reach the solved state:

```
1  2
3  0
```

Using BFS to determine the shortest sequence of moves, we find the correct sequence of inputs:

```plaintext
LEFT-UP-RIGHT-DOWN
4.0 → 13.7015 → 9.1757 → 878.6
```

Submitting these values in the game completes the puzzle and reveals the flag:

```
EH4X{4.0_13.7015_9.1757_878.6}
```

**Flag:** `EH4X{4.0_13.7015_9.1757_878.6}`\
✨ *Keep Glowing*