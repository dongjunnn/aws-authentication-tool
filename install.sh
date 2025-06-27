#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
# The directory where the executable will be placed.
# /usr/local/bin is a standard location for user-installed executables
# and is typically in the user's PATH.
INSTALL_DIR="/usr/local/bin"

# The name of the command you want to use to run your program.
APP_NAME="aws-auth"

# The directory where your application files and virtual environment will be stored.
APP_HOME="/opt/aws-authentication-tool"

# --- Main Installation Logic ---

# 1. Check for root privileges, as we're writing to system directories.
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Please use sudo." >&2
    exit 1
fi

# 2. Create the application directory.
echo "Creating application directory at $APP_HOME..."
mkdir -p "$APP_HOME"

# 3. Copy your application files to the application directory.
echo "Copying application files..."
cp src/aws-auth.py requirements.txt "$APP_HOME/"

# 4. Create and activate a virtual environment.
echo "Creating virtual environment..."
python3 -m venv "$APP_HOME/venv"

# 5. Install dependencies into the virtual environment.
echo "Installing dependencies..."
"$APP_HOME/venv/bin/pip" install -r "$APP_HOME/requirements.txt"

# 6. Create a wrapper script in the installation directory.
# This script is what the user will actually run.
echo "Creating command at $INSTALL_DIR/$APP_NAME..."
cat > "$INSTALL_DIR/$APP_NAME" <<EOL
#!/bin/bash
# This wrapper script executes your Python script with the correct interpreter
# from the virtual environment.
"$APP_HOME/venv/bin/python" "$APP_HOME/aws-auth.py" "\$@"
EOL

# 7. Make the wrapper script executable.
chmod +x "$INSTALL_DIR/$APP_NAME"

echo "Installation successful!"
echo "You can now run the tool from anywhere by typing '$APP_NAME' in your terminal."