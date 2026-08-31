import customtkinter as ctk
from tkinter import messagebox
import os
import shutil
import pathlib
import stat
import sys
import threading
import platform

try:
    from PIL import Image
except ImportError:
    Image = None

APP_NAME = "Neatify"
APP_VERSION = "1.3.1"
REPOSITORY_URL = "https://github.com/hayalimnet/Neatify"

# Platform detection
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

# Only import ctypes on Windows
if IS_WINDOWS:
    import ctypes
    try:
        import winreg
    except Exception:
        winreg = None


def get_windows_desktop_path(user_profile):
    """Resolve the actual Desktop path on Windows (supports OneDrive redirect)."""
    if not IS_WINDOWS:
        return os.path.join(user_profile, 'Desktop')

    candidates = []

    # 1) Preferred source: User Shell Folders (can include %USERPROFILE%)
    if winreg is not None:
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            ) as key:
                desktop_value, _ = winreg.QueryValueEx(key, 'Desktop')
                expanded = os.path.expandvars(desktop_value)
                if expanded:
                    candidates.append(expanded)
        except Exception:
            pass

        # 2) Fallback: Shell Folders (already expanded)
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
            ) as key:
                desktop_value, _ = winreg.QueryValueEx(key, 'Desktop')
                if desktop_value:
                    candidates.append(desktop_value)
        except Exception:
            pass

    # 3) Common fallbacks
    candidates.append(os.path.join(user_profile, 'Desktop'))
    one_drive = os.environ.get('OneDrive') or os.environ.get('OneDriveConsumer') or os.environ.get('OneDriveCommercial')
    if one_drive:
        candidates.append(os.path.join(one_drive, 'Desktop'))

    # Pick first existing directory; otherwise return first candidate
    for path in candidates:
        if path and os.path.isdir(path):
            return path

    return candidates[0] if candidates else os.path.join(user_profile, 'Desktop')

# Lazy import - speeds up app startup
requests = None
def get_requests():
    global requests
    if requests is None:
        import requests as req
        requests = req
    return requests

# --- ADMIN CHECK ---
def is_admin():
    """Check for administrator/root privileges"""
    try:
        if IS_WINDOWS:
            return ctypes.windll.shell32.IsUserAnAdmin()
        else:
            return os.geteuid() == 0
    except:
        return False

# --- RESOURCE PATH (FOR EXE) ---
def resource_path(relative_path):
    """Return the path to bundled resource files in frozen application builds."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# --- SETTINGS AND PATHS ---
if IS_WINDOWS:
    USER_PROFILE = os.environ.get('USERPROFILE', '')
    LOCAL_APP_DATA = os.environ.get('LOCALAPPDATA', os.path.join(USER_PROFILE, 'AppData', 'Local'))
    ROAMING_APP_DATA = os.environ.get('APPDATA', os.path.join(USER_PROFILE, 'AppData', 'Roaming'))
    
    TARGET_DIRS = {
        "System Temp": r'C:\Windows\Temp',
        "User Temp": os.path.join(LOCAL_APP_DATA, 'Temp'),
        "Prefetch": r'C:\Windows\Prefetch',
        "Logs": r'C:\Windows\Logs'
    }
    
    BROWSER_PATHS = {
        "Chrome": os.path.join(LOCAL_APP_DATA, r"Google\Chrome\User Data"),
        "Edge": os.path.join(LOCAL_APP_DATA, r"Microsoft\Edge\User Data"),
        "Brave": os.path.join(LOCAL_APP_DATA, r"BraveSoftware\Brave-Browser\User Data"),
        "Opera": os.path.join(ROAMING_APP_DATA, r"Opera Software\Opera Stable"),
        "Opera GX": os.path.join(ROAMING_APP_DATA, r"Opera Software\Opera GX Stable")
    }
    
    FIREFOX_PATH = os.path.join(ROAMING_APP_DATA, r"Mozilla\Firefox\Profiles")
    DESKTOP_PATH = get_windows_desktop_path(USER_PROFILE)
    
else:  # Linux
    # Handle sudo: get real user's home, not root's
    _sudo_user = os.environ.get('SUDO_USER')
    if _sudo_user:
        USER_PROFILE = os.path.join('/home', _sudo_user)
    else:
        USER_PROFILE = os.path.expanduser('~')
    
    LOCAL_APP_DATA = os.path.join(USER_PROFILE, '.local', 'share')
    ROAMING_APP_DATA = os.path.join(USER_PROFILE, '.config')
    
    TARGET_DIRS = {
        "System Temp": '/tmp',
        "User Cache": os.path.join(USER_PROFILE, '.cache'),
        "Thumbnails": os.path.join(USER_PROFILE, '.cache', 'thumbnails'),
        "Logs": '/var/log'
    }
    
    BROWSER_PATHS = {
        "Chrome": os.path.join(ROAMING_APP_DATA, 'google-chrome'),
        "Chromium": os.path.join(ROAMING_APP_DATA, 'chromium'),
        "Brave": os.path.join(ROAMING_APP_DATA, 'BraveSoftware', 'Brave-Browser'),
        "Opera": os.path.join(ROAMING_APP_DATA, 'opera'),
        "Vivaldi": os.path.join(ROAMING_APP_DATA, 'vivaldi')
    }
    
    FIREFOX_PATH = os.path.join(USER_PROFILE, '.mozilla', 'firefox')
    DESKTOP_PATH = os.path.join(USER_PROFILE, 'Desktop')
    
    # Also check XDG desktop location (but skip if running as sudo - it returns root's desktop)
    if not os.environ.get('SUDO_USER'):
        try:
            import subprocess
            result = subprocess.run(['xdg-user-dir', 'DESKTOP'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                DESKTOP_PATH = result.stdout.strip()
        except:
            pass

# Browser files/folders for the optional advanced cleanup.
# This list can include site data and may reset parts of web applications.
BROWSER_ADVANCED_CLEAN_LIST = [
    "Cache", "Code Cache", "GPUCache", "ShaderCache", "GrShaderCache",
    "Service Worker", "CacheStorage", "File System", "Local Storage",
    "Session Storage", "IndexedDB", "blob_storage", "databases",
    "Platform Notifications", "thumbnails", "Favicons", "Favicons-journal",
    "Shortcuts", "Network Action Predictor", "cache2", "startupCache", "OfflineCache"
]

# Safe mode only removes disposable browser cache folders. Cookies, history,
# login data, Local Storage and IndexedDB are intentionally excluded.
BROWSER_SAFE_CLEAN_LIST = [
    "Cache", "Code Cache", "GPUCache", "ShaderCache", "GrShaderCache",
    "Media Cache", "cache2", "startupCache", "OfflineCache"
]

def get_browser_clean_list(advanced=False):
    """Return the browser paths eligible for the selected cleanup mode."""
    return BROWSER_ADVANCED_CLEAN_LIST if advanced else BROWSER_SAFE_CLEAN_LIST

DESKTOP_RULES = {
    'Images': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.ico', '.tiff', '.tif', '.raw'],
    'Documents': ['.pdf', '.docx', '.doc', '.txt', '.xlsx', '.xls', '.pptx', '.ppt', '.odt', '.rtf', '.log', '.md', '.pub', '.mobi'],
    'Programs': ['.exe', '.msi', '.bat', '.ps1', '.cmd', '.vbs', '.reg'],
    'Shortcuts': ['.lnk', '.url'],
    'Archives': ['.zip', '.rar', '.7z', '.iso', '.tar', '.gz', '.bz2', '.xz'],
    'Code': ['.py', '.js', '.html', '.css', '.json', '.cpp', '.sql', '.java', '.cs', '.ts', '.jsx', '.tsx', '.xml', '.yaml', '.yml'],
    'Fonts': ['.ttf', '.otf', '.woff', '.woff2', '.eot'],
    'Videos': ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'],
    'Music': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.mid', '.midi'],
    'Design': ['.psd', '.ai', '.eps', '.svg', '.fig', '.xd', '.sketch'],
    'Database': ['.db', '.sqlite', '.sql', '.mdb', '.accdb'],
    '3D_CAD': ['.stl', '.obj', '.fbx', '.blend', '.dwg', '.dxf'],
    'Other': ['.rf', '.torrent', '.nfo', '.srt', '.sub']
}

# Linux: Override/extend rules for Linux-specific file types
if IS_LINUX:
    DESKTOP_RULES['Programs'] = ['.sh', '.AppImage', '.run', '.deb', '.rpm', '.snap', '.flatpakref']
    DESKTOP_RULES['Archives'].extend(['.tgz', '.tbz2', '.txz', '.deb', '.rpm'])
    DESKTOP_RULES['Code'].extend(['.conf', '.cfg', '.ini', '.service'])
    DESKTOP_RULES['Shortcuts'] = ['.desktop']  # Linux app shortcuts are .desktop files

# --- HELPER FUNCTIONS ---
def get_trash_paths():
    """Get all possible trash paths for Linux"""
    if not IS_LINUX:
        return []
    
    trash_paths = set()  # Use set to avoid duplicates
    
    # Standard XDG trash location
    xdg_data = os.environ.get('XDG_DATA_HOME', os.path.join(USER_PROFILE, '.local', 'share'))
    trash_paths.add(os.path.join(xdg_data, 'Trash'))
    
    # Also check common locations
    trash_paths.add(os.path.join(USER_PROFILE, '.local', 'share', 'Trash'))
    trash_paths.add(os.path.join(USER_PROFILE, '.Trash'))
    
    # Check mounted drives for .Trash-1000 folders
    uid = os.getuid() if hasattr(os, 'getuid') else 1000
    try:
        with open('/proc/mounts', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    mount_point = parts[1]
                    if mount_point.startswith('/media') or mount_point.startswith('/mnt'):
                        trash_paths.add(os.path.join(mount_point, f'.Trash-{uid}'))
    except:
        pass
    
    return list(trash_paths)

def get_trash_path():
    """Get the main trash path (for backward compatibility)"""
    paths = get_trash_paths()
    return paths[0] if paths else None

def recycle_bin_size():
    """Calculate total file size in Recycle Bin/Trash"""
    if IS_WINDOWS:
        try:
            from ctypes import windll, pointer, Structure, c_ulonglong, c_ulong
            
            class SHQUERYRBINFO(Structure):
                _fields_ = [
                    ("cbSize", c_ulong),
                    ("i64Size", c_ulonglong),
                    ("i64NumItems", c_ulonglong)
                ]
            
            info = SHQUERYRBINFO()
            info.cbSize = 24  # sizeof(SHQUERYRBINFO)
            
            # SHQueryRecycleBin - None for all drives
            result = windll.shell32.SHQueryRecycleBinW(None, pointer(info))
            
            if result == 0:  # S_OK
                return info.i64Size, info.i64NumItems
            return 0, 0
        except Exception:
            return 0, 0
    else:  # Linux
        total_size = 0
        total_items = 0
        
        for trash_path in get_trash_paths():
            try:
                files_path = os.path.join(trash_path, 'files')
                if not os.path.exists(files_path):
                    continue
                
                for item in os.listdir(files_path):
                    item_path = os.path.join(files_path, item)
                    total_items += 1
                    if os.path.isfile(item_path):
                        total_size += os.path.getsize(item_path)
                    elif os.path.isdir(item_path):
                        for root, dirs, files in os.walk(item_path):
                            for f in files:
                                try:
                                    total_size += os.path.getsize(os.path.join(root, f))
                                except:
                                    pass
            except Exception:
                continue
        
        return total_size, total_items

def empty_recycle_bin(log_func=None):
    """Empty Recycle Bin (Windows) or Trash (Linux)"""
    if IS_WINDOWS:
        try:
            # SHEmptyRecycleBin flags:
            # SHERB_NOCONFIRMATION = 0x00000001
            # SHERB_NOPROGRESSUI = 0x00000002  
            # SHERB_NOSOUND = 0x00000004
            flags = 0x00000001 | 0x00000002 | 0x00000004  # Silent, no confirmation, no progress
            
            result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
            
            if result == 0:  # S_OK
                return True
            elif result == -2147418113:  # S_FALSE (already empty)
                if log_func:
                    log_func("   ℹ️ Recycle Bin is already empty")
                return True
            return False
        except Exception as e:
            if log_func:
                log_func(f"   ⚠️ Could not empty Recycle Bin: {type(e).__name__}")
            return False
    else:  # Linux
        total_deleted = 0
        for trash_path in get_trash_paths():
            try:
                files_path = os.path.join(trash_path, 'files')
                info_path = os.path.join(trash_path, 'info')
                
                # Delete files in trash
                if os.path.exists(files_path):
                    for item in os.listdir(files_path):
                        item_path = os.path.join(files_path, item)
                        if safe_delete(item_path, log_func):
                            total_deleted += 1
                
                # Delete .trashinfo files
                if os.path.exists(info_path):
                    for item in os.listdir(info_path):
                        item_path = os.path.join(info_path, item)
                        safe_delete(item_path)
            except Exception:
                continue
        
        return total_deleted > 0

# --- WALLPAPER SETTINGS ---
WALLPAPER_CATEGORIES = {
    "🌄 Nature": "nature",
    "🏙️ City": "city",
    "🌌 Space": "space",
    "🌅 Landscape": "landscape",
    "🏔️ Mountain": "mountain",
    "🌊 Ocean": "ocean",
    "🌲 Forest": "forest",
    "🌃 Night": "night",
    "🌈 Minimal": "minimal",
    "🎨 Abstract": "abstract"
}

def download_wallpaper(category="nature", log_func=None):
    """
    Download category-based wallpaper from Unsplash API.
    """
    import random
    import time
    import base64
    
    # Default key (obfuscated) - user can override with UNSPLASH_KEY env variable
    _default = base64.b64decode("YTQyWUdXLWJJUmYtdG5wcEFIejVzbW55QUg0Y3YtbENybDlZSS1ZenlpTQ==").decode()
    _k = os.environ.get('UNSPLASH_KEY', _default)
    
    try:
        req = get_requests()
        
        # Get screen resolution
        width, height = get_screen_resolution()
        
        if log_func:
            log_func(f"   📷 Searching '{category}' for {width}x{height}...")
        
        # Unsplash API - random photo endpoint
        api_url = "https://api.unsplash.com/photos/random"
        
        headers = {
            'Authorization': f'Client-ID {_k}',
            'Accept': 'application/json',
        }
        
        # Determine orientation
        orientation = "landscape" if width > height else "portrait"
        
        params = {
            'query': category,
            'orientation': orientation,
        }
        
        # Get random photo info from API
        response = req.get(api_url, headers=headers, params=params, timeout=15)
        
        if response.status_code != 200:
            if log_func:
                log_func(f"   ⚠️ API error: {response.status_code}")
            return None
        
        data = response.json()
        
        # Get image in best size
        # Options: raw, full, regular, small, thumb
        # w parameter sets the size
        image_url = data.get('urls', {}).get('raw', '')
        if image_url:
            image_url = f"{image_url}&w={width}&h={height}&fit=crop&auto=format"
        else:
            image_url = data.get('urls', {}).get('full', '')
        
        if not image_url:
            if log_func:
                log_func("   ⚠️ Image URL not found")
            return None
        
        # Photographer info
        photographer = data.get('user', {}).get('name', 'Unknown')
        if log_func:
            log_func(f"   📸 Photographer: {photographer}")
        
        # Download image
        img_response = req.get(image_url, timeout=30, stream=True)
        
        if img_response.status_code != 200:
            if log_func:
                log_func("   ⚠️ Could not download image")
            return None
        
        # Save to temp file
        if IS_WINDOWS:
            wallpaper_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Neatify')
        else:
            wallpaper_dir = os.path.join(USER_PROFILE, '.local', 'share', 'neatify')
        os.makedirs(wallpaper_dir, exist_ok=True)
        
        wallpaper_path = os.path.join(wallpaper_dir, 'wallpaper.jpg')
        
        with open(wallpaper_path, 'wb') as f:
            for chunk in img_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size = os.path.getsize(wallpaper_path)
        if log_func:
            log_func(f"   ✅ Image downloaded ({file_size // 1024} KB)")
        
        return wallpaper_path
    
    except Exception as e:
        error_type = type(e).__name__
        if "Timeout" in error_type:
            if log_func:
                log_func("   ⚠️ Connection timeout")
        elif "Request" in error_type or "Connection" in error_type:
            if log_func:
                log_func(f"   ⚠️ Download error: {error_type}")
        else:
            if log_func:
                log_func(f"   ⚠️ Error: {error_type}")
        return None

def get_screen_resolution():
    """Get screen resolution (cross-platform)"""
    if IS_WINDOWS:
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    else:
        # Try xrandr on Linux
        try:
            import subprocess
            result = subprocess.run(['xrandr'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if ' connected' in line and 'primary' in line:
                    # Find resolution like "1920x1080+0+0"
                    parts = line.split()
                    for part in parts:
                        if 'x' in part and '+' in part:
                            res = part.split('+')[0]
                            w, h = res.split('x')
                            return int(w), int(h)
        except:
            pass
        return 1920, 1080  # Default fallback

def set_wallpaper(image_path, log_func=None):
    """
    Change desktop wallpaper (cross-platform).
    """
    if IS_WINDOWS:
        try:
            SPI_SETDESKWALLPAPER = 0x0014
            SPIF_UPDATEINIFILE = 0x01
            SPIF_SENDCHANGE = 0x02
            
            result = ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER, 
                0, 
                image_path, 
                SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
            )
            
            if result:
                if log_func:
                    log_func("   ✅ Wallpaper changed!")
                return True
            else:
                if log_func:
                    log_func("   ⚠️ Could not set wallpaper")
                return False
        except Exception as e:
            if log_func:
                log_func(f"   ⚠️ Error: {type(e).__name__}")
            return False
    else:  # Linux
        try:
            import subprocess
            
            # Detect desktop environment
            desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').upper()
            
            # Try XFCE first (xfconf-query)
            if 'XFCE' in desktop:
                try:
                    # Get current monitor property
                    result = subprocess.run(
                        ['xfconf-query', '-c', 'xfce4-desktop', '-l'],
                        capture_output=True, text=True
                    )
                    # Find backdrop image properties
                    for line in result.stdout.split('\n'):
                        if '/last-image' in line:
                            subprocess.run([
                                'xfconf-query', '-c', 'xfce4-desktop',
                                '-p', line.strip(), '-s', image_path
                            ], check=True, capture_output=True)
                    if log_func:
                        log_func("   ✅ Wallpaper changed!")
                    return True
                except Exception as e:
                    if log_func:
                        log_func(f"   ⚠️ XFCE error: {e}")
            
            # Try GNOME/gsettings
            try:
                subprocess.run([
                    'gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri',
                    f'file://{image_path}'
                ], check=True, capture_output=True)
                subprocess.run([
                    'gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri-dark',
                    f'file://{image_path}'
                ], capture_output=True)
                if log_func:
                    log_func("   ✅ Wallpaper changed!")
                return True
            except:
                pass
            
            # Try KDE/Plasma
            try:
                script = f'''
var allDesktops = desktops();
for (i=0;i<allDesktops.length;i++) {{
    d = allDesktops[i];
    d.wallpaperPlugin = "org.kde.image";
    d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");
    d.writeConfig("Image", "file://{image_path}")
}}
'''
                subprocess.run(['qdbus', 'org.kde.plasmashell', '/PlasmaShell',
                              'org.kde.PlasmaShell.evaluateScript', script],
                              check=True, capture_output=True)
                if log_func:
                    log_func("   ✅ Wallpaper changed!")
                return True
            except:
                pass
            
            # Try feh (lightweight WMs like i3, bspwm)
            try:
                subprocess.run(['feh', '--bg-fill', image_path], check=True, capture_output=True)
                if log_func:
                    log_func("   ✅ Wallpaper changed!")
                return True
            except:
                pass
            
            # Try nitrogen
            try:
                subprocess.run(['nitrogen', '--set-zoom-fill', image_path], check=True, capture_output=True)
                if log_func:
                    log_func("   ✅ Wallpaper changed!")
                return True
            except:
                pass
            
            # Try MATE
            try:
                subprocess.run([
                    'gsettings', 'set', 'org.mate.background', 'picture-filename', image_path
                ], check=True, capture_output=True)
                if log_func:
                    log_func("   ✅ Wallpaper changed!")
                return True
            except:
                pass
            
            # Try Cinnamon
            try:
                subprocess.run([
                    'gsettings', 'set', 'org.cinnamon.desktop.background', 'picture-uri',
                    f'file://{image_path}'
                ], check=True, capture_output=True)
                if log_func:
                    log_func("   ✅ Wallpaper changed!")
                return True
            except:
                pass
            
            if log_func:
                log_func("   ⚠️ Could not set wallpaper (unsupported DE)")
            return False
        except Exception as e:
            if log_func:
                log_func(f"   ⚠️ Error: {type(e).__name__}")
            return False

def format_size(byte_size):
    """Convert bytes to human readable format"""
    if byte_size < 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if byte_size < 1024:
            return f"{byte_size:.2f} {unit}"
        byte_size /= 1024
    return f"{byte_size:.2f} TB"

# Chromium browser files used by advanced cleanup.
CHROMIUM_ADVANCED_PROFILE_FILES = [
    "Favicons", "Favicons-journal",
    "Shortcuts", "Shortcuts-journal",
    "Network Action Predictor", "Network Action Predictor-journal"
]

# Chromium browser folders used by advanced cleanup. Some of these contain
# site data, so they are never removed by the default safe mode.
CHROMIUM_ADVANCED_PROFILE_DIRS = [
    "Cache", "Code Cache", "GPUCache", "ShaderCache", "GrShaderCache",
    "Service Worker", "CacheStorage", "File System",
    "Local Storage", "Session Storage", "IndexedDB",
    "blob_storage", "databases", "Platform Notifications"
]

# Disposable cache folders used by the default safe mode.
CHROMIUM_SAFE_PROFILE_DIRS = [
    "Cache", "Code Cache", "GPUCache", "ShaderCache", "GrShaderCache", "Media Cache"
]

def clean_chromium_profile(browser_path, log_func=None, advanced=False):
    """
    Clean Chromium-based browser profile folders.
    Scans all profiles: Default, Profile 1, Profile 2, etc.
    """
    deleted = 0
    freed_bytes = 0
    profile_files = CHROMIUM_ADVANCED_PROFILE_FILES if advanced else []
    profile_dirs = CHROMIUM_ADVANCED_PROFILE_DIRS if advanced else CHROMIUM_SAFE_PROFILE_DIRS
    if not os.path.exists(browser_path):
        return 0, 0
    
    # Find profile folders (Default, Profile 1, Profile 2...)
    profiles = []
    try:
        for item in os.listdir(browser_path):
            item_path = os.path.join(browser_path, item)
            if os.path.isdir(item_path):
                if item == "Default" or item.startswith("Profile "):
                    profiles.append(item_path)
    except Exception:
        pass
    
    for profile in profiles:
        # Delete files (exact match)
        for file_name in profile_files:
            file_path = os.path.join(profile, file_name)
            if os.path.exists(file_path):
                item_size = calculate_path_size(file_path)
                if safe_delete(file_path, log_func):
                    deleted += 1
                    freed_bytes += item_size
        
        # Delete folders
        for folder_name in profile_dirs:
            folder_path = os.path.join(profile, folder_name)
            if os.path.exists(folder_path):
                item_size = calculate_path_size(folder_path)
                if safe_delete(folder_path, log_func):
                    deleted += 1
                    freed_bytes += item_size
    
    # Also clean Cache folders in main directory
    main_cache_dirs = ["Cache", "GPUCache", "ShaderCache", "GrShaderCache", "Media Cache"]
    for folder_name in main_cache_dirs:
        folder_path = os.path.join(browser_path, folder_name)
        if os.path.exists(folder_path):
            item_size = calculate_path_size(folder_path)
            if safe_delete(folder_path, log_func):
                deleted += 1
                freed_bytes += item_size
    
    return deleted, freed_bytes

def safe_delete(path, log_func=None, max_attempts=3):
    """Safely delete a file or folder. Retries for locked files."""
    import time
    
    for attempt in range(max_attempts):
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.chmod(path, stat.S_IWRITE)
                os.remove(path)
                return True
            elif os.path.isdir(path):
                shutil.rmtree(path, onerror=lambda func, p, _: (os.chmod(p, stat.S_IWRITE), func(p)))
                return True
        except PermissionError:
            if attempt < max_attempts - 1:
                time.sleep(0.5)  # Wait for locked file
                continue
            if log_func:
                log_func(f"⚠️ Access denied: {os.path.basename(path)}")
        except Exception as e:
            if log_func:
                log_func(f"⚠️ Could not delete: {os.path.basename(path)} - {type(e).__name__}")
            break
    return False

def calculate_folder_size(path, filter_list=None):
    """Calculate folder size, with optional filter"""
    total = 0
    if not path or not os.path.exists(path):
        return 0
    filter_names = {item.casefold() for item in filter_list} if filter_list else None
    try:
        for root, _, files in os.walk(path):
            root_names = {part.casefold() for part in pathlib.Path(root).parts}
            for f in files:
                if filter_list:
                    # Match complete folder/file names so safe-mode estimates
                    # do not accidentally include folders such as CacheStorage.
                    if root_names.intersection(filter_names) or f.casefold() in filter_names:
                        try:
                            total += os.path.getsize(os.path.join(root, f))
                        except (OSError, PermissionError):
                            continue
                else:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except (OSError, PermissionError):
                        continue
    except (OSError, PermissionError):
        pass
    return total

def calculate_path_size(path):
    """Return the current size of one file or directory before it is removed."""
    if not path or not os.path.exists(path):
        return 0
    try:
        if os.path.isfile(path) or os.path.islink(path):
            return os.path.getsize(path)
    except (OSError, PermissionError):
        return 0
    return calculate_folder_size(path)

def get_desktop_organization_plan(desktop_path):
    """Build a previewable plan for files directly on the desktop."""
    plan = []
    if not desktop_path or not os.path.isdir(desktop_path):
        return plan

    try:
        for file_name in os.listdir(desktop_path):
            source_path = os.path.join(desktop_path, file_name)
            if not os.path.isfile(source_path):
                continue

            extension = pathlib.Path(file_name).suffix.lower()
            target_folder = next(
                (
                    folder
                    for folder, extensions in DESKTOP_RULES.items()
                    if extension in extensions
                ),
                None,
            )
            if not target_folder:
                continue

            target_dir = os.path.join(desktop_path, target_folder)
            target_path = os.path.join(target_dir, file_name)
            plan.append({
                "name": file_name,
                "source": source_path,
                "target_dir": target_dir,
                "target": target_path,
                "folder": target_folder,
                "conflict": os.path.exists(target_path),
                "selected": True,
            })
    except (OSError, PermissionError):
        pass

    return plan

def get_unique_path(path):
    """Return a non-existing path by adding a numbered suffix."""
    if not os.path.exists(path):
        return path

    path_obj = pathlib.Path(path)
    counter = 1
    while True:
        candidate = path_obj.with_name(
            f"{path_obj.stem} ({counter}){path_obj.suffix}"
        )
        if not candidate.exists():
            return str(candidate)
        counter += 1


# --- GUI CLASS ---
class AssistantGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1100x760")
        self.minsize(1000, 650)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Set icon
        self._set_icon()
        
        # Operation state
        self.operation_in_progress = False
        self.scan_results = {}
        self.scan_selection = None
        self.last_scan_completed = False
        self.cleanup_details = []
        self.cleanup_selection = {}
        self.desktop_plan = []
        self.last_desktop_moves = []
        self.rename_desktop_conflicts = False
        self.delete_empty_desktop_folders = False
        
        # Grid settings
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Header Area
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, columnspan=2, pady=(15, 5), sticky="ew")
        
        brand_row = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        brand_row.pack()
        self.brand_logo = None
        logo_path = resource_path("neatify-logo.png")
        if Image is not None and os.path.exists(logo_path):
            try:
                logo_image = Image.open(logo_path)
                self.brand_logo = ctk.CTkImage(
                    light_image=logo_image,
                    dark_image=logo_image,
                    size=(48, 48),
                )
                ctk.CTkLabel(brand_row, text="", image=self.brand_logo).pack(
                    side="left", padx=(0, 10)
                )
            except Exception:
                self.brand_logo = None
        self.title_label = ctk.CTkLabel(
            brand_row,
            text="Neatify",
            font=("Segoe UI", 36, "bold"),
            text_color="#3498db"
        )
        self.title_label.pack(side="left")
        
        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="Cleaning Tool",
            font=("Segoe UI", 14),
            text_color="gray"
        )
        self.subtitle_label.pack()

        # Admin warning
        if not is_admin():
            admin_text = "⚠️ Run as Administrator for full cleaning" if IS_WINDOWS else "⚠️ Run as root for full cleaning"
            self.admin_label = ctk.CTkLabel(
                self.header_frame, 
                text=admin_text,
                font=("Segoe UI", 13, "bold"),
                text_color="#f39c12"
            )
            self.admin_label.pack(pady=(5, 0))

        # Options Panel
        self.options_frame = ctk.CTkFrame(
            self,
            corner_radius=15,
            border_width=2,
            border_color="#2c3e50"
        )
        self.options_frame.grid(row=1, column=0, columnspan=2, padx=30, pady=10, sticky="ew")
        self.options_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        cb_font = ("Segoe UI", 14, "bold")

        self.var_system = ctk.BooleanVar(value=True)
        self.cb_system = ctk.CTkCheckBox(
            self.options_frame, 
            text="🗂️ System", 
            variable=self.var_system,
            font=cb_font,
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        self.cb_system.grid(row=0, column=0, padx=15, pady=20)

        self.var_browser = ctk.BooleanVar(value=True)
        self.cb_browser = ctk.CTkCheckBox(
            self.options_frame, 
            text="🌐 Browsers", 
            variable=self.var_browser,
            font=cb_font,
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        self.cb_browser.grid(row=0, column=1, padx=15, pady=20)

        self.var_desktop = ctk.BooleanVar(value=False)
        self.cb_desktop = ctk.CTkCheckBox(
            self.options_frame, 
            text="🖥️ Desktop", 
            variable=self.var_desktop,
            font=cb_font,
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        self.cb_desktop.grid(row=0, column=2, padx=15, pady=20)

        self.var_recycle_bin = ctk.BooleanVar(value=True)
        trash_label = "🗑️ Recycle Bin" if IS_WINDOWS else "🗑️ Trash"
        self.cb_recycle_bin = ctk.CTkCheckBox(
            self.options_frame, 
            text=trash_label, 
            variable=self.var_recycle_bin,
            font=cb_font,
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        self.cb_recycle_bin.grid(row=0, column=3, padx=15, pady=20)

        self.var_advanced_browser = ctk.BooleanVar(value=False)
        self.cb_advanced_browser = ctk.CTkCheckBox(
            self.options_frame,
            text="⚠️ Advanced browser cleanup (site data may be removed)",
            variable=self.var_advanced_browser,
            font=("Segoe UI", 11),
            text_color="#f39c12",
            fg_color="#f39c12",
            hover_color="#d68910"
        )
        self.cb_advanced_browser.grid(
            row=1, column=0, columnspan=4, padx=15, pady=(0, 12), sticky="w"
        )

        # Scan summary cards
        self.summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.summary_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=(4, 0), sticky="ew")
        self.summary_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.summary_values = {}
        summary_cards = [
            ("system", "🗂️ System", "#3498db"),
            ("browser", "🌐 Browser", "#9b59b6"),
            ("desktop", "🖥️ Desktop", "#f39c12"),
            ("recycle_bin", trash_label, "#e74c3c"),
        ]
        for column, (key, title, color) in enumerate(summary_cards):
            card = ctk.CTkFrame(
                self.summary_frame,
                corner_radius=12,
                border_width=1,
                border_color="#2c3e50"
            )
            card.grid(row=0, column=column, padx=5, sticky="ew")
            ctk.CTkLabel(
                card, text=title, font=("Segoe UI", 11, "bold"), text_color=color
            ).pack(pady=(8, 0))
            value_label = ctk.CTkLabel(
                card, text="—", font=("Segoe UI", 14, "bold")
            )
            value_label.pack(pady=(2, 8))
            self.summary_values[key] = value_label

        # Cleanup details panel
        self.details_frame = ctk.CTkFrame(
            self,
            corner_radius=12,
            border_width=1,
            border_color="#2c3e50",
        )
        self.details_frame.grid(row=3, column=0, padx=(20, 8), pady=(10, 0), sticky="nsew")
        self.details_frame.grid_columnconfigure(0, weight=1)
        self.details_frame.grid_rowconfigure(1, weight=1)

        details_header = ctk.CTkFrame(self.details_frame, fg_color="transparent")
        details_header.grid(row=0, column=0, padx=12, pady=(8, 0), sticky="ew")
        details_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            details_header,
            text="Cleanup Details",
            font=("Segoe UI", 14, "bold"),
            text_color="#3498db",
        ).grid(row=0, column=0, sticky="w")
        self.details_status_label = ctk.CTkLabel(
            details_header,
            text="Run Analyze to choose individual cleanup targets.",
            font=("Segoe UI", 11),
            text_color="gray",
        )
        self.details_status_label.grid(row=1, column=0, sticky="w", pady=(0, 4))

        details_actions = ctk.CTkFrame(details_header, fg_color="transparent")
        details_actions.grid(row=0, column=1, rowspan=2, sticky="e")
        self.details_select_all_btn = ctk.CTkButton(
            details_actions,
            text="Select All",
            command=lambda: self._set_all_detail_selections(True),
            width=92,
            height=28,
            font=("Segoe UI", 11),
            fg_color="#34495e",
            hover_color="#2c3e50",
        )
        self.details_select_all_btn.pack(side="left", padx=3)
        self.details_clear_all_btn = ctk.CTkButton(
            details_actions,
            text="Clear All",
            command=lambda: self._set_all_detail_selections(False),
            width=92,
            height=28,
            font=("Segoe UI", 11),
            fg_color="#34495e",
            hover_color="#2c3e50",
        )
        self.details_clear_all_btn.pack(side="left", padx=3)

        self.details_panel = ctk.CTkScrollableFrame(
            self.details_frame,
            height=220,
            corner_radius=8,
        )
        self.details_panel.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.details_vars = {}
        self.details_checks = {}
        self._show_details_placeholder()

        # Activity Log
        self.log_frame = ctk.CTkFrame(
            self,
            corner_radius=12,
            border_width=1,
            border_color="#2c3e50",
        )
        self.log_frame.grid(row=3, column=1, padx=(8, 20), pady=(10, 0), sticky="nsew")
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            self.log_frame,
            text="Activity Log",
            font=("Segoe UI", 14, "bold"),
            text_color="#2ecc71",
        ).grid(row=0, column=0, padx=12, pady=(8, 4), sticky="w")

        self.log_box = ctk.CTkTextbox(
            self.log_frame,
            font=("Consolas", 12),
            corner_radius=10
        )
        self.log_box.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.log_box.insert("0.0", "🎉 Welcome!\n\nClick '🔍 Analyze' to scan your system.\n")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            self, 
            mode="indeterminate",
            height=12,
            corner_radius=6,
            progress_color="#3498db",
            fg_color="#2c3e50"
        )
        self.progress_bar.grid(row=4, column=0, columnspan=2, padx=30, pady=(0, 15), sticky="ew")
        self.progress_bar.set(0)

        # Buttons
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=5, column=0, columnspan=2, pady=(0, 20))

        self.btn_analyze = ctk.CTkButton(
            self.btn_frame, 
            text="🔍 Analyze", 
            command=self.start_analysis,
            font=("Segoe UI", 14, "bold"),
            width=150,
            height=40
        )
        self.btn_analyze.grid(row=0, column=0, padx=10)

        self.btn_clean = ctk.CTkButton(
            self.btn_frame, 
            text="🧹 Start Cleaning", 
            fg_color="#2ecc71", 
            hover_color="#27ae60", 
            command=self.start_cleaning,
            font=("Segoe UI", 14, "bold"),
            width=180,
            height=40
        )
        self.btn_clean.grid(row=0, column=1, padx=10)

        self.btn_wallpaper = ctk.CTkButton(
            self.btn_frame, 
            text="🖼️ Wallpaper", 
            fg_color="#9b59b6", 
            hover_color="#8e44ad", 
            command=self.wallpaper_dialog,
            font=("Segoe UI", 14, "bold"),
            width=150,
            height=40
        )
        self.btn_wallpaper.grid(row=0, column=2, padx=10)

        self.btn_undo = ctk.CTkButton(
            self.btn_frame,
            text="↩ Undo Organization",
            fg_color="#34495e",
            hover_color="#2c3e50",
            command=self.undo_last_desktop_organization,
            font=("Segoe UI", 13, "bold"),
            width=180,
            height=40,
            state="disabled",
        )
        self.btn_undo.grid(row=0, column=3, padx=10)

        self.btn_about = ctk.CTkButton(
            self.btn_frame,
            text="ℹ About",
            fg_color="#2c3e50",
            hover_color="#1f2d3a",
            command=self.about_dialog,
            font=("Segoe UI", 13, "bold"),
            width=120,
            height=40,
        )
        self.btn_about.grid(row=0, column=4, padx=10)

        # Window close event
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _set_icon(self):
        """Set application icon"""
        try:
            icon_path = resource_path("neatify.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass  # Use default icon if not found

    def about_dialog(self):
        """Show application version and project information."""
        if self.operation_in_progress:
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"About {APP_NAME}")
        dialog.geometry("500x430")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Ⓝ Neatify",
            font=("Segoe UI", 32, "bold"),
            text_color="#3498db",
        ).pack(pady=(28, 4))
        ctk.CTkLabel(
            dialog,
            text=f"Version {APP_VERSION}",
            font=("Segoe UI", 15, "bold"),
            text_color="#2ecc71",
        ).pack(pady=(0, 18))
        ctk.CTkLabel(
            dialog,
            text="A cross-platform PC cleanup and desktop organizer.",
            font=("Segoe UI", 13),
            text_color="gray",
        ).pack(pady=4)
        ctk.CTkLabel(
            dialog,
            text="Safe cleanup · Browser cache management · Desktop organization",
            font=("Segoe UI", 11),
            wraplength=420,
            justify="center",
        ).pack(pady=(4, 20))
        ctk.CTkLabel(
            dialog,
            text="Source code and releases",
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=(0, 6))
        ctk.CTkLabel(
            dialog,
            text=REPOSITORY_URL,
            font=("Segoe UI", 11),
            text_color="#3498db",
        ).pack(pady=(0, 10))

        def open_repository():
            import webbrowser
            webbrowser.open(REPOSITORY_URL)

        ctk.CTkButton(
            dialog,
            text="Open GitHub Repository",
            command=open_repository,
            width=220,
            height=38,
            fg_color="#34495e",
            hover_color="#2c3e50",
        ).pack(pady=4)
        ctk.CTkLabel(
            dialog,
            text="MIT License · © 2026 Neatify",
            font=("Segoe UI", 10),
            text_color="gray",
        ).pack(pady=(22, 0))
        ctk.CTkButton(
            dialog,
            text="Close",
            command=dialog.destroy,
            width=100,
            height=34,
        ).pack(pady=(10, 18))

    def log(self, message, color=None):
        """Thread-safe logging"""
        self.after(0, self._write_log, message, color)

    def _write_log(self, message, color=None):
        """Write log in main thread"""
        if color:
            self.log_box.tag_config(color, foreground=color)
            self.log_box.insert("end", f"\n{message}", color)
        else:
            self.log_box.insert("end", f"\n{message}")
        self.log_box.see("end")

    def _show_details_placeholder(self):
        """Show the initial state of the embedded cleanup details panel."""
        for child in self.details_panel.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self.details_panel,
            text="No analysis results yet.",
            font=("Segoe UI", 12),
            text_color="gray",
        ).pack(anchor="w", padx=10, pady=8)
        self.details_status_label.configure(
            text="Run Analyze to choose individual cleanup targets."
        )

    def _populate_cleanup_details(self):
        """Render analyzed cleanup targets inside the main window."""
        for child in self.details_panel.winfo_children():
            child.destroy()
        self.details_vars = {}
        self.details_checks = {}

        if not self.cleanup_details:
            self._show_details_placeholder()
            return

        grouped_details = {}
        for detail in self.cleanup_details:
            grouped_details.setdefault(detail["group"], []).append(detail)

        for group, details in grouped_details.items():
            ctk.CTkLabel(
                self.details_panel,
                text=group,
                font=("Segoe UI", 12, "bold"),
                text_color="#f39c12",
            ).pack(anchor="w", padx=8, pady=(5, 2))

            for detail in details:
                key = detail["key"]
                detail_var = ctk.BooleanVar(
                    value=self.cleanup_selection.get(key, True)
                )
                self.details_vars[key] = detail_var
                count_text = (
                    f" · {detail['count']} item(s)"
                    if "count" in detail else ""
                )
                check = ctk.CTkCheckBox(
                    self.details_panel,
                    text=f"{detail['label']} — {format_size(detail['size'])}{count_text}",
                    variable=detail_var,
                    command=lambda detail_key=key: self._sync_detail_selection(detail_key),
                    font=("Segoe UI", 12),
                    fg_color="#3498db",
                    hover_color="#2980b9",
                )
                check.pack(anchor="w", padx=18, pady=3)
                self.details_checks[key] = check

        self._update_details_status()

    def _sync_detail_selection(self, key):
        """Persist a checkbox change from the embedded details panel."""
        if key in self.details_vars:
            self.cleanup_selection[key] = bool(self.details_vars[key].get())
            self._update_details_status()

    def _set_all_detail_selections(self, value):
        """Select or clear all analyzed cleanup targets."""
        for key, detail_var in self.details_vars.items():
            detail_var.set(value)
            self.cleanup_selection[key] = value
        self._update_details_status()

    def _update_details_status(self):
        selected_count = sum(
            1 for detail in self.cleanup_details
            if self.cleanup_selection.get(detail["key"], True)
        )
        selected_size = self._selected_estimate()
        self.details_status_label.configure(
            text=f"{selected_count} target(s) selected · {format_size(selected_size)}"
        )

    def set_buttons_state(self, enabled):
        """Enable/disable buttons"""
        state = "normal" if enabled else "disabled"
        self.btn_analyze.configure(state=state)
        self.btn_clean.configure(state=state)
        self.cb_system.configure(state=state)
        self.cb_browser.configure(state=state)
        self.cb_desktop.configure(state=state)
        self.cb_recycle_bin.configure(state=state)
        self.cb_advanced_browser.configure(state=state)
        self.btn_wallpaper.configure(state=state)
        self.btn_undo.configure(
            state="normal" if enabled and self.last_desktop_moves else "disabled"
        )
        self.btn_about.configure(state=state)
        detail_state = state if self.cleanup_details else "disabled"
        self.details_select_all_btn.configure(state=detail_state)
        self.details_clear_all_btn.configure(state=detail_state)
        for check in self.details_checks.values():
            check.configure(state=detail_state)
        
        if enabled:
            self.progress_bar.stop()
            self.progress_bar.set(0)
        else:
            self.progress_bar.start()

    def _selection_state(self):
        """Return the options used by the most recent scan."""
        return (
            bool(self.var_system.get()),
            bool(self.var_browser.get()),
            bool(self.var_desktop.get()),
            bool(self.var_recycle_bin.get()),
            bool(self.var_advanced_browser.get()),
        )

    def _selected_estimate(self):
        """Return the estimated bytes for the selected categories."""
        return sum(
            detail.get("size", 0)
            for detail in self.cleanup_details
            if self.cleanup_selection.get(detail["key"], True)
        )

    def _selected_desktop_items(self):
        """Return desktop files selected in the desktop preview."""
        return [item for item in self.desktop_plan if item.get("selected", True)]

    def _selected_cleanup_labels(self):
        """Build grouped labels for the cleanup confirmation dialog."""
        groups = {}
        for detail in self.cleanup_details:
            if self.cleanup_selection.get(detail["key"], True):
                groups.setdefault(detail["group"], []).append(detail["label"])

        labels = [
            f"{group}: {', '.join(items)}"
            for group, items in groups.items()
        ]
        if self.var_desktop.get() and self._selected_desktop_items():
            labels.append(
                f"Desktop organization ({len(self._selected_desktop_items())} file(s))"
            )
        return labels

    def _update_summary(self, results):
        """Update the compact scan summary shown above the details log."""
        self.summary_values["system"].configure(
            text=format_size(results.get("system", 0))
        )
        self.summary_values["browser"].configure(
            text=format_size(results.get("browser", 0))
        )
        self.summary_values["desktop"].configure(
            text=f"{results.get('desktop', 0)} files"
        )
        self.summary_values["recycle_bin"].configure(
            text=format_size(results.get("recycle_bin", 0))
        )
        self.subtitle_label.configure(
            text=f"Last scan: {format_size(results.get('total', 0))} cleanable space · Choose categories above before cleaning"
        )
        self._populate_cleanup_details()

    def _invalidate_scan(self, freed_bytes=None):
        """Mark the summary stale after a cleanup changes the filesystem."""
        self.last_scan_completed = False
        self.scan_results = {}
        self.cleanup_details = []
        self.cleanup_selection = {}
        self.details_vars = {}
        self.details_checks = {}
        for value_label in self.summary_values.values():
            value_label.configure(text="—")
        self._show_details_placeholder()
        if freed_bytes is None:
            self.subtitle_label.configure(text="Cleanup completed · Run a new analysis for current results")
        else:
            self.subtitle_label.configure(
                text=f"Cleanup completed · {format_size(freed_bytes)} freed · Run a new analysis for current results"
            )

    def _finish_cleanup(self, freed_bytes):
        """Show the measured cleanup result after the worker has finished."""
        self._invalidate_scan(freed_bytes)
        messagebox.showinfo(
            "Cleanup complete",
            f"Cleanup completed successfully.\n\nSpace freed: {format_size(freed_bytes)}",
        )

    def start_analysis(self):
        """Start analysis operation"""
        if self.operation_in_progress:
            return
        self.last_scan_completed = False
        self.scan_results = {}
        self.cleanup_details = []
        self.cleanup_selection = {}
        self.desktop_plan = []
        self.rename_desktop_conflicts = False
        self.delete_empty_desktop_folders = False
        self.scan_selection = self._selection_state()
        self.operation_in_progress = True
        self.set_buttons_state(False)
        threading.Thread(target=self.analysis_logic, daemon=True).start()

    def analysis_logic(self):
        """Analysis operation logic"""
        try:
            self.after(0, lambda: self.log_box.delete("0.0", "end"))
            self.log("🔍 Starting analysis...\n", "#3498db")
            
            results = {
                "system": 0,
                "browser": 0,
                "desktop": 0,
                "recycle_bin": 0,
                "total": 0,
            }
            cleanup_details = []
            browser_clean_list = get_browser_clean_list(self.var_advanced_browser.get())
            # System
            if self.var_system.get():
                self.log("\n─── 📁 SCANNING SYSTEM FOLDERS ───", "#f39c12")
                s_size = 0
                for name, path in TARGET_DIRS.items():
                    if os.path.exists(path):
                        size = calculate_folder_size(path)
                        s_size += size
                        cleanup_details.append({
                            "key": f"system:{name}",
                            "group": "System",
                            "label": name,
                            "size": size,
                            "path": path,
                        })
                        self.log(f"   • {name}: {format_size(size)}")
                self.log(f"   ➜ System Total: {format_size(s_size)}\n")
                results["system"] = s_size
            
            # Browser
            if self.var_browser.get():
                self.log("\n─── 🌐 SCANNING BROWSERS ───", "#f39c12")
                b_size = 0
                for name, path in BROWSER_PATHS.items():
                    if os.path.exists(path):
                        size = calculate_folder_size(path, browser_clean_list)
                        cleanup_details.append({
                            "key": f"browser:{name}",
                            "group": "Browsers",
                            "label": name,
                            "size": size,
                            "path": path,
                        })
                        if size > 0:
                            b_size += size
                            self.log(f"   • {name}: {format_size(size)}")
                
                if os.path.exists(FIREFOX_PATH):
                    ff_size = calculate_folder_size(FIREFOX_PATH, browser_clean_list)
                    cleanup_details.append({
                        "key": "browser:Firefox",
                        "group": "Browsers",
                        "label": "Firefox",
                        "size": ff_size,
                        "path": FIREFOX_PATH,
                    })
                    if ff_size > 0:
                        b_size += ff_size
                        self.log(f"   • Firefox: {format_size(ff_size)}")
                
                self.log(f"   ➜ Browser Total: {format_size(b_size)}\n")
                results["browser"] = b_size
            
            # Desktop analysis
            if self.var_desktop.get():
                self.log("\n─── 🖥️ SCANNING DESKTOP ───", "#f39c12")
                d_path = DESKTOP_PATH
                self.log(f"   • Desktop path: {d_path}")
                if os.path.exists(d_path):
                    desktop_plan = get_desktop_organization_plan(d_path)
                    self.desktop_plan = desktop_plan
                    shortcut_exts = set(DESKTOP_RULES.get("Shortcuts", []))
                    shortcut_count = sum(
                        1 for item in desktop_plan
                        if pathlib.Path(item["name"]).suffix.lower() in shortcut_exts
                    )
                    other_file_count = len(desktop_plan) - shortcut_count
                    empty_folder_count = len([d for d in os.listdir(d_path) 
                                             if os.path.isdir(os.path.join(d_path, d)) 
                                             and not os.listdir(os.path.join(d_path, d))])
                    if shortcut_count > 0:
                        self.log(f"   • Shortcuts to organize: {shortcut_count}")
                    if other_file_count > 0:
                        self.log(f"   • Other files to organize: {other_file_count}")
                    if empty_folder_count > 0:
                        self.log(f"   • Empty folders to delete: {empty_folder_count}")
                    conflict_count = sum(1 for item in desktop_plan if item["conflict"])
                    if conflict_count > 0:
                        self.log(f"   • Conflicts to review: {conflict_count}")
                    results["desktop"] = len(desktop_plan)
                    self.log("")
                else:
                    self.desktop_plan = []
            
            # Recycle Bin / Trash analysis
            if self.var_recycle_bin.get():
                trash_name = "Recycle Bin" if IS_WINDOWS else "Trash"
                self.log(f"\n─── 🗑️ SCANNING {trash_name.upper()} ───", "#f39c12")
                bin_size, bin_count = recycle_bin_size()
                cleanup_details.append({
                    "key": "recycle_bin",
                    "group": "Recycle Bin" if IS_WINDOWS else "Trash",
                    "label": "Recycle Bin" if IS_WINDOWS else "Trash",
                    "size": bin_size,
                    "count": int(bin_count),
                })
                if bin_count > 0:
                    self.log(f"   • {int(bin_count)} items, {format_size(bin_size)}")
                    results["recycle_bin"] = bin_size
                else:
                    self.log(f"   • {trash_name} is empty")
                self.log("")
            
            self.log("=" * 45, "#2ecc71")
            results["total"] = (
                results["system"] + results["browser"] + results["recycle_bin"]
            )
            self.cleanup_details = cleanup_details
            self.cleanup_selection = {
                detail["key"]: True for detail in cleanup_details
            }
            self.scan_results = results
            self.last_scan_completed = True
            self.after(0, self._update_summary, results)
            self.log(f"📊 TOTAL CLEANABLE: {format_size(results['total'])}", "#2ecc71")
            self.log("=" * 45, "#2ecc71")
            
        except Exception as e:
            self.log(f"❌ Error occurred: {e}", "#e74c3c")
        finally:
            self.operation_in_progress = False
            self.after(0, lambda: self.set_buttons_state(True))

    def start_cleaning(self, show_desktop_preview=True):
        """Start cleaning operation"""
        if self.operation_in_progress:
            return

        if not self.last_scan_completed:
            messagebox.showwarning(
                "New analysis required",
                "Run a fresh analysis before cleanup."
            )
            return

        if self.scan_selection != self._selection_state():
            messagebox.showwarning(
                "Cleanup selection changed",
                "The cleanup selection changed after the last analysis.\n"
                "Run a new analysis to refresh the results."
            )
            return
        
        if show_desktop_preview and self.var_desktop.get() and self.desktop_plan:
            self.desktop_preview_dialog()
            return

        # Get confirmation from the selected detail rows.
        selections = self._selected_cleanup_labels()
        if not selections:
            messagebox.showwarning("Warning", "Please select at least one cleanup category.")
            return
        
        estimated = self._selected_estimate()
        advanced_warning = "\n\n⚠️ Advanced browser cleanup is enabled: some site data may be removed." if self.var_advanced_browser.get() else ""
        confirm = messagebox.askyesno(
            "Cleanup preview",
            "Based on the latest analysis, these operations will be performed:\n\n• "
            + "\n• ".join(selections)
            + f"\n\nEstimated space: {format_size(estimated)}"
            + advanced_warning
            + "\n\nDo you want to continue?"
        )
        
        if not confirm:
            return
        
        self.operation_in_progress = True
        self.set_buttons_state(False)
        threading.Thread(target=self.cleaning_logic, daemon=True).start()

    def desktop_preview_dialog(self):
        """Show the desktop move plan before any files are changed."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Desktop Organization Preview")
        dialog.geometry("760x600")
        dialog.minsize(650, 500)
        dialog.resizable(True, True)
        dialog.transient(self)
        dialog.grab_set()

        header = ctk.CTkFrame(dialog, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(
            header,
            text="🖥️ Desktop Organization Preview",
            font=("Segoe UI", 23, "bold"),
            text_color="#f39c12",
        ).pack(anchor="w")

        conflict_count = sum(1 for item in self.desktop_plan if item["conflict"])
        summary_text = f"{len(self.desktop_plan)} file(s) can be organized."
        if conflict_count:
            summary_text += f" {conflict_count} conflict(s) found."
        summary_label = ctk.CTkLabel(
            header,
            text=summary_text,
            font=("Segoe UI", 13),
            text_color="gray",
        )
        summary_label.pack(anchor="w", pady=(3, 0))

        # Keep category filters separate from item selection. This lets users
        # narrow the list (for example to Shortcuts or Music) and then select
        # every currently visible file in one action.
        desktop_vars = {
            index: ctk.BooleanVar(value=item.get("selected", True))
            for index, item in enumerate(self.desktop_plan)
        }
        folders = list(dict.fromkeys(item["folder"] for item in self.desktop_plan))
        filter_vars = {folder: ctk.BooleanVar(value=True) for folder in folders}

        filters_frame = ctk.CTkFrame(
            dialog,
            corner_radius=10,
            border_width=1,
            border_color="#2c3e50",
        )
        filters_frame.pack(fill="x", padx=24, pady=(0, 8))
        filters_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            filters_frame,
            text="Filter desktop items by category",
            font=("Segoe UI", 12, "bold"),
            text_color="#3498db",
        ).grid(row=0, column=0, padx=12, pady=(8, 2), sticky="w")

        filter_actions = ctk.CTkFrame(filters_frame, fg_color="transparent")
        filter_actions.grid(row=0, column=1, padx=8, pady=(6, 0), sticky="e")

        categories_frame = ctk.CTkFrame(filters_frame, fg_color="transparent")
        categories_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 8), sticky="ew")
        for column in range(3):
            categories_frame.grid_columnconfigure(column, weight=1)

        list_frame = ctk.CTkScrollableFrame(
            dialog,
            corner_radius=12,
            border_width=1,
            border_color="#2c3e50",
        )
        list_frame.pack(fill="both", expand=True, padx=24, pady=12)
        list_frame.grid_columnconfigure(0, weight=3)
        list_frame.grid_columnconfigure(1, weight=2)
        list_frame.grid_columnconfigure(2, weight=2)

        def visible_indexes():
            return [
                index for index, item in enumerate(self.desktop_plan)
                if filter_vars[item["folder"]].get()
            ]

        def render_list():
            for child in list_frame.winfo_children():
                child.destroy()
            indexes = visible_indexes()
            selected_count = sum(1 for index in indexes if desktop_vars[index].get())
            summary_label.configure(
                text=(
                    f"{len(indexes)} item(s) shown · {selected_count} selected. "
                    "Use Select Filtered to select every visible item."
                )
            )
            if not indexes:
                ctk.CTkLabel(
                    list_frame,
                    text="No desktop items match the selected filters.",
                    font=("Segoe UI", 12),
                    text_color="gray",
                ).grid(row=0, column=0, columnspan=3, padx=10, pady=12, sticky="w")
                return
            for row, index in enumerate(indexes):
                item = self.desktop_plan[index]
                status = "Conflict — will be skipped" if item["conflict"] else "Ready"
                status_color = "#e74c3c" if item["conflict"] else "#2ecc71"
                ctk.CTkCheckBox(
                    list_frame,
                    text=item["name"],
                    variable=desktop_vars[index],
                    command=render_list,
                    font=("Segoe UI", 12),
                    fg_color="#3498db",
                    hover_color="#2980b9",
                ).grid(row=row, column=0, padx=10, pady=6, sticky="ew")
                ctk.CTkLabel(
                    list_frame,
                    text=f"→ {item['folder']}/",
                    anchor="w",
                    font=("Segoe UI", 12),
                    text_color="#3498db",
                ).grid(row=row, column=1, padx=10, pady=6, sticky="ew")
                ctk.CTkLabel(
                    list_frame,
                    text=status,
                    anchor="w",
                    font=("Segoe UI", 11),
                    text_color=status_color,
                ).grid(row=row, column=2, padx=10, pady=6, sticky="ew")

        def set_filters(value):
            for filter_var in filter_vars.values():
                filter_var.set(value)
            render_list()

        def set_visible_selections(value):
            for index in visible_indexes():
                desktop_vars[index].set(value)
            render_list()

        ctk.CTkButton(
            filter_actions,
            text="All Categories",
            command=lambda: set_filters(True),
            width=95,
            height=26,
            font=("Segoe UI", 11),
            fg_color="#34495e",
            hover_color="#2c3e50",
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            filter_actions,
            text="Clear Filters",
            command=lambda: set_filters(False),
            width=90,
            height=26,
            font=("Segoe UI", 11),
            fg_color="#34495e",
            hover_color="#2c3e50",
        ).pack(side="left", padx=2)
        for index, folder in enumerate(folders):
            ctk.CTkCheckBox(
                categories_frame,
                text=folder,
                variable=filter_vars[folder],
                command=render_list,
                font=("Segoe UI", 11),
                fg_color="#3498db",
                hover_color="#2980b9",
            ).grid(row=index // 3, column=index % 3, padx=5, pady=2, sticky="w")

        render_list()

        options = ctk.CTkFrame(dialog, fg_color="transparent")
        options.pack(fill="x", padx=24, pady=(0, 8))
        rename_var = ctk.BooleanVar(value=False)
        delete_empty_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            options,
            text="Rename conflicting files automatically",
            variable=rename_var,
            font=("Segoe UI", 12),
            fg_color="#3498db",
            hover_color="#2980b9",
        ).pack(anchor="w", pady=3)
        ctk.CTkCheckBox(
            options,
            text="Delete empty desktop folders",
            variable=delete_empty_var,
            font=("Segoe UI", 12),
            fg_color="#e67e22",
            hover_color="#d35400",
        ).pack(anchor="w", pady=3)

        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.pack(fill="x", padx=24, pady=(4, 20))

        def cancel_preview():
            dialog.grab_release()
            dialog.destroy()

        def continue_to_confirmation():
            for row, item in enumerate(self.desktop_plan):
                item["selected"] = bool(desktop_vars[row].get())
            self.rename_desktop_conflicts = bool(rename_var.get())
            self.delete_empty_desktop_folders = bool(delete_empty_var.get())
            dialog.grab_release()
            dialog.destroy()
            self.start_cleaning(show_desktop_preview=False)

        ctk.CTkButton(
            buttons,
            text="Deselect Filtered",
            command=lambda: set_visible_selections(False),
            fg_color="#34495e",
            hover_color="#2c3e50",
            width=130,
            height=38,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            buttons,
            text="Select Filtered",
            command=lambda: set_visible_selections(True),
            fg_color="#3498db",
            hover_color="#2980b9",
            width=130,
            height=38,
        ).pack(side="left")

        ctk.CTkButton(
            buttons,
            text="Cancel",
            command=cancel_preview,
            fg_color="#34495e",
            hover_color="#2c3e50",
            width=130,
            height=38,
        ).pack(side="right", padx=(10, 0))
        ctk.CTkButton(
            buttons,
            text="Continue",
            command=continue_to_confirmation,
            fg_color="#2ecc71",
            hover_color="#27ae60",
            width=150,
            height=38,
        ).pack(side="right")

    def cleaning_logic(self):
        """Cleaning operation logic"""
        freed_bytes = 0
        cleanup_completed = False
        try:
            self.after(0, lambda: self.log_box.delete("0.0", "end"))
            self.log("🧹 Starting cleanup...\n", "#3498db")
            desktop_moves = []
            
            if self.var_system.get():
                self.log("\n─── 📁 CLEANING SYSTEM FOLDERS ───", "#f39c12")
                for name, path in TARGET_DIRS.items():
                    if not self.cleanup_selection.get(f"system:{name}", True):
                        self.log(f"   • {name}: skipped by user")
                        continue
                    if os.path.exists(path):
                        count = 0
                        try:
                            for file in os.listdir(path):
                                item_path = os.path.join(path, file)
                                item_size = calculate_path_size(item_path)
                                if safe_delete(item_path):
                                    count += 1
                                    freed_bytes += item_size
                            self.log(f"   ✓ {name}: {count} items deleted")
                        except PermissionError:
                            self.log(f"   ⚠️ {name}: Access denied")
                self.log("")

            if self.var_browser.get():
                self.log("\n─── 🌐 CLEANING BROWSERS ───", "#f39c12")
                
                advanced_browser = self.var_advanced_browser.get()
                browser_clean_list = get_browser_clean_list(advanced_browser)

                # Chromium-based browsers (Chrome, Edge, Brave, Opera)
                for name, path in BROWSER_PATHS.items():
                    if not self.cleanup_selection.get(f"browser:{name}", True):
                        self.log(f"   • {name}: skipped by user")
                        continue
                    if os.path.exists(path):
                        count, browser_freed = clean_chromium_profile(
                            path, self.log, advanced=advanced_browser
                        )
                        freed_bytes += browser_freed
                        if count > 0:
                            self.log(
                                f"   ✓ {name}: {count} items cleaned "
                                f"({format_size(browser_freed)} freed)"
                            )
                
                # Firefox (different structure)
                if (
                    os.path.exists(FIREFOX_PATH)
                    and self.cleanup_selection.get("browser:Firefox", True)
                ):
                    ff_count = 0
                    try:
                        for root, dirs, files in os.walk(FIREFOX_PATH, topdown=False):
                            for n in files + dirs:
                                if any(x.lower() == n.lower() or x.lower() in n.lower() for x in browser_clean_list):
                                    item_path = os.path.join(root, n)
                                    item_size = calculate_path_size(item_path)
                                    if safe_delete(item_path):
                                        ff_count += 1
                                        freed_bytes += item_size
                        if ff_count > 0:
                            self.log(f"   ✓ Firefox: {ff_count} items cleaned")
                    except Exception:
                        pass
                
                self.log("")

            if self.var_desktop.get():
                self.log("\n─── 🖥️ ORGANIZING DESKTOP ───", "#f39c12")
                d_path = DESKTOP_PATH
                self.log(f"   • Desktop path: {d_path}")
                if os.path.exists(d_path):
                    moved = 0
                    shortcuts_moved = 0
                    skipped_conflicts = 0
                    missing_files = 0
                    deleted_folders = 0
                    for item in self.desktop_plan:
                        if not item.get("selected", True):
                            continue
                        source_path = item["source"]
                        if not os.path.exists(source_path):
                            missing_files += 1
                            continue

                        destination = item["target"]
                        if os.path.exists(destination):
                            if self.rename_desktop_conflicts:
                                destination = get_unique_path(destination)
                            else:
                                skipped_conflicts += 1
                                continue

                        try:
                            os.makedirs(item["target_dir"], exist_ok=True)
                            shutil.move(source_path, destination)
                            desktop_moves.append({
                                "source": source_path,
                                "destination": destination,
                            })
                            if item["folder"] == "Shortcuts":
                                shortcuts_moved += 1
                            else:
                                moved += 1
                        except Exception as error:
                            self.log(
                                f"   ⚠️ Could not move {item['name']}: {type(error).__name__}"
                            )

                    self.last_desktop_moves = desktop_moves

                    if self.delete_empty_desktop_folders:
                        # Delete empty folders only when explicitly selected.
                        for item in os.listdir(d_path):
                            item_path = os.path.join(d_path, item)
                            if os.path.isdir(item_path):
                                try:
                                    if not os.listdir(item_path):
                                        os.rmdir(item_path)
                                        deleted_folders += 1
                                except Exception:
                                    pass
                    
                    if shortcuts_moved > 0:
                        self.log(f"   ✓ {shortcuts_moved} shortcuts organized → Shortcuts/")
                    if moved > 0:
                        self.log(f"   ✓ {moved} files organized")
                    if skipped_conflicts > 0:
                        self.log(f"   ℹ️ {skipped_conflicts} conflicting files skipped")
                    if missing_files > 0:
                        self.log(f"   ℹ️ {missing_files} files were no longer found")
                    if shortcuts_moved == 0 and moved == 0:
                        self.log("   ℹ️ No files to organize")
                    if deleted_folders > 0:
                        self.log(f"   ✓ {deleted_folders} empty folders deleted")
                    elif not self.delete_empty_desktop_folders:
                        self.log("   ℹ️ Empty folders were left untouched")
                    self.log("")

            # Empty Recycle Bin / Trash
            if (
                self.var_recycle_bin.get()
                and self.cleanup_selection.get("recycle_bin", True)
            ):
                trash_name = "Recycle Bin" if IS_WINDOWS else "Trash"
                self.log(f"\n─── 🗑️ EMPTYING {trash_name.upper()} ───", "#f39c12")
                bin_size, bin_count = recycle_bin_size()
                if bin_count > 0:
                    if empty_recycle_bin(self.log):
                        freed_bytes += bin_size
                        self.log(f"   ✓ {int(bin_count)} items deleted ({format_size(bin_size)})")
                else:
                    self.log(f"   ℹ️ {trash_name} is already empty")
                self.log("")

            self.log("=" * 45, "#2ecc71")
            self.log("✅ OPERATION COMPLETED SUCCESSFULLY!", "#2ecc71")
            self.log(f"💾 TOTAL SPACE FREED: {format_size(freed_bytes)}", "#2ecc71")
            self.log("=" * 45, "#2ecc71")
            cleanup_completed = True
            
        except Exception as e:
            self.log(f"❌ Error occurred: {e}", "#e74c3c")
        finally:
            self.operation_in_progress = False
            self.after(0, lambda: self.set_buttons_state(True))
            if cleanup_completed:
                self.after(0, lambda: self._finish_cleanup(freed_bytes))
            else:
                self.after(0, self._invalidate_scan)

    def undo_last_desktop_organization(self):
        """Restore files moved by the most recent desktop organization."""
        if self.operation_in_progress or not self.last_desktop_moves:
            return

        if not messagebox.askyesno(
            "Undo Desktop Organization",
            "Move the files from the last organization back to the desktop?"
        ):
            return

        self.operation_in_progress = True
        self.set_buttons_state(False)
        threading.Thread(target=self.undo_desktop_logic, daemon=True).start()

    def undo_desktop_logic(self):
        """Undo the latest desktop move journal in reverse order."""
        try:
            self.after(0, lambda: self.log_box.delete("0.0", "end"))
            self.log("↩ Undoing desktop organization...\n", "#3498db")
            restored = 0
            skipped = 0

            for move in reversed(self.last_desktop_moves):
                source_path = move["source"]
                destination = move["destination"]
                if not os.path.exists(destination) or os.path.exists(source_path):
                    skipped += 1
                    continue
                try:
                    shutil.move(destination, source_path)
                    restored += 1
                except Exception as error:
                    skipped += 1
                    self.log(
                        f"   ⚠️ Could not restore {os.path.basename(source_path)}: {type(error).__name__}"
                    )

            self.last_desktop_moves = []
            self.log(f"   ✓ {restored} file(s) restored")
            if skipped > 0:
                self.log(f"   ℹ️ {skipped} file(s) could not be restored")
            self.log("✅ Desktop organization undone", "#2ecc71")
        except Exception as error:
            self.log(f"❌ Undo failed: {type(error).__name__}", "#e74c3c")
        finally:
            self.operation_in_progress = False
            self.after(0, lambda: self.set_buttons_state(True))
            self.after(0, self._invalidate_scan)

    def on_close(self):
        """Window close handler"""
        if self.operation_in_progress:
            if not messagebox.askyesno("Warning", "Operation in progress. Close anyway?"):
                return
        self.destroy()

    def wallpaper_dialog(self):
        """Wallpaper category selection dialog"""
        if self.operation_in_progress:
            return
        
        # Create new window
        dialog = ctk.CTkToplevel(self)
        dialog.title("✨ Wallpaper Studio")
        dialog.geometry("450x600")
        dialog.resizable(False, False)
        dialog.transient(self)
        
        # On Linux, wait for window to be visible before grab_set
        if IS_LINUX:
            dialog.after(100, lambda: dialog.grab_set())
        else:
            dialog.grab_set()
        
        # Set icon
        try:
            icon_path = resource_path("neatify.ico")
            if os.path.exists(icon_path):
                dialog.iconbitmap(icon_path)
        except:
            pass
        
        # Header Frame
        header = ctk.CTkFrame(dialog, fg_color="transparent")
        header.pack(pady=(20, 10), fill="x")
        
        # Title
        ctk.CTkLabel(
            header,
            text="🖼️ Wallpaper Studio",
            font=("Segoe UI", 24, "bold"),
            text_color="#9b59b6"
        ).pack(pady=(0, 5))
        
        ctk.CTkLabel(
            header,
            text="Discover high-quality wallpapers from Unsplash.",
            font=("Segoe UI", 13),
            text_color="gray"
        ).pack()
        
        # Category buttons
        btn_frame = ctk.CTkScrollableFrame(
            dialog, 
            width=380, 
            height=350,
            corner_radius=15,
            border_width=2,
            border_color="#2c3e50"
        )
        btn_frame.pack(pady=15, padx=30, fill="both", expand=True)
        
        def select_category(category_key, category_val):
            dialog.destroy()
            self.change_wallpaper(category_key, category_val)
        
        for i, (category_name, category_val) in enumerate(WALLPAPER_CATEGORIES.items()):
            btn = ctk.CTkButton(
                btn_frame,
                text=category_name,
                font=("Segoe UI", 14, "bold"),
                fg_color="#34495e",
                hover_color="#9b59b6",
                corner_radius=8,
                height=45,
                command=lambda k=category_name, v=category_val: select_category(k, v)
            )
            btn.pack(pady=6, padx=10, fill="x")
        
        # Random button
        ctk.CTkButton(
            dialog,
            text="🎲 Surprise Me!",
            font=("Segoe UI", 15, "bold"),
            fg_color="#e74c3c",
            hover_color="#c0392b",
            corner_radius=10,
            height=50,
            command=lambda: select_category("🎲 Random", "wallpaper")
        ).pack(pady=(0, 20), padx=30, fill="x")

    def change_wallpaper(self, category_name, category_val):
        """Change wallpaper"""
        self.operation_in_progress = True
        self.set_buttons_state(False)
        
        def operation():
            try:
                self.after(0, lambda: self.log_box.delete("0.0", "end"))
                self.log(f"🖼️ Changing wallpaper...\n", "#3498db")
                self.log(f"   📂 Category: {category_name}")
                
                # Download
                image_path = download_wallpaper(category_val, self.log)
                
                if image_path and os.path.exists(image_path):
                    # Set wallpaper
                    set_wallpaper(image_path, self.log)
                    self.log("")
                    self.log("=" * 45, "#2ecc71")
                    self.log("🎉 Your new wallpaper is ready!", "#2ecc71")
                    self.log("=" * 45, "#2ecc71")
                else:
                    self.log("")
                    self.log("❌ Could not download wallpaper", "#e74c3c")
                    self.log("   Check your internet connection", "#e74c3c")
                    
            except Exception as e:
                self.log(f"❌ Error: {e}", "#e74c3c")
            finally:
                self.operation_in_progress = False
                self.after(0, lambda: self.set_buttons_state(True))
        
        threading.Thread(target=operation, daemon=True).start()


# --- MAIN PROGRAM ---
if __name__ == "__main__":
    app = AssistantGUI()
    app.mainloop()
