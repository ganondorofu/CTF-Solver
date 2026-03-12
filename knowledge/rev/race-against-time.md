# race-against-time [rev]

## 問題概要

# RaceAgainstTime

**Difficulty:** Medium  
**Author:** ved_dev

## Flag
```
EH4X{r4c3_4g41nst_t1m3_4ppl3_p13}
```

## Overview

RaceAgainstTime is a rev challenge where timing is everything. The game relies on a file named `score.txt` to check if you've met the win condition. When the score in that file is set to `-1`, you win and the flag is revealed.


## Overview

RaceAgainstTime is a chill challenge where timing is everything. The game relies on a file named `score.txt` to check if you've met the win condition. When the score in that file is set to `-1`, you win and the flag is revealed.

## Theory

In this challenge, the win condition is controlled by a file (`score.txt`). The game constantly checks this file, and if it sees a `-1`, it triggers a win. The provided script exploits this mechanism by repeatedly writing `-1` into the file every 10 milliseconds. This demonstrates a simple race condition where the timing of file writes affects the outcome of the program. 


## How to Solve

The solution is super simple:

1. **Get the File:** Make sure there's a `score.txt` file in your game directory.
2. **Run the Script:** Use the provided Python script. It constantly checks if `score.txt` exists and writes `-1` to it every 10 milliseconds.
3. **Win:** Once the file is updated with `-1`, the game detects the win condition and you'll see the flag.

In other words, the script does all the work for you by forcing the winning score!

## 
## The Script

Below is the Python script you can run:

```python
import os
import time

score_file = "score.txt"

while True:
    if os.path.exists(score_file):
        with open(score_file, "w") as f:
            f.write("-1")
    time.sleep(0.01)  # Sleep for 10 milliseconds
```