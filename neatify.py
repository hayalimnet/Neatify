import customtkinter as ctk
from tkinter import messagebox
import os
import shutil
import pathlib
import stat
import sys
import ctypes
import threading

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
    """Check for Windows administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# --- RESOURCE PATH (FOR EXE) ---
def resource_path(relative_path):
    """Returns the path to resource files when packaged with PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# --- SETTINGS AND PATHS ---
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

# Browser files/folders to delete (CACHE ONLY - safe)
# Note: Cookies, Login Data and other sensitive files are NOT included
BROWSER_CLEAN_LIST = [
    # Cache folders
    "Cache", "Code Cache", "GPUCache", "ShaderCache", "GrShaderCache",
    "Service Worker", "CacheStorage",
    # Temporary files
    "thumbnails", "Favicons", "Favicons-journal",
    # Firefox cache
    "cache2", "startupCache", "OfflineCache"
]

DESKTOP_RULES = {
    'Images': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.ico', '.tiff', '.tif', '.raw'],
    'Documents': ['.pdf', '.docx', '.doc', '.txt', '.xlsx', '.xls', '.pptx', '.ppt', '.odt', '.rtf', '.log', '.md'],
    'Programs': ['.exe', '.msi', '.bat', '.ps1', '.cmd', '.vbs', '.reg'],
    'Archives': ['.zip', '.rar', '.7z', '.iso', '.tar', '.gz', '.bz2', '.xz'],
    'Code': ['.py', '.js', '.html', '.css', '.json', '.cpp', '.sql', '.java', '.cs', '.ts', '.jsx', '.tsx', '.xml', '.yaml', '.yml'],
    'Fonts': ['.ttf', '.otf', '.woff', '.woff2', '.eot'],
    'Videos': ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'],
    'Music': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'],
    'Design': ['.psd', '.ai', '.eps', '.svg', '.fig', '.xd', '.sketch'],
    'Database': ['.db', '.sqlite', '.sql', '.mdb', '.accdb'],
    '3D_CAD': ['.stl', '.obj', '.fbx', '.blend', '.dwg', '.dxf'],
    'Other': ['.rf', '.torrent', '.nfo', '.srt', '.sub']
}

# --- HELPER FUNCTIONS ---
def recycle_bin_size():
    """Calculate total file size in Recycle Bin"""
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

def empty_recycle_bin(log_func=None):
    """Empty Windows Recycle Bin"""
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
        user32 = ctypes.windll.user32
        width = user32.GetSystemMetrics(0)
        height = user32.GetSystemMetrics(1)
        
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
        wallpaper_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Neatify')
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

def set_wallpaper(image_path, log_func=None):
    """
    Change Windows desktop wallpaper.
    """
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

def format_size(byte_size):
    """Convert bytes to human readable format"""
    if byte_size < 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if byte_size < 1024:
            return f"{byte_size:.2f} {unit}"
        byte_size /= 1024
    return f"{byte_size:.2f} TB"

# Chromium browser files to delete (CACHE ONLY)
# Note: History, Cookies, Login Data and other sensitive files are NOT included
CHROMIUM_PROFILE_FILES = [
    "Favicons", "Favicons-journal",
    "Shortcuts", "Shortcuts-journal",
    "Network Action Predictor", "Network Action Predictor-journal"
]

# Chromium browser folders to delete (CACHE)
CHROMIUM_PROFILE_DIRS = [
    "Cache", "Code Cache", "GPUCache", "ShaderCache", "GrShaderCache",
    "Service Worker", "CacheStorage", "File System",
    "Local Storage", "Session Storage", "IndexedDB",
    "blob_storage", "databases", "Platform Notifications"
]

def clean_chromium_profile(browser_path, log_func=None):
    """
    Clean Chromium-based browser profile folders.
    Scans all profiles: Default, Profile 1, Profile 2, etc.
    """
    deleted = 0
    if not os.path.exists(browser_path):
        return 0
    
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
        for file_name in CHROMIUM_PROFILE_FILES:
            file_path = os.path.join(profile, file_name)
            if os.path.exists(file_path):
                if safe_delete(file_path, log_func):
                    deleted += 1
        
        # Delete folders
        for folder_name in CHROMIUM_PROFILE_DIRS:
            folder_path = os.path.join(profile, folder_name)
            if os.path.exists(folder_path):
                if safe_delete(folder_path, log_func):
                    deleted += 1
    
    # Also clean Cache folders in main directory
    for folder_name in ["Cache", "GPUCache", "ShaderCache", "GrShaderCache"]:
        folder_path = os.path.join(browser_path, folder_name)
        if os.path.exists(folder_path):
            if safe_delete(folder_path, log_func):
                deleted += 1
    
    return deleted

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
    try:
        for root, _, files in os.walk(path):
            for f in files:
                if filter_list:
                    if any(x.lower() in root.lower() or x.lower() in f.lower() for x in filter_list):
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


# --- GUI CLASS ---
class AssistantGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Neatify v1.0")
        self.geometry("750x600")
        self.minsize(600, 500)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Set icon
        self._set_icon()
        
        # Operation state
        self.operation_in_progress = False
        
        # Grid settings
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Title
        self.title_label = ctk.CTkLabel(
            self, 
            text="✨ Neatify - PC Cleaning Assistant", 
            font=("Segoe UI", 26, "bold")
        )
        self.title_label.grid(row=0, column=0, pady=(20, 10))
        
        # Admin warning
        if not is_admin():
            self.admin_label = ctk.CTkLabel(
                self, 
                text="⚠️ Run as Administrator for full cleaning",
                font=("Segoe UI", 12),
                text_color="#f39c12"
            )
            self.admin_label.grid(row=0, column=0, pady=(55, 0))

        # Options Panel
        self.options_frame = ctk.CTkFrame(self)
        self.options_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.options_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.var_system = ctk.BooleanVar(value=True)
        self.cb_system = ctk.CTkCheckBox(
            self.options_frame, 
            text="🗂️ System Cleanup", 
            variable=self.var_system,
            font=("Segoe UI", 13)
        )
        self.cb_system.grid(row=0, column=0, padx=10, pady=15)

        self.var_browser = ctk.BooleanVar(value=True)
        self.cb_browser = ctk.CTkCheckBox(
            self.options_frame, 
            text="🌐 Browser Cleanup", 
            variable=self.var_browser,
            font=("Segoe UI", 13)
        )
        self.cb_browser.grid(row=0, column=1, padx=10, pady=15)

        self.var_desktop = ctk.BooleanVar(value=False)
        self.cb_desktop = ctk.CTkCheckBox(
            self.options_frame, 
            text="🖥️ Organize Desktop", 
            variable=self.var_desktop,
            font=("Segoe UI", 13)
        )
        self.cb_desktop.grid(row=0, column=2, padx=10, pady=15)

        self.var_recycle_bin = ctk.BooleanVar(value=True)
        self.cb_recycle_bin = ctk.CTkCheckBox(
            self.options_frame, 
            text="🗑️ Empty Recycle Bin", 
            variable=self.var_recycle_bin,
            font=("Segoe UI", 13)
        )
        self.cb_recycle_bin.grid(row=0, column=3, padx=10, pady=15)

        # Log Box
        self.log_box = ctk.CTkTextbox(
            self, 
            font=("Consolas", 12),
            corner_radius=10
        )
        self.log_box.grid(row=2, column=0, padx=20, pady=15, sticky="nsew")
        self.log_box.insert("0.0", "🎉 Welcome!\n\nClick '🔍 Analyze' to scan your system.\n")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self, mode="indeterminate")
        self.progress_bar.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.progress_bar.set(0)

        # Buttons
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=4, column=0, pady=(0, 20))

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

    def log(self, message):
        """Thread-safe logging"""
        self.after(0, self._write_log, message)

    def _write_log(self, message):
        """Write log in main thread"""
        self.log_box.insert("end", f"\n{message}")
        self.log_box.see("end")

    def set_buttons_state(self, enabled):
        """Enable/disable buttons"""
        state = "normal" if enabled else "disabled"
        self.btn_analyze.configure(state=state)
        self.btn_clean.configure(state=state)
        self.cb_system.configure(state=state)
        self.cb_browser.configure(state=state)
        self.cb_desktop.configure(state=state)
        self.cb_recycle_bin.configure(state=state)
        
        if enabled:
            self.progress_bar.stop()
            self.progress_bar.set(0)
        else:
            self.progress_bar.start()

    def start_analysis(self):
        """Start analysis operation"""
        if self.operation_in_progress:
            return
        self.operation_in_progress = True
        self.set_buttons_state(False)
        threading.Thread(target=self.analysis_logic, daemon=True).start()

    def analysis_logic(self):
        """Analysis operation logic"""
        try:
            self.after(0, lambda: self.log_box.delete("0.0", "end"))
            self.log("🔍 Starting analysis...\n")
            
            total = 0
            
            # System
            if self.var_system.get():
                self.log("📁 Scanning system folders...")
                s_size = 0
                for name, path in TARGET_DIRS.items():
                    if os.path.exists(path):
                        size = calculate_folder_size(path)
                        s_size += size
                        self.log(f"   • {name}: {format_size(size)}")
                self.log(f"   ➜ System Total: {format_size(s_size)}\n")
                total += s_size
            
            # Browser
            if self.var_browser.get():
                self.log("🌐 Scanning browsers...")
                b_size = 0
                for name, path in BROWSER_PATHS.items():
                    if os.path.exists(path):
                        size = calculate_folder_size(path, BROWSER_CLEAN_LIST)
                        if size > 0:
                            b_size += size
                            self.log(f"   • {name}: {format_size(size)}")
                
                if os.path.exists(FIREFOX_PATH):
                    ff_size = calculate_folder_size(FIREFOX_PATH, BROWSER_CLEAN_LIST)
                    if ff_size > 0:
                        b_size += ff_size
                        self.log(f"   • Firefox: {format_size(ff_size)}")
                
                self.log(f"   ➜ Browser Total: {format_size(b_size)}\n")
                total += b_size
            
            # Desktop analysis
            if self.var_desktop.get():
                self.log("🖥️ Scanning desktop...")
                d_path = os.path.join(USER_PROFILE, 'Desktop')
                if os.path.exists(d_path):
                    file_count = len([f for f in os.listdir(d_path) if os.path.isfile(os.path.join(d_path, f))])
                    empty_folder_count = len([d for d in os.listdir(d_path) 
                                             if os.path.isdir(os.path.join(d_path, d)) 
                                             and not os.listdir(os.path.join(d_path, d))])
                    self.log(f"   • Files to organize: {file_count}")
                    if empty_folder_count > 0:
                        self.log(f"   • Empty folders to delete: {empty_folder_count}")
                    self.log("")
            
            # Recycle Bin analysis
            if self.var_recycle_bin.get():
                self.log("🗑️ Scanning Recycle Bin...")
                bin_size, bin_count = recycle_bin_size()
                if bin_count > 0:
                    self.log(f"   • {int(bin_count)} items, {format_size(bin_size)}")
                    total += bin_size
                else:
                    self.log("   • Recycle Bin is empty")
                self.log("")
            
            self.log("=" * 45)
            self.log(f"📊 TOTAL CLEANABLE: {format_size(total)}")
            self.log("=" * 45)
            
        except Exception as e:
            self.log(f"❌ Error occurred: {e}")
        finally:
            self.operation_in_progress = False
            self.after(0, lambda: self.set_buttons_state(True))

    def start_cleaning(self):
        """Start cleaning operation"""
        if self.operation_in_progress:
            return
        
        # Get confirmation
        selections = []
        if self.var_system.get():
            selections.append("System files")
        if self.var_browser.get():
            selections.append("Browser cache")
        if self.var_desktop.get():
            selections.append("Desktop organization")
        if self.var_recycle_bin.get():
            selections.append("Empty Recycle Bin")
        
        if not selections:
            messagebox.showwarning("Warning", "Please select at least one option.")
            return
        
        confirm = messagebox.askyesno(
            "Confirmation", 
            f"The following operations will be performed:\n\n• " + "\n• ".join(selections) + "\n\nContinue?"
        )
        
        if not confirm:
            return
        
        self.operation_in_progress = True
        self.set_buttons_state(False)
        threading.Thread(target=self.cleaning_logic, daemon=True).start()

    def cleaning_logic(self):
        """Cleaning operation logic"""
        try:
            self.after(0, lambda: self.log_box.delete("0.0", "end"))
            self.log("🧹 Starting cleanup...\n")
            
            if self.var_system.get():
                self.log("📁 Cleaning system...")
                for name, path in TARGET_DIRS.items():
                    if os.path.exists(path):
                        count = 0
                        try:
                            for file in os.listdir(path):
                                if safe_delete(os.path.join(path, file)):
                                    count += 1
                            self.log(f"   ✓ {name}: {count} items deleted")
                        except PermissionError:
                            self.log(f"   ⚠️ {name}: Access denied")
                self.log("")

            if self.var_browser.get():
                self.log("🌐 Cleaning browsers...")
                
                # Chromium-based browsers (Chrome, Edge, Brave, Opera)
                for name, path in BROWSER_PATHS.items():
                    if os.path.exists(path):
                        count = clean_chromium_profile(path)
                        if count > 0:
                            self.log(f"   ✓ {name}: {count} items cleaned")
                
                # Firefox (different structure)
                if os.path.exists(FIREFOX_PATH):
                    ff_count = 0
                    try:
                        for root, dirs, files in os.walk(FIREFOX_PATH, topdown=False):
                            for n in files + dirs:
                                if any(x.lower() == n.lower() or x.lower() in n.lower() for x in BROWSER_CLEAN_LIST):
                                    if safe_delete(os.path.join(root, n)):
                                        ff_count += 1
                        if ff_count > 0:
                            self.log(f"   ✓ Firefox: {ff_count} items cleaned")
                    except Exception:
                        pass
                
                self.log("")

            if self.var_desktop.get():
                self.log("🖥️ Organizing desktop...")
                d_path = os.path.join(USER_PROFILE, 'Desktop')
                if os.path.exists(d_path):
                    moved = 0
                    deleted_folders = 0
                    
                    # Move files to categories
                    for file in os.listdir(d_path):
                        f_path = os.path.join(d_path, file)
                        if os.path.isfile(f_path):
                            ext = pathlib.Path(file).suffix.lower()
                            for folder, extensions in DESKTOP_RULES.items():
                                if ext in extensions:
                                    target = os.path.join(d_path, folder)
                                    os.makedirs(target, exist_ok=True)
                                    try:
                                        shutil.move(f_path, os.path.join(target, file))
                                        moved += 1
                                    except Exception:
                                        pass
                                    break
                    
                    # Delete empty folders (only on desktop, don't recurse)
                    for item in os.listdir(d_path):
                        item_path = os.path.join(d_path, item)
                        if os.path.isdir(item_path):
                            try:
                                # Check if folder is empty
                                if not os.listdir(item_path):
                                    os.rmdir(item_path)
                                    deleted_folders += 1
                            except Exception:
                                pass
                    
                    self.log(f"   ✓ {moved} files organized")
                    if deleted_folders > 0:
                        self.log(f"   ✓ {deleted_folders} empty folders deleted")
                    self.log("")

            # Empty Recycle Bin
            if self.var_recycle_bin.get():
                self.log("🗑️ Emptying Recycle Bin...")
                bin_size, bin_count = recycle_bin_size()
                if bin_count > 0:
                    if empty_recycle_bin(self.log):
                        self.log(f"   ✓ {int(bin_count)} items deleted ({format_size(bin_size)})")
                else:
                    self.log("   ℹ️ Recycle Bin is already empty")
                self.log("")

            self.log("=" * 45)
            self.log("✅ OPERATION COMPLETED SUCCESSFULLY!")
            self.log("=" * 45)
            
        except Exception as e:
            self.log(f"❌ Error occurred: {e}")
        finally:
            self.operation_in_progress = False
            self.after(0, lambda: self.set_buttons_state(True))

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
        dialog.title("🖼️ Change Wallpaper")
        dialog.geometry("400x500")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        # Set icon
        try:
            icon_path = resource_path("neatify.ico")
            if os.path.exists(icon_path):
                dialog.iconbitmap(icon_path)
        except:
            pass
        
        # Title
        ctk.CTkLabel(
            dialog,
            text="🖼️ Select Wallpaper Category",
            font=("Segoe UI", 18, "bold")
        ).pack(pady=20)
        
        ctk.CTkLabel(
            dialog,
            text="High quality wallpapers from Unsplash",
            font=("Segoe UI", 12),
            text_color="gray"
        ).pack()
        
        # Category buttons
        btn_frame = ctk.CTkScrollableFrame(dialog, width=350, height=300)
        btn_frame.pack(pady=20, padx=20, fill="both", expand=True)
        
        def select_category(category_key, category_val):
            dialog.destroy()
            self.change_wallpaper(category_key, category_val)
        
        for i, (category_name, category_val) in enumerate(WALLPAPER_CATEGORIES.items()):
            btn = ctk.CTkButton(
                btn_frame,
                text=category_name,
                font=("Segoe UI", 14),
                width=300,
                height=40,
                command=lambda k=category_name, v=category_val: select_category(k, v)
            )
            btn.pack(pady=5)
        
        # Random button
        ctk.CTkButton(
            dialog,
            text="🎲 Random",
            font=("Segoe UI", 14, "bold"),
            fg_color="#e74c3c",
            hover_color="#c0392b",
            width=200,
            height=45,
            command=lambda: select_category("🎲 Random", "wallpaper")
        ).pack(pady=15)

    def change_wallpaper(self, category_name, category_val):
        """Change wallpaper"""
        self.operation_in_progress = True
        self.set_buttons_state(False)
        
        def operation():
            try:
                self.after(0, lambda: self.log_box.delete("0.0", "end"))
                self.log(f"🖼️ Changing wallpaper...\n")
                self.log(f"   📂 Category: {category_name}")
                
                # Download
                image_path = download_wallpaper(category_val, self.log)
                
                if image_path and os.path.exists(image_path):
                    # Set wallpaper
                    set_wallpaper(image_path, self.log)
                    self.log("")
                    self.log("=" * 45)
                    self.log("🎉 Your new wallpaper is ready!")
                    self.log("=" * 45)
                else:
                    self.log("")
                    self.log("❌ Could not download wallpaper")
                    self.log("   Check your internet connection")
                    
            except Exception as e:
                self.log(f"❌ Error: {e}")
            finally:
                self.operation_in_progress = False
                self.after(0, lambda: self.set_buttons_state(True))
        
        threading.Thread(target=operation, daemon=True).start()


# --- MAIN PROGRAM ---
if __name__ == "__main__":
    app = AssistantGUI()
    app.mainloop()
