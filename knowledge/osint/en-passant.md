# en-passant [osint]

## 問題概要

# En Passant

Stacy is a chess enthusiast who runs a blog where she shares game analyses, strategies, and tournament updates. Recently, she posted a cryptic message hinting at a hidden secret on her blog. Your task is to investigate her blog and uncover the hidden message. find the last 5 moves of the game stacy refers to for the flag

Check blog at http://chall.ehax.tech:8856

`difficulty: hard`

`author: stapat, cha0s`

## Flag
`EH4X{ra4_kc5_dc5_nc5_qa1}`

## Writeup
[click here](./writeup.md)

---

## Writeup

# En Passant - OSINT Challenge Writeup

## Challenge description

Stacy is a chess enthusiast who runs a blog where she shares game analyses, strategies, and tournament updates. Recently, she posted a cryptic message hinting at a hidden secret on her blog. Your task is to investigate her blog and uncover the hidden message. find the last 5 moves of the game stacy refers to for the flag

Check blog at http://chall.ehax.tech:8856

---

1. "On Flight VJH643, at 1:18 AM" was mentioned in the first blog.
![En Passant - OSINT Challenge Writeup](./img/blog.png)

2. Tracking **Flight VJH643** on **FlightRadar24** 
[link](<https://www.flightradar24.com/data/flights/h5643>) showed that the flight was above **Tilburg** at that time.

![En Passant - OSINT Challenge Writeup](./img/flight.png)

3. A famous chess tournament was held in **Tilburg in 1981**, and the blog also mentioned **"A Grandmaster world champion"**, making it easier to find the reference.
   
5. The blog contained a chess game where **Sicilian Defense** was played.

![En Passant - OSINT Challenge Writeup](./img/chessgame.png)

5. Researching strong Sicilian Defense players led to **Viswanathan Anand** and **Garry Kasparov**.
6. **Viswanathan Anand** was ruled out as he became a Grandmaster in 1988, leaving **Garry Kasparov** as the likely player.
7. The second blog post had a **YouTube video** showing a **"Burning Tiger"**.[link](<https://youtu.be/CAm_bonffcQ?t=266>)

![En Passant - OSINT Challenge Writeup](./img/burningtiger.png)

8. Searching for **Kasparov's games in 1981 in Tilburg** led to the discovery of the game **"Tiger Tiger Burning Bright"**.

   **Game Link:** [ChessGames.com](https://www.chessgames.com/perl/chessgame?gid=1069975)

9. The last **five moves** of the game were:

   ```
   ra4_kc5_dc5_nc5_qa1
   ```

10. Wrapping these in **EH4X{}**, the final flag was:

    ```
    EH4X{ra4_kc5_dc5_nc5_qa1}
    ```