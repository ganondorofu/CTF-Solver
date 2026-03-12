# help_the_hacker [misc]

## 問題概要

# Help the Hacker
My hacker friend was trying to make a photo that cannot be decrpyted, He wants your help to test out if you can get the data from the photo or not.

`difficulty: medium` <br>
`author: Yegnis, Shield01, Warrior`

## Flag
```
EHAX{s73g_h1d3_is_n07_3N0ugh}
```

## Solution

1. **Decrypting the Text File**:
    - Download the provided `.txt` file and the `enc.c` file.
    - Analyze the `enc.c` file to understand the encryption algorithm.
    - Write a decryption function based on the reverse of the encryption algorithm.
    - Decrypt the contents of the `.txt` file using your decryption function to obtain the passphrase to input in the steghide.

2. **Checking metadata**:
    - Use `exiftool` to check the metadata of .jpg.
    - In the metadata there will be EHAX{ , which when joined with the decrypted text will form the passphrase to be inserted into the steghide tool.
    - Steghide passkey - `EHAX{thismightbetherealflag}`
   
4. **Extracting the Flag from the Photo**:
    - Use the `steghide` tool to extract the hidden data from the photo:
      ```sh
      steghide extract -sf <photo_filename>
      ```
    - The extracted data will be a string encoded in Base64 and encrypted using ROT13.
    - Decode the Base64 string and then apply ROT13 to obtain the flag.

---

## Writeup

# Writeup: Help the Hacker

## Challenge Description
My hacker friend was trying to make a photo that cannot be decrpyted, He wants your help to test out if you can get the data from the photo or not.

## Tools Used
- `steghide`: A steganography tool to extract hidden data from images.
- A text editor or IDE to read and modify the `enc.c` file.
- Base64 decoder and ROT13 decoder (online tools or custom scripts).

## Steps to Solve the Challenge

### Step 1: Decrypting the Text File
1. **Analyze `enc.c` File**:
    - We downloaded the provided `.txt` file and the `enc.c` file.
    - We carefully read and analyzed the `enc.c` file to understand the custom encryption algorithm used.

2. **Write Decryption Function**:
    - Based on our understanding of the encryption algorithm, we wrote a decryption function to reverse the encryption process.
   ```
    #include <stdio.h>
    #include <stdlib.h>
    #include <string.h>

    void decrypt(const char *encrypted_text, const char *mapping[], char *decrypted_text) {
        size_t len = strlen(encrypted_text);
        size_t i = 0;
        while (i < len) {
            int found = 0;
            for (int j = 0; j < 52; j++) {
                size_t map_len = strlen(mapping[j]);
                if (strncmp(&encrypted_text[i], mapping[j], map_len) == 0) {
                    if (j < 26) {
                        decrypted_text[strlen(decrypted_text)] = 'a' + j;
                    } else {
                        decrypted_text[strlen(decrypted_text)] = 'A' + (j - 26);
                    }
                    i += map_len;
                    found = 1;
                    break;
                }
            }
            if (!found) {
                decrypted_text[strlen(decrypted_text)] = encrypted_text[i];
                i++;
            }
        }
    }
    
    int main() {
        char encrypted_text[1024];
        printf("Enter the encrypted text: ");
        fgets(encrypted_text, sizeof(encrypted_text), stdin);
        encrypted_text[strcspn(encrypted_text, "\n")] = 0;
    
        const char *mapping[52] = {
            "@!", "#$", "%^", "&*", "()", "_+", "-=", "{}", "[]", ":;", "\"\"", "<>", ",.", "/?", "|\\", "`~",
            "12", "34", "56", "78", "90", "AB", "CD", "EF", "GH", "IJ", "KL", "MN", "OP", "QR", "ST", "UV",
            "WX", "YZ", "ab", "cd", "ef", "gh", "ij", "kl", "mn", "op", "qr", "st", "uv", "wx", "yz", "01",
            "23", "45", "67", "89"
        };
    
        char decrypted_text[256] = "";
        decrypt(encrypted_text, mapping, decrypted_text);
    
        printf("Decrypted text: %s\n", decrypted_text);
    
        return 0;
    }
   ```
 

3. **Decrypt the Text File**:
    - We compiled and ran our decryption function to decrypt the contents of the `.txt` file.
    - Command:
      ```sh
      gcc -o decrypt decrypt.c
      ./decrypt
      ```

4. **Obtain the Passphrase**:
    - The decrypted content of the `.txt` file was the passphrase for [steghide](http://_vscodecontentref_/1).

### Step 2: Extracting the Flag from the Photo
1. **Extract Hidden Data**:
    - We used the [steghide](http://_vscodecontentref_/2) tool to extract the hidden data from the provided photo using the passphrase obtained from the decrypted text file.
    - Command:
      ```sh
      steghide extract -sf <photo_filename> -p <passphrase>
      ```

2. **Decode Base64 and ROT13**:
    - The extracted data was a string encoded in Base64 and encrypted using ROT13.
    - We first decoded the Base64 string using an online Base64 decoder or a custom script.
    - After decoding, we applied ROT13 to the resulting string to obtain the flag.
    - Example Python script for ROT13:
      ```python
      import codecs

      encoded_string = "your_base64_decoded_string_here"
      decoded_string = codecs.decode(encoded_string, 'rot_13')
      print(decoded_string)
      ```

## Conclusion
By following the steps outlined above, we successfully decrypted the text file to obtain the passphrase for [steghide](http://_vscodecontentref_/3), and then used that passphrase to extract the hidden flag from the photo. This challenge tested our skills in steganography and cryptography, and we learned how to use various tools and techniques to solve complex problems.

## Flag
EHAX{s73g_h1d3_is_n07_3N0ugh}

## Passkey
EHAX{thismightbetherealflag}