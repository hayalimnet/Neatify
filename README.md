# ✨ Neatify

A cross-platform PC cleanup and desktop organizer tool.

**Supports:** Windows & Linux (Ubuntu, Fedora, Arch, etc.)

## Features

- 🗂️ **System Cleanup** - Removes temp files, cache, and logs
- 🌐 **Browser Cleanup** - Clears cache for Chrome, Edge, Brave, Opera, Firefox
- 🖥️ **Desktop Organizer** - Sorts files into folders by type (shortcuts organized into dedicated `Shortcuts/` folder)
- 🖼️ **Wallpaper Changer** - Downloads HD wallpapers from Unsplash
- 🗑️ **Empty Trash** - One-click empty (Recycle Bin on Windows, Trash on Linux)

## Installation

### Windows
1. Download `Neatify.exe` from [Releases](https://github.com/hayalimnet/Neatify/releases)
2. Run the exe file
3. Done! No installation required.

> 💡 **Tip:** Run as Administrator for full system cleaning.

### Linux

**One-liner install (Ubuntu/Debian/Fedora/Arch):**
```bash
curl -sSL https://raw.githubusercontent.com/hayalimnet/Neatify/main/install.sh | bash
```

This will:
- ✅ Install dependencies automatically
- ✅ Create virtual environment
- ✅ Add `neatify` command to your PATH
- ✅ Create desktop shortcut

**Run anytime with:**
```bash
neatify
```

> 💡 **Tip:** Run with `sudo neatify` for full system cleaning.

**Supported Desktop Environments:** GNOME, KDE Plasma, XFCE (Linux Mint), Cinnamon, MATE, i3, bspwm, and more

## Notes

- **Wallpapers are saved to:**
  - Windows: `%LOCALAPPDATA%\Neatify\wallpaper.jpg`
  - Linux: `~/.local/share/neatify/wallpaper.jpg`
- **Antivirus Warning:** Some antivirus may flag this as false positive. The source code is open for inspection.

## Custom API Key (Optional)

The wallpaper feature works out of the box. However, if you want to use your own Unsplash API key:

1. Get a free API key from [Unsplash Developers](https://unsplash.com/developers)
2. Set environment variable:
   - **Windows:**
     ```
     setx UNSPLASH_KEY "your-api-key-here"
     ```
   - **Linux:**
     ```bash
     echo 'export UNSPLASH_KEY="your-api-key-here"' >> ~/.bashrc
     source ~/.bashrc
     ```
3. Restart the app

## License

MIT