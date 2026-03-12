# tazerman-into-the-dtuverse [forensics]

## 問題概要

# Tazerman: Into the DTUverse
My beloved Tazerman poster... torn apart. Each shred a painful reminder of what’s lost. But what if there’s more beneath the surface in the 'chunks' of my poster ? Could these fragments hold a hidden secret, waiting to be uncovered?
“With great files, comes great responsibility. Keep them in the same format, and you’ll uncover the truth." - Uncle Ben(zo)

Hint 1 : I tried to tie the poster by **'strings'** but failed..maybe you can try 

`difficulty: easy` <br>
`author: cha0s`

## Flag
```
EH4X{4y1_s4b4sh}
```

## Solution
* reconstruct the image by using text chunks which store the coordinates in each piece using a py script
* use aperi or any other tool to browse bit planes and find 9 pieces of qr code placed in perfect place 
* scan qr code and get the flag

---

## Writeup

# Tazerman: Into the DTUverse
My beloved Tazerman poster... torn apart. Each shred a painful reminder of what’s lost. But what if there’s more beneath the surface in the 'chunks' of my poster ? Could these fragments hold a hidden secret, waiting to be uncovered?
“With great files, comes great responsibility. Keep them in the same format, and you’ll uncover the truth." - Uncle Ben(zo)

## inferences 
* string chunks
* pieces of image
* hidden secret

## solutions
* the handouts contain 1200 images as pieces of a big image
* do strings on a image and read
  ![image](https://github.com/user-attachments/assets/27cc74e2-84ed-48e6-9690-99ecc2a307b4)
* the x coordinates are < 40 and y coordinates < 30, hence it is a 40x30 matrix
* script for joining them
  
  ```
  import cv2
  import os
  import numpy as np
  from PIL import Image
  
  def extract_coordinates_from_metadata(image_path):
      image_pil = Image.open(image_path)
      metadata = image_pil.text
      coordinate_str = metadata.get('Coordinate', '')
      if coordinate_str:
          coordinates = tuple(map(int, coordinate_str.strip('()').split(', ')))
          return coordinates
      return None
  
  def reconstruct_image_from_grid(grid_dir, grid_size=(30, 40), output_path="reconstructed_image.png"):
      rows, cols = grid_size
      first_image_path = None
      for file_name in os.listdir(grid_dir):
          if file_name.lower().endswith(".png"):
              first_image_path = os.path.join(grid_dir, file_name)
              break
      if first_image_path is None:
          print("Error: No grid images found in the directory.")
          return
      grid_image = cv2.imread(first_image_path, cv2.IMREAD_UNCHANGED)
      if grid_image is None:
          print(f"Error: Unable to load image at {first_image_path}")
          return
      cell_height, cell_width, _ = grid_image.shape
      reconstructed_image = np.zeros((rows * cell_height, cols * cell_width, 3), dtype=np.uint8)
      for file_name in os.listdir(grid_dir):
          if file_name.lower().endswith(".png"):
              grid_image_path = os.path.join(grid_dir, file_name)
              coordinates = extract_coordinates_from_metadata(grid_image_path)
              if coordinates:
                  x, y = coordinates
                  grid_image = cv2.imread(grid_image_path, cv2.IMREAD_UNCHANGED)
                  start_y = (y - 1) * cell_height
                  start_x = (x - 1) * cell_width
                  reconstructed_image[start_y:start_y + cell_height, start_x:start_x + cell_width] = grid_image
      cv2.imwrite(output_path, reconstructed_image)
      print(f"Reconstructed image saved to {output_path}")
  
  if __name__ == "__main__":
      grid_directory = r"/home/cha0s/Downloads/tazerman-poster"
      reconstruct_image_from_grid(grid_directory)
  ```
* you will get this picture
* ![image](https://github.com/user-attachments/assets/65b4010c-36ee-42d4-a522-16e5201d26e0)
* upload the image to aperisolve and you will find qr code pieces in the bit planes
* write a script to join them and read the flag

## fun fact 
the pic is of ehax president during a comiccon, i found somewhere on internet

## flag
`
EH4X{4y1_s4b4sh}
`