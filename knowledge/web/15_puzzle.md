# 15_puzzle [web]

## 問題概要

# 15_puzzle

it iz what it iz

`difficulty: medium`

`author: benzo`

## Flag
`EH4X{h499y_u_s0lv3d_15_9uzz13_100_7im35}`

## Writeup
[click here](./writeup)

---

## Writeup

# 15 Puzzle

## Description

> it iz what it iz


`author: benzo`

## Solution

### Understanding the Challenge

The challenge presents a **15-puzzle** game at the route `/p/<puzzle_id>`. This is a classic sliding puzzle with a  **4x4 grid** , where numbers **1 to 15** must be arranged in order, leaving the blank space in the  **bottom-right corner** .

![Game Screenshot](./img/game.png)

Each time we check our solution using the `Check` button, the website sends an array of movements taken by the blank space to the backend. These movements are encoded as:

* **Up:** `[-1, 0]`
* **Down:** `[1, 0]`
* **Left:** `[0, -1]`
* **Right:** `[0, 1]`

To automate solving the puzzle, we need to determine the sequence of correct moves and submit them.

### Automating the Solution

1. **Scraping Puzzle Data**
   * Using `BeautifulSoup`, we extract the puzzle grid from the webpage.
   * Convert the puzzle into a  **2D array** , representing the blank space as `0`.
2. **Solving the Puzzle**
   * We use the  **A* (A-star) algorithm* * to determine the optimal sequence of moves taken by blank space.
   * The algorithm minimizes the number of moves using the  **Manhattan distance heuristic** .
   * The solution returns a list of moves required to solve the puzzle.
3. **Automating Requests**
   * Submit the computed moves via a **POST request** to the `/p/<puzzle_id>/check` endpoint.
   * If correct, the response provides the next puzzle URL.
   * Repeat this process for  **100 puzzles** .
4. **Extracting the Flag**
   * After solving all 100 puzzles (it will take a long time), we receive a final URL `/fl4g_i5_you_c4n7_s33_m3`.
   * The flag is hidden in the response header  **`Hmm`** , which contains a Base64-encoded string.
   * Decoding it reveals the flag.
   * Note that the route `/g37_y0ur_r3al_fl4g` and the gif given in it is irrelevant. (just for fun)

### Solution Script

#### `sol.py` - [here](./sol.py)

```python
import requests
from bs4 import BeautifulSoup
from utils import get_moves
import base64

chall = "..." # challenge url goes here

home_html = requests.get(chall).text

soup = BeautifulSoup(home_html, 'html.parser')

puzzle_link = soup.a.get("href")

i = 1

while True:
    puzzle_soup = BeautifulSoup(requests.get(chall+puzzle_link).text, 'html.parser')

    # initially the array of puzzle loads in script tag
    puzzle = str(puzzle_soup.find("script")).split("\n")[1]

    # evaluate string array from script to python list
    puzzle = eval(puzzle[puzzle.find("["):-1])

    print(f"[*] Solving puzzle {i}")

    for row in puzzle:
        print(" ".join([str(x) for x in row]))

    # Our algo needs a hashable type tuble convert puzzle to tuple
    puzzle = tuple(tuple(row) for row in puzzle)

    solution_moves = get_moves(puzzle)

    print(f"Solved in {len(solution_moves)} moves...")

    r = requests.post(chall+puzzle_link+"/check", json={ "movements": solution_moves }).json()
  
    if r["solved"] == True:
        puzzle_link = r["next_puzzle"] # update puzzle link

        if not r["next_puzzle"].startswith("/p"):
            print("Found the flag...")
            print(base64.b64decode(requests.get(chall+r["next_puzzle"]).headers["Hmm"]).decode())
            break
        print(f"Got next puzzle: {r["next_puzzle"]}")
    else:
        continue

    print("\n")
    i += 1


```

#### `utils.py` - [here](./utils.py)

```python
import heapq

GOAL_STATE = (
    (1, 2, 3, 4),
    (5, 6, 7, 8),
    (9, 10, 11, 12),
    (13, 14, 15, 0)
)

def manhattan_distance(state, goal):
    distance = 0
    for i in range(4):
        for j in range(4):
            if state[i][j] != 0:
                goal_position = [(goal[row][col] == state[i][j]) for row in range(4) for col in range(4)]
                goal_row, goal_col = divmod(goal_position.index(True), 4)
                distance += abs(goal_row - i) + abs(goal_col - j)
    return distance


def get_neighbors(state):
    neighbors = []
    blank_pos = [(ix, iy) for ix, row in enumerate(state) for iy, i in enumerate(row) if i == 0][0]
    x, y = blank_pos
    to_move = [[-1, 0], [1, 0], [0, -1], [0, 1]] 
  
    for dx, dy in to_move:
        new_x = x + dx
        new_y = y + dy
        if 0 <= new_x < 4 and 0 <= new_y < 4:
            new_state = [list(row) for row in state]
            new_state[x][y], new_state[new_x][new_y] = new_state[new_x][new_y], new_state[x][y]
            neighbors.append(((tuple(tuple(row) for row in new_state), [dx, dy])))
  
    return neighbors

def a_star(start, goal):
    priority_queue = []
    heapq.heappush(priority_queue, (0, start, []))
    came_from = {start: None}
    cost_so_far = {start: 0}
  
    while priority_queue:
        _, current, moves = heapq.heappop(priority_queue)
  
        if current == goal:
            path = []
            while current:
                path.append(current)
                current = came_from[current]
            return path[::-1], moves
  
        for neighbor, move in get_neighbors(current):
            new_cost = cost_so_far[current] + 1
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost
                priority = new_cost + manhattan_distance(neighbor, goal)
                heapq.heappush(priority_queue, (priority, neighbor, moves+[move]))
                came_from[neighbor] = current
    return None




def is_solvable(tiles):
    flattened = [tile for row in tiles for tile in row]
    inv_count = sum(
        1
        for i in range(len(flattened))
        for j in range(i + 1, len(flattened))
        if flattened[i] and flattened[j] and flattened[i] > flattened[j]
    )
    empty_row = next(i for i, row in enumerate(tiles) if 0 in row)
    return (inv_count % 2 == 0) if empty_row % 2 else (inv_count % 2 == 1)


def get_moves(start_state):
    print("If solvable: ", is_solvable(start_state))
    solution_path, moves = a_star(start_state, GOAL_STATE)

    return moves

```

### Final Flag Extraction

After solving 100 puzzles, we receive a Base64-encoded string in the `Hmm` header at `/fl4g_i5_you_c4n7_s33_m3`. Decoding it:

```
RUg0WHtoNDk5eV91X3MwbHYzZF8xNV85dXp6MTNfMTAwXzdpbTM1fQ==
```

gives:

```
EH4X{h499y_u_s0lv3d_15_9uzz13_100_7im35}
```


Hence we get our flag -

```
EH4X{h499y_u_s0lv3d_15_9uzz13_100_7im35}
```

---

## 解法スクリプト: solve.py

```python
import heapq

GOAL_STATE = (
    (1, 2, 3, 4),
    (5, 6, 7, 8),
    (9, 10, 11, 12),
    (13, 14, 15, 0)
)

def manhattan_distance(state, goal):
    distance = 0
    for i in range(4):
        for j in range(4):
            if state[i][j] != 0:
                goal_position = [(goal[row][col] == state[i][j]) for row in range(4) for col in range(4)]
                goal_row, goal_col = divmod(goal_position.index(True), 4)
                distance += abs(goal_row - i) + abs(goal_col - j)
    return distance


def get_neighbors(state):
    neighbors = []
    blank_pos = [(ix, iy) for ix, row in enumerate(state) for iy, i in enumerate(row) if i == 0][0]
    x, y = blank_pos
    to_move = [[-1, 0], [1, 0], [0, -1], [0, 1]] 
    
    for dx, dy in to_move:
        new_x = x + dx
        new_y = y + dy
        if 0 <= new_x < 4 and 0 <= new_y < 4:
            new_state = [list(row) for row in state]
            new_state[x][y], new_state[new_x][new_y] = new_state[new_x][new_y], new_state[x][y]
            neighbors.append(((tuple(tuple(row) for row in new_state), [dx, dy])))
    
    return neighbors

def a_star(start, goal):
    priority_queue = []
    heapq.heappush(priority_queue, (0, start, []))
    came_from = {start: None}
    cost_so_far = {start: 0}
    
    while priority_queue:
        _, current, moves = heapq.heappop(priority_queue)
        
        if current == goal:
            path = []
            while current:
                path.append(current)
                current = came_from[current]
            return path[::-1], moves
        
        for neighbor, move in get_neighbors(current):
            new_cost = cost_so_far[current] + 1
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost
                priority = new_cost + manhattan_distance(neighbor, goal)
                heapq.heappush(priority_queue, (priority, neighbor, moves+[move]))
                came_from[neighbor] = current
    return None



def get_moves(start_state):
    solution_path, moves = a_star(start_state, GOAL_STATE)

    return moves
```