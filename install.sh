#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# --- Configuration ---
INSTALL_DIR="/usr/local/bin"
APP_NAME="aws-auth"
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
cp "$SCRIPT_DIR/src/aws-auth.py" "$SCRIPT_DIR/requirements.txt" "$APP_HOME/"

# 4. Create and activate a virtual environment.
echo "Creating virtual environment..."
python3 -m venv "$APP_HOME/venv"

# 5. Install dependencies into the virtual environment.
echo "Installing dependencies..."
"$APP_HOME/venv/bin/pip" install -r "$APP_HOME/requirements.txt"

# 6. Create the main run script inside the application home directory.
# This contains the logic from your original run.sh, but with absolute paths.
echo "Creating run script at $APP_HOME/run.sh..."
cat > "$APP_HOME/run.sh" <<EOL
#!/bin/bash

# This script is intended to be sourced by the main aws-auth command.

# Execute the python script using the virtual environment.
# The python script will handle user interaction and create the temp credential file.
"$APP_HOME/venv/bin/python" "$APP_HOME/aws-auth.py"

# Source the temporary file with credentials if it was created by the python script.
if [ -f "/tmp/aws_env_vars888.sh" ]; then
    source /tmp/aws_env_vars888.sh
    rm /tmp/aws_env_vars888.sh
    echo "AWS temporary credentials have been set for this shell session."
fi
EOL

# 7. Create the main aws-auth command in the installation directory.
# This command simply sources the run.sh script.
echo "Creating command at $INSTALL_DIR/$APP_NAME..."
cat > "$INSTALL_DIR/$APP_NAME" <<EOL
#!/bin/bash
#
# This wrapper script executes your main run script.
# To set credentials in your current shell, you MUST run this with 'source':
#
#   source aws-auth
#
source "$APP_HOME/run.sh"
EOL

# 8. Make both new scripts executable.
chmod +x "$APP_HOME/run.sh"
chmod +x "$INSTALL_DIR/$APP_NAME"

echo ""
echo "Installation successful!"
echo "To set your AWS credentials, you must run the tool using the 'source' command:"
echo ""
echo "  source $APP_NAME"
echo ""