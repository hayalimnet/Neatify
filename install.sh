#!/bin/bash
# Neatify Installer for Linux
# Usage: curl -sSL https://raw.githubusercontent.com/hayalimnet/Neatify/main/install.sh | bash

set -e

echo "✨ Neatify Installer"
echo "===================="

INSTALL_DIR="$HOME/.local/share/neatify"
VENV_DIR="$INSTALL_DIR/venv"
BIN_DIR="$HOME/.local/bin"

# Detect package manager
if command -v apt &> /dev/null; then
    PM="apt"
    echo "📦 Detected: Ubuntu/Debian"
elif command -v dnf &> /dev/null; then
    PM="dnf"
    echo "📦 Detected: Fedora/RHEL"
elif command -v pacman &> /dev/null; then
    PM="pacman"
    echo "📦 Detected: Arch Linux"
else
    echo "❌ Unsupported distribution"
    exit 1
fi

# Install system dependencies
echo ""
echo "📥 Installing system dependencies..."
case $PM in
    apt)
        sudo apt update -qq
        sudo apt install -y python3 python3-tk python3-venv curl
        ;;
    dnf)
        sudo dnf install -y python3 python3-tkinter python3-pip curl
        ;;
    pacman)
        sudo pacman -S --noconfirm python tk curl
        ;;
esac

# Create install directory
echo ""
echo "📁 Creating install directory..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# Create virtual environment
echo ""
echo "🐍 Creating virtual environment..."
python3 -m venv "$VENV_DIR"

# Install Python packages
echo ""
echo "📦 Installing Python packages..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet customtkinter requests

# Download neatify.py
echo ""
echo "⬇️ Downloading Neatify..."
curl -sSL https://raw.githubusercontent.com/hayalimnet/Neatify/main/neatify.py -o "$INSTALL_DIR/neatify.py"

# Create launcher script
echo ""
echo "🚀 Creating launcher..."
cat > "$BIN_DIR/neatify" << LAUNCHER
#!/bin/bash
$VENV_DIR/bin/python $INSTALL_DIR/neatify.py "\$@"
LAUNCHER
chmod +x "$BIN_DIR/neatify"

# Create desktop shortcut
echo ""
echo "🖥️ Creating desktop shortcut..."
cat > "$HOME/.local/share/applications/neatify.desktop" << DESKTOP
[Desktop Entry]
Name=Neatify
Comment=PC Cleanup Assistant
Exec=$BIN_DIR/neatify
Icon=utilities-system-monitor
Terminal=false
Type=Application
Categories=Utility;System;
DESKTOP

# Add ~/.local/bin to PATH if not already
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    echo "📝 Adding ~/.local/bin to PATH..."
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    export PATH="$HOME/.local/bin:$PATH"
fi

# Create symlink for sudo support
echo ""
echo "🔐 Setting up sudo support..."
sudo ln -sf "$BIN_DIR/neatify" /usr/local/bin/neatify 2>/dev/null || echo "   ⚠️ Could not create sudo symlink (optional)"

echo ""
echo "============================================"
echo "✅ Neatify installed successfully!"
echo ""
echo "Run with:  neatify"
echo "Or find it in your application menu"
echo "============================================"
