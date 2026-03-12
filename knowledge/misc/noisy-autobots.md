# noisy-autobots [misc]

## 問題概要

# NOIST AUTOBOTS
Decodicons really didn’t want us reading this QR code—it’s buried under a mess of noise. But we’re not out of luck. Bumblebee got a dataset full of noisy QR codes along with their clean versions.

Your job? Figure out how to use the dataset to restore the original QR code and reveal the hidden flag.

Can you clean up the noise and crack the code?
`difficulty: hard`
`author: cha0s`

## Flag
```
EHAX{n01s3_c4nc3ll4ti0n_f7w_6c9c6c9c}
```

## Hints
aHR0cHM6Ly93d3cueW91dHViZS5jb20vd2F0Y2g/dj0wVjk2d0U3bFk0dw==

## Solution
* write a py script to train on this dataset and denoise the qrcode
* run it
* scan qr code

## Making Challenge
had to train models 50+ times

---

## Writeup

# WRITEUP - NOISY AUTOBOTS

the task was simple users had to figure out ML methods to denoise an image, based on the enormous training data

the autobots was a hint to autoencoders - especially denoising autoencoders

solution
* process the data, you have clean and noisy qr codes fit for training a cleaning model
* write a training script, here is mine
```
#!/usr/bin/env python3
import os
from PIL import Image
from torch.utils.data import Dataset, DataLoader
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.transforms as transforms

# ==== Configuration ====
CLEAN_DIR = "clean"
NOISY_DIR = "noisy"
IMG_SIZE = (128, 128)  # (width, height)
BATCH_SIZE = 32
EPOCHS = 50
LEARNING_RATE = 1e-3

class QRDataset(Dataset):
    def __init__(self, noisy_dir, clean_dir, transform=None):
        self.noisy_dir = noisy_dir
        self.clean_dir = clean_dir
        self.noisy_files = sorted([f for f in os.listdir(noisy_dir) if f.endswith(".png")])
        self.clean_files = sorted([f for f in os.listdir(clean_dir) if f.endswith(".png")])
        self.transform = transform

    def __len__(self):
        return len(self.noisy_files)

    def __getitem__(self, idx):
        noisy_path = os.path.join(self.noisy_dir, self.noisy_files[idx])
        clean_path = os.path.join(self.clean_dir, self.clean_files[idx])
        noisy_img = Image.open(noisy_path).convert("L")
        clean_img = Image.open(clean_path).convert("L")
        if self.transform:
            noisy_img = self.transform(noisy_img)
            clean_img = self.transform(clean_img)
        return noisy_img, clean_img

transform = transforms.Compose([
    transforms.Resize(IMG_SIZE, interpolation=Image.NEAREST),
    transforms.ToTensor(),  # Converts to [C, H, W] with values in [0,1]
])

class Autoencoder(nn.Module):
    def __init__(self):
        super(Autoencoder, self).__init__()
        # Encoder
        self.enc_conv1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)
        self.enc_pool1 = nn.MaxPool2d(2, 2)
        self.enc_conv2 = nn.Conv2d(32, 16, kernel_size=3, padding=1)
        self.enc_pool2 = nn.MaxPool2d(2, 2)
        # Decoder
        self.dec_conv1 = nn.Conv2d(16, 16, kernel_size=3, padding=1)
        self.dec_conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        self.dec_conv3 = nn.Conv2d(32, 1, kernel_size=3, padding=1)
    
    def forward(self, x):
        # Encoder
        x = F.relu(self.enc_conv1(x))
        x = self.enc_pool1(x)
        x = F.relu(self.enc_conv2(x))
        x = self.enc_pool2(x)
        # Decoder
        x = F.relu(self.dec_conv1(x))
        x = F.interpolate(x, scale_factor=2, mode='nearest')
        x = F.relu(self.dec_conv2(x))
        x = F.interpolate(x, scale_factor=2, mode='nearest')
        x = torch.sigmoid(self.dec_conv3(x))
        return x


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Using device:", device)
    
    dataset = QRDataset(NOISY_DIR, CLEAN_DIR, transform=transform)
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=4)
    
    model = Autoencoder().to(device)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    
    model.train()
    for epoch in range(EPOCHS):
        running_loss = 0.0
        for batch_idx, (noisy, clean) in enumerate(dataloader):
            noisy = noisy.to(device)
            clean = clean.to(device)
            
            optimizer.zero_grad()
            outputs = model(noisy)
            loss = criterion(outputs, clean)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            if (batch_idx + 1) % 100 == 0:
                print(f"Epoch [{epoch+1}/{EPOCHS}], Step [{batch_idx+1}/{len(dataloader)}], Loss: {loss.item():.4f}")
        
        epoch_loss = running_loss / len(dataloader)
        print(f"Epoch [{epoch+1}/{EPOCHS}] Average Loss: {epoch_loss:.4f}")
    
    torch.save(model.state_dict(), "denoising_autoencoder.pt")
    print("Model saved as denoising_autoencoder.pt")

if __name__ == "__main__":
    main()
```
* write an inference script to use on the noisy flag one 
```
#!/usr/bin/env python3
import argparse
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
import torchvision.transforms as transforms

# (must match training model) 
class Autoencoder(nn.Module):
    def __init__(self):
        super(Autoencoder, self).__init__()
        # Encoder
        self.enc_conv1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)
        self.enc_pool1 = nn.MaxPool2d(2, 2)
        self.enc_conv2 = nn.Conv2d(32, 16, kernel_size=3, padding=1)
        self.enc_pool2 = nn.MaxPool2d(2, 2)
        # Decoder
        self.dec_conv1 = nn.Conv2d(16, 16, kernel_size=3, padding=1)
        self.dec_conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        self.dec_conv3 = nn.Conv2d(32, 1, kernel_size=3, padding=1)
    
    def forward(self, x):
        # Encoder
        x = F.relu(self.enc_conv1(x))
        x = self.enc_pool1(x)
        x = F.relu(self.enc_conv2(x))
        x = self.enc_pool2(x)
        # Decoder
        x = F.relu(self.dec_conv1(x))
        x = F.interpolate(x, scale_factor=2, mode='nearest')
        x = F.relu(self.dec_conv2(x))
        x = F.interpolate(x, scale_factor=2, mode='nearest')
        x = torch.sigmoid(self.dec_conv3(x))
        return x

def load_image(image_path, img_size=(128, 128)):
    transform = transforms.Compose([
        transforms.Resize(img_size, interpolation=Image.NEAREST),
        transforms.ToTensor(),  # Converts image to tensor [C, H, W] with values in [0,1]
    ])
    img = Image.open(image_path).convert("L")
    img = transform(img)
    img = img.unsqueeze(0)  
    return img

def save_image(tensor, output_path):
    # tensor shape: [1, 1, H, W] -> squeeze batch and channel dimensions
    tensor = tensor.squeeze(0).squeeze(0)
    img = transforms.ToPILImage()(tensor)
    img.save(output_path)

def main():
    parser = argparse.ArgumentParser(description="PyTorch Denoising Autoencoder Inference")
    parser.add_argument("input_image", help="Path to the input noisy image")
    parser.add_argument("--output", default="denoised.png", help="Filename for the output denoised image")
    parser.add_argument("--model", default="denoising_autoencoder.pt", help="Path to the trained model file")
    parser.add_argument("--img_size", type=int, nargs=2, default=[128, 128], help="Image size as width height")
    args = parser.parse_args()
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Using device:", device)
    
    model = Autoencoder().to(device)
    model.load_state_dict(torch.load(args.model, map_location=device))
    model.eval()
    
    img = load_image(args.input_image, img_size=tuple(args.img_size))
    img = img.to(device)
    
    with torch.no_grad():
        output = model(img)
    
    save_image(output.cpu(), args.output)
    print(f"Denoised image saved to {args.output}")

if __name__ == "__main__":
    main()
```

* tip : GPT IS YOUR FRIEND
* scan the qr code and you are good to go
*