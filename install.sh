#!/bin/bash
# Neatify Installer for Linux
# Usage: curl -sSL https://raw.githubusercontent.com/hayalimnet/Neatify/main/install.sh | bash

set -e

echo "Neatify Installer"
echo "===================="

INSTALL_DIR="$HOME/.local/share/neatify"
VENV_DIR="$INSTALL_DIR/venv"
BIN_DIR="$HOME/.local/bin"

if command -v apt &> /dev/null; then
    PM="apt"
    echo "Detected: Ubuntu/Debian"
elif command -v dnf &> /dev/null; then
    PM="dnf"
    echo "Detected: Fedora/RHEL"
elif command -v pacman &> /dev/null; then
    PM="pacman"
    echo "Detected: Arch Linux"
else
    echo "Unsupported distribution"
    exit 1
fi

echo ""
echo "Installing system dependencies..."
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

echo ""
echo "Creating install directory..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

echo ""
echo "Creating virtual environment..."
python3 -m venv "$VENV_DIR"

echo ""
echo "Installing Python packages..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet customtkinter requests

echo ""
echo "Downloading Neatify..."
curl -sSL https://raw.githubusercontent.com/hayalimnet/Neatify/main/neatify.py -o "$INSTALL_DIR/neatify.py"

echo ""
echo "Creating launcher..."
echo '#!/bin/bash' > "$BIN_DIR/neatify"
echo "$VENV_DIR/bin/python $INSTALL_DIR/neatify.py \"\$@\"" >> "$BIN_DIR/neatify"
chmod +x "$BIN_DIR/neatify"

echo ""
echo "Creating desktop shortcut..."
cat > "$HOME/.local/share/applications/neatify.desktop" << DESKTOPFILE
[Desktop Entry]
Name=Neatify
Comment=PC Cleanup Assistant
Exec=$BIN_DIR/neatify
Icon=utilities-system-monitor
Terminal=false
Type=Application
Categories=Utility;System;
DESKTOPFILE

if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    echo "Adding ~/.local/bin to PATH..."
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    export PATH="$HOME/.local/bin:$PATH"
fi

echo ""
echo "Setting up sudo support..."
sudo ln -sf "$BIN_DIR/neatify" /usr/local/bin/neatify 2>/dev/null || true

echo ""
echo "============================================"
echo "Neatify installed successfully!"
echo ""
echo "Run with:  neatify"
echo "Or find it in your application menu"
echo "============================================"
