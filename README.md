# ✨ Neatify

A cross-platform PC cleanup and desktop organizer tool.

**Current version:** v1.3.0

Open the in-app **About** panel for version information and the [Neatify GitHub repository](https://github.com/hayalimnet/Neatify).

**Supports:** Windows & Linux (Ubuntu, Fedora, Arch, etc.)

## Features

- 🗂️ **System Cleanup** - Lets users choose individual temp, cache, prefetch, and log targets
- 🌐 **Safe Browser Cleanup** - Lets users choose browsers individually and clears disposable cache without removing login data by default
- ⚠️ **Advanced Browser Cleanup** - Optional deeper cleanup with a clear site-data warning
- 🖥️ **Desktop Organizer** - Previews file moves, handles name conflicts safely, and supports undo (shortcuts organized into dedicated `Shortcuts/` folder)
- 🖼️ **Wallpaper Changer** - Downloads HD wallpapers from Unsplash
- 🗑️ **Empty Trash** - One-click empty (Recycle Bin on Windows, Trash on Linux)

Before analysis, choose the cleanup categories with the checkboxes in the options panel. After analysis, the embedded `Cleanup Details` panel lets users include or exclude individual cleanup targets before the confirmation preview. Desktop organization also provides a file-by-file move preview, optional conflict renaming, and an undo action. A fresh scan is required if the main cleanup selection changes.

## Installation

### Windows
1. Download the latest [Neatify release](https://github.com/hayalimnet/Neatify/releases)
2. Run!

> 💡 **Tip:** Run as Administrator for full system cleaning.

Windows releases are built with Nuitka to reduce antivirus false positives. For a local build, install the dependencies and Nuitka, then run `build_neatify.bat`.

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
- **Antivirus Warning:** Antivirus software can occasionally flag unsigned cleanup utilities as false positives. The source code is open for inspection, and Windows releases are built with Nuitka.

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
