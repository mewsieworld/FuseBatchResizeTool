# Manual

## Overview

The Manual Center Image Resizer is a tool designed to help you quickly resize and center images with precise control over the background color and output dimensions.
It has many features, including bulk processing, preview modes, and easily all-cursor management for ease of usage.

## Basic Usage

1. Click "Folder > Open Folder" to select a folder containing images

2. Set your desired output resolution(s) using the resolution picker

3. Click on the image to set the center point

4. Right-click to pick a background color

5. Use the arrow keys to navigate between images


## Mouse Modes

- * **Left Click**: Set the center point of the image
- * **Right Click**: Pick background color from the image
- **Eyedropper Mode**: Click the BG Color label to activate eyedropper mode for precise color selection
* This is configurable in the options menu (Options > Mouse Mode) to switch between left and right mouse options.

## Preview Options

- **Off**: No preview shown
- **Show Last Output**: Displays the last processed image
- **Show Crop Preview**: Shows live preview of how the image will be cropped
You can only select one preview option at a time to reduce clutter of windows on your screen.

## Background Color Box

- Toggle the background color box on/off (Options > BG Color Box Options > Toggle BG Color Box)
- Change the position (top/bottom) (Options > BG Color Box Options > Change Location)
- Toggle between color name and hex code display (Options > BG Color Box Options > Toggle Hex Color)

## Keyboard Shortcuts
- **Left Arrow**: Previous image
- **Right Arrow**: Next image
- **Escape**: Cancel eyedropper mode
- **Ctrl+A**: Select all resolutions (only available on resolution selection screen)

## Output Structure
Images are saved in the following structure:

```
output_resized/
  ├── timestamp/
  │   ├── 50x50/
  │   │   └── original_folder_structure/
  │   └── 100x100/
  │       └── original_folder_structure/
```
or
```
output_resized/
  ├── timestamp/
  │   └── original_folder_structure/
  ```
  
## Statistics

The application tracks:

- Total files processed
- Time spent
- Estimated time saved
- Most used background colors
- Most used resolutions 

## Changelog

### Initial Release

- Manual center selection (left-click)
- Background color sampling (right-click)
- Resolution-agnostic batch import
- Consistent output (200x200 BMP)
- Mirror original folder structure


### V2 Upgrade

- Toolbar time!!!!
- Select new folder mid-session
- Choose between left and right mouse button features
- Choose output file resolution, as well as mid-session
- Option to create timestamp-based output folders, in case you want to do multiple versions of the same one


### v3 - Upgrade and More Polish

- Options Menu created
- Mouse Mode moved to Options menu
- Background color now visible in a box at the top so you can't miss it like I do
- You can also toggle off the Background Color Box if it bothers you or you don't think you need it in the Options Menu
- Or even better you can click the BG Color box to eyedrop if you solely want to rely on singular button input
- You can also preview the BG Color's Hex Code (for double confirmation) thanks to "Show Hex"
- Arrow keys allow you to select back and forth between images within the folder(s) selected
- Preview Mode allows you to preview either the last image rendered or your future render based on the mouse hover (off by default)
- Added icon :)
- Removed the god awful command prompt (changed file type to python gui)
- Changed filetree (less accessible to new users)
- Background options all moved to a singular branch under Options menu 
- Background box location is able to be changed from top or bottom

### v3.1 - Tweaks

- Images now load in the center for you to make it easier to click
- Multiple render options at once!
- Multiple preview windows at once! (Not multiple modes though, I feel like that's overwhelming)
- Manual added