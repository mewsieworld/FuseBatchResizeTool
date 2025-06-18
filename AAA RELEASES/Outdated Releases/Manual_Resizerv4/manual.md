## Manual Overview

The Manual Center Image Resizer is a tool designed to help you quickly resize and center images with precise control over the background color and output dimensions.
It has many features, including bulk processing, preview modes, and easily all-cursor management for ease of usage.

[The repository is available here at any time.](https://github.com/mewsieworld/FuseBatchResizeTool)

## Basic Usage

1. Click "Folder > Open Folder" to select a folder containing images

2. Set your desired output resolution(s) using the resolution picker

3. Click on the image to set the center point

4. Right-click to pick a background color

5. Use the arrow keys to navigate between images

## Supported Stuff

- *.png
- *.jpg
- *.jpeg
- *.bmp 
- Folders

## Grids

- Hidden by default
- Your crosshair snaps to this grid!
- Displays a 1x1 grid across your screen
- Hides when you get too far away so it doesn't overtake the Image
- Configure the color in Options

This feature is NOT recommended for high resolutions. I cannot guarantee performance.

## Mouse Modes

- ^**Left Click**: Set the center point of the image
- ^**Right Click**: Pick background color from the image
- **Scroll Wheel**: Zoom in/out, also move zoom by holding. Can also be used with key commands for more zoom options.
- **Eyedropper Mode**: Click the BG Color label to activate eyedropper mode for precise color selection
^ This is configurable in the options menu (Options > Mouse Mode) to switch between left and right mouse options or can be switched at any time with **Ctrl+M**.

## Crosshairs

All of these snap to the invisible (by default) pixel grid

- **Pixel** - 1x1 pixel crosshair
- **Cross** - Configurable Cross pixel crosshair
- **Other Crosshair** - Configure your own size cross
- **Crosshair Color** - Self-explanatory 

This feature is NOT recommended for high resolutions (e.g. past 300x300). I cannot guarantee performance.

## Background Color Box

All these are configurable in (Options > Color Box)

- Toggle the background color box on/off
- Change the position (top/bottom)
- Toggle between color name and hex code display 

These are not configurable

- Right click the Reset button to bring up a secret RGB Background Color Picker :)

## Preview Options

- **Off**: No preview shown
- **Show Last Output**: Displays the last processed image
- **Show Crop Preview**: Shows live preview of how the image will be cropped

Both of these two preview modes are adjustable with an options menu that pops up when you initialize either.
You can select which resolutions you want using this window.

## Keyboard Shortcuts

- **Left Arrow**: Previous image
- **Right Arrow**: Next image
- **Escape**: Cancel eyedropper mode
- **Ctrl+A**: Select all resolutions (only on resolution selection screen)
- **Ctrl+O**: Opens a folder
- **Ctrl+G**: Toggle grid
- **Ctrl+D**: Open Log window
- **Ctrl+M**: Switch Mouse Mode
- **Ctrl+R**: Reset Background color
- **Ctrl+0**: Resets Zoom
- **Ctrl+-**: Decreases zoom by 10%
- **Ctrl++**: Increases zoom by 10%
- **Ctrl+Scroll wheel**: Zoom in and out
- **Ctrl+Shift+Scroll wheel**: Move the canvas left and right

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

You also can choose the folder location (File > Change Input Folder...). By default, it goes to the same folder/location as the .exe/.py files.


## Statistics

The application tracks (ONLY LOCALLY):

- Total files processed
- Time spent
- Estimated time saved
- Total Sessions
- Files saved that session
- Largest batch of files converted
- Longest session with the app
- Most used background colors
- Most used resolutions 
- Last accessed
- Last accessed file name+time
- Top file types converted with
- Pixels processed
- Folders Extracted

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
- Made text on background color picker more visible/accessible/dynamic
- Error for no images selected moved to BEFORE the filestamp option, and then reprompts you to select a folder

### v4 - Keyboard Shortcuts, Transparency Support, and More!

- Works with transparent images, turning them to magenta
- Allows zooming in and out with the scroll wheel as well as clicking and holding scrollwheel to pan
- Scroll in/out/reset using `ctrl`+`+` or `-` or `0`
- Option to configure the output of the folder (script folder by default)
- Scrolling left+right (`ctrl+scrollwheel`) or up and down (`ctrl+shift+scrollwheel`)
- Added crosshairs (two options: invert singular pixel underneath or a configurable crosshair of pixels)
- Crosshair cursor snaps to an invisible pixel grid which can be displayed and changed the color of under Options 
- Added fun statistics :) 
- Added a Debug Mode which will create a console and print to it
- Upgraded the RGB color picking...everywhere.
- Upgraded the BG Color Box Menu 
- Removed About menu option -> Migrated to Manual
- Works with transparent images! Yes, even the previews!
- Right clicking the Reset Background Color button brings up a colorpicker