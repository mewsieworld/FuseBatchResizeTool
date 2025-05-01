# Manual Center Image Resizer

A tiny desktop app that lets you manually center images for batch standardization — no cropping, no stress.

Perfect for fuse assets, sprites, or literally any image that needs to fit inside a 200x200 square without losing anything.

![image](https://github.com/user-attachments/assets/b9219860-4570-460b-984a-0733e80aec63)

## What It Does

- Load a whole folder (recursively) of images
- Configurable Click where you want the center of each image to be
- Configurable Right-click to sample the background color
- Pads the image to fit perfectly inside a predetermined canvas size, or input one
- Saves as `.bmp` in a mirrored output folder, with or without a main timestamp folder

No cropping. No auto-alignment weirdness. Just your eye and your click.

### You Also Can...
- Preview past crops, or view what your current one will look like
- Configurable view of the background color and/or hex color code
- Use the arrow keys to cycle through the picture files in the chosen folder


## Why?

I made this because I was importing a bunch of fuses that weren’t made with the same resolution or alignment. I needed a way to batch process them, but I also wanted precise manual control — especially over centering and background matching.

This fixes that.

When you're making bulk fuses, often, you will have different resolutions for your cropped files. If you didn't and used a template, you can more easily bulk import the animations. This tool is for people who want to do that but did not use a template, or already made the existing assets and want to have it transferrable easily.

This is not to say it will not require manual adjustment in your fuse tool, but it should negate a lot of the stress you would've otherwise had if you were doing all of these by hand like I was.

## Features

The lastest release will ALWAYS support these features! The notes are just for users using legacy versions.

- Manual center selection (left-click) (configurable v2+)
- Background color sampling (right-click) (configurable v2+)
- Resolution-agnostic batch import
- Consistent output (200x200 BMP) (configurable consistent output v2+)
- Mirror original folder structure

### V2+

- Toolbar with more options
- Select new folder mid-session
- Choose between left and right mouse button features
- Choose output file resolution mid-session
- Option to create timestamp-based output folders, in case you want to do multiple versions of the same one

### V3+

- Shows Background Color in a box at the top by default, which can also be toggled off, or clicked to one-time change background color
- Allows using of arrow keys to move between images in the folder
- Preview Mode (off by default) for the last image rendered or a preview of the crop
- Show Hex code of the background color (off by default) (dynamically colored text to preserve contrast ratio [make reading easier]; v3.1+)
- Select multiple resolutions to output and view (v3.1+)
- Statistics for the program, in case you're into that (v3.1+)
- An in-program manual (just in case) (v3.1+)

## How to Use

1. Run the EXE (or the Python script itself if you are using an older version i.e. `pyw manual_resizer\__main__.pyw`, `py manual_resizerv2.py` etc.) 
2. Select the parent folder containing all your images
3. For each image:
   - Left-click where you want the center to be
   - Right-click on the background to set the padding color
   - Automatically moves to the next image
4. Find your processed images in the `output_resized/` or `output_resized/timestamp/` folder

## DISCLAIMER

This is admittedly vibes code. But I looked over it and it didn't seem like anything that could blow up my computer. However, if this still ails you, I suggest reviewing the python file(s) yourself and making something better, if you can. This is the best I got right now.

## If You're Using the Python Script

Make sure you have these installed/run this ahead of time in your terminal:

```pip install pillow```

I ran this on python 3.13.2 and have no plans to add support for other versions lol
