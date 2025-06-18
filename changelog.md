# Initial Release

- Manual center selection (left-click)
- Background color sampling (right-click)
- Resolution-agnostic batch import
- Consistent output (200x200 BMP)
- Mirror original folder structure


# V2 Upgrade

- Toolbar time!!!!
- Select new folder mid-session
- Choose between left and right mouse button features
- Choose output file resolution, as well as mid-session
- Option to create timestamp-based output folders, in case you want to do multiple versions of the same one


# v3 - Upgrade and More Polish

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

# v3.1 - Tweaks

- Images now load in the center for you to make it easier to click
- Multiple render options at once!
- Multiple preview windows at once! (Not multiple modes though, I feel like that's overwhelming)
- Manual added
- Made text on background color picker more visible/accessible/dynamic
- Error for no images selected moved to BEFORE the filestamp option, and then reprompts you to select a folder

# v4 - Keyboard Shortcuts, Transparency Support, and More! 

- Works with transparent images, turning them to magenta
- Allows zooming in and out with the scroll wheel as well as clicking and holding scrollwheel to pan
- Scroll in/out/reset using `ctrl`+`+` or `-` or `0`
- Option to configure the output of the folder (script folder by default)
- Scrolling left+right (`ctrl+scrollwheel`) or up and down (`ctrl+shift+scrollwheel`)
- Added crosshairs (two options: invert singular pixel underneath or a configurable crosshair of pixels)
- Crosshair cursor snaps to an invisible pixel grid which can be displayed and changed the color of under Options 
- Added fun statistics :) 
- Added a Debug Mode which will create a console and print to it
- Upgraded the color picking...everywhere.
- Upgraded the BG Color Box Menu 
- Removed About menu option -> Migrated to Manual
- Works with transparent images! Yes, even the previews!
- Right clicking the Reset Background Color button brings up a colorpicker

# v4.1 - NECESSARY BUG FIX

- Fixed File Structure being not retained upon output

