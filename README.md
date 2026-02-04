# ✨ Neatify

A simple Windows cleanup and desktop organizer tool.

## Features

- 🗂️ **System Cleanup** - Removes temp files, prefetch, and logs
- 🌐 **Browser Cleanup** - Clears cache for Chrome, Edge, Brave, Opera
- 🖥️ **Desktop Organizer** - Sorts files into folders by type
- 🖼️ **Wallpaper Changer** - Downloads HD wallpapers from Unsplash
- 🗑️ **Recycle Bin** - One-click empty

## Usage

1. Download `Neatify.exe` from [Releases](https://github.com/hayalimnet/Neatify/releases)
2. Run the exe file
3. Done! No installation required.

> 💡 **Tip:** Run as Administrator for full system cleaning.

## Notes

- **Wallpapers are saved to:** `%LOCALAPPDATA%\Neatify\wallpaper.jpg`
- **Antivirus Warning:** Some antivirus may flag this as false positive. The source code is open for inspection.

## Custom API Key (Optional)

The wallpaper feature works out of the box. However, if you want to use your own Unsplash API key:

1. Get a free API key from [Unsplash Developers](https://unsplash.com/developers)
2. Set environment variable:
   ```
   setx UNSPLASH_KEY "your-api-key-here"
   ```
3. Restart the app

## License

MIT