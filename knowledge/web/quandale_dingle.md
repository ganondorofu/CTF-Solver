# quandale_dingle [web]

## 問題概要

# Quandale Dingle
What's up guys! It's Quandale Dingle here! (rheheheh) I have been arrested for multiple crimes. Including: Searching for videos which I shouldnt on 20.244.95.158:80 /stream

`difficulty: hard` <br>
`author: anonimbus, benzo`

## Flag
```
EH4X{55H_Tunn3linG}
```

## Solution
* The search box searches for video on youtube and saves it in database
* after trying the basic sqli payload `' OR '1'='1`, we see that all the videos we searched for are shown
* we check for available tables using `' UNION SELECT name, '', '', '' FROM sqlite_master WHERE type='table' --`. After scrolling down we see a table named `users`
* Then we proceed to dump the users table by `' union select username, password, '', '' from users --` and see a entry called quandale with text `quandale_s3cr3t_p47h` which is a backlink to this website
* A private key called quandale.pem downloads.
* We ssh using `ssh -i quandale.pem quandale@20.244.95.158`
* We get a restricted shell hence there is nothing we can do
* We run nmap on the ip on which the website is hosted and see that port 8080 is closed which is odd
* We do ssh tunneling using `ssh -i quandale.pem -L 8080:localhost:8080 quandale@20.244.95.158` and then run nmap on our localhost and we see that the port which we mirrored is using a VLC media server.
* We use VLC media player to open that network live stream and get the flag in the video http://localhost:8080/stream

## Making Challenge
- `vlc -I dummy "bruh.mp4" --sout="#transcode{vcodec=h264,acodec=mp3}:std{access=http,mux=ts,dst=localhost:8080}" --loop`
- opened port in azure but closed in program side