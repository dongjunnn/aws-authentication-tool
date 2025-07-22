
# AWS Authentication Utility

A lightweight command-line utility to simplify AWS multi-factor authentication (MFA), temporary session generation, access key rotation, and RDS IAM token generation.

This tool provides a simple interactive menu to manage credentials for multiple AWS profiles, ensuring a secure and efficient workflow.

***

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Uninstallation](#uninstallation)
- [Requirements](#requirements)
- [Contributing](#contributing)
- [License](#license)
- [Disclaimer](#disclaimer)

---

## Features

* **MFA Session Management**: Easily activate an AWS profile by generating temporary session tokens using your MFA device.
* **Secure Access Key Rotation**: Safely rotate your IAM access keys, ensuring you never exceed AWS's limit of two active keys per user.
* **RDS IAM Token Generation**: Quickly generate temporary database credentials for Amazon RDS/Aurora instances that have IAM database authentication enabled.
* **Multi-Profile Support**: Seamlessly switch between different AWS named profiles configured in your `~/.aws/credentials` file.
* **Interactive Interface**: A simple menu-driven command-line interface makes all operations straightforward.

---

## Prerequisites

Before using this tool, you must have an AWS IAM user with the following:

1.  **Programmatic Access Keys**: Your IAM user must have an `AccessKeyId` and `SecretAccessKey` configured.
2.  **MFA Enabled**: A Multi-Factor Authentication (MFA) device (virtual or hardware) must be configured for your IAM user.
3.  **Required IAM Permissions**: The user must have permissions to manage their own credentials. Attach a policy with the following permissions:
    ```json
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "iam:CreateAccessKey",
                    "iam:UpdateAccessKey",
                    "iam:DeleteAccessKey",
                    "iam:ListAccessKeys"
                ],
                "Resource": "arn:aws:iam::*:user/${aws:username}"
            }
        ]
    }
    ```

---

## Installation

The installation process involves downloading the tool, running a setup script, and configuring your shell environment. The `install.sh` script will copy the executable to `/usr/local/bin/aws-auth` and its dependencies to `/opt/aws-authentication-tool`.

#### Step 1: Download and Install the Tool

For security, it is recommended that you inspect the contents of `install.sh` before executing it with `sudo`.

```bash
# Download and extract the latest version
curl -L https://github.com/dongjunnn/aws-authentication-tool/archive/refs/heads/main.tar.gz | tar -xz

# (Optional but Recommended) Inspect the installation script
less aws-authentication-tool-main/install.sh

# Run the installer with sudo permissions
sudo bash aws-authentication-tool-main/install.sh

# Clean up the downloaded files
rm -rf aws-authentication-tool-main
````

#### Step 2: Configure Your Shell Environment

To use the tool effectively, you need to set a few environment variables. Add the following lines to your shell's configuration file (e.g., `~/.bashrc` for Bash or `~/.zshrc` for Zsh).

Replace the placeholder values for the RDS endpoints with your actual Amazon Aurora cluster endpoints.

```bash
# AWS Authentication Tool Configuration
echo 'export <YOUR_AWS_REGION>' >> ~/.bashrc
echo 'export <YOUR_AMAZON_RDS_PROD_ENDPOINT>' >> ~/.bashrc
echo 'export <YOUR_AMAZON_RDS_NONPROD_ENDPOINT>' >> ~/.bashrc

```

After saving the file, reload your shell to apply the changes:

```bash
# For Bash
source ~/.bashrc && hash -r

# For Zsh
source ~/.zshrc && hash -r
```

-----
## Usage

To start the utility, simply run the following command in your terminal:

```bash
aws-auth
```

This will launch an interactive menu where you can select your desired operation.

To verify that the session tokens have been activated correctly, you can exit the tool and check your current AWS identity using the AWS CLI:

```bash
aws sts get-caller-identity
```

-----

## Uninstallation

To completely remove the tool from your system, follow these steps:

1.  **Remove the Executable:**
    ```bash
    sudo rm /usr/local/bin/aws-auth
    ```
2.  **Remove the Installed Directory:**
    ```bash
    sudo rm -rf /opt/aws-authentication-tool
    ```
3.  **Clean up Environment Variables:**
    Remember to remove the `export` lines you added from your `~/.bashrc` or `~/.zshrc` file.

-----

## Requirements

  * **System:** A Linux or macOS environment with `bash` and standard core utilities (`curl`, `tar`).
  * **Interpreter:** Python 3.6 or later.
  * **Tools:** AWS CLI (for identity verification).
  * **Python Packages:** `boto3`, `pyotp`, `enquiries`. These are installed automatically by the `install.sh` script.

-----

## Contributing

Contributions are welcome\! If you find a bug or have a feature request, please open an issue on the GitHub repository.

-----

## License

This tool is distributed under the **MIT License**. See the `LICENSE` file for more information.

All rights to the tool, including the source code and associated intellectual property, belong to **Kabam Robotics**.

-----

## Disclaimer

This tool manages sensitive credentials, including IAM access keys. While it is designed to be safe, use it at your own risk. The author and Kabam Robotics are not responsible for any security incidents or data loss that may result from its use. Always review scripts and understand what they do before executing them.
