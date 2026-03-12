# are-you-really-sane [misc]

## Writeup

# Are You Really Sane
description - trust me i got a O in maths


## Flag
```
EH4X{0h_d4mn_y0u_4r3_ju5t_in54n3_lik3_m3}
```
## Solution
* just overflow the integer limit in the discord bot 
* $add num1,num2 
* you'll get a message ```this the most i can give you https://discord.com/channels/1338938921303670844/1338938923325460652/1338946847133405308```
* copy the server id and make the iframe for discord in the format 
```html
<iframe src="https://discord.com/widget?id=1338938921303670844&theme=dark" width="350" height="500" allowtransparency="true" frameborder="0" sandbox="allow-popups allow-popups-to-escape-sandbox allow-same-origin allow-scripts"></iframe>
```
* scroll down to get your flag
* enjoy!!!!!!!