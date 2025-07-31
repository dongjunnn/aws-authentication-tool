#!/usr/bin/env python3

import configparser
import os
import enquiries
import pyotp
from os.path import expanduser
from curtsies.fmtfuncs import red, bold, green, on_blue, yellow, cyan
import boto3
import binascii
import sys
from enquiries.error import SelectionAborted
import urllib.parse
from datetime import datetime, timezone
import time


home = expanduser("~")
config = configparser.ConfigParser()
awsCredFile = '%s/.aws/credentials' % (home)
config.read(awsCredFile)


# Helper function to handle input prompts correctly when using eval
def get_input(prompt):
    return input(prompt).strip()


def test_rds_token_connection(hostname, db_user, db_name, token):
    import subprocess
    command = f'psql "host={hostname} port=5432 dbname={db_name} user={db_user} sslmode=require" -c \'SELECT 1;\''
    env = os.environ.copy()
    env['PGPASSWORD'] = token

    print(yellow("Validating RDS IAM token by attempting a connection..."))

    try:
        result = subprocess.run(command, shell=True, env=env, capture_output=True, text=True)
        if result.returncode == 0:
            print(green("Token is valid! Successfully connected to the database."))
            return True
        else:
            print(red("Token validation failed. Could not connect to database."))
            print(red(result.stderr.strip()))
            return False
    except Exception as e:
        print(red(f"Exception occurred while testing token: {e}"))
        return False


def stage_main_menu():
    menu = ["Activate Profile (Get Token)", "Activate DB", "Rotate Keys", "Add New Profile", "Remove Profile","Quit"]
    choice = enquiries.choose("Action:", menu)
    if choice == "Activate Profile (Get Token)":
        return "Activate Profile (Get Token)"
    if choice == "Add New Profile":
        return "Add New Profile"
    if choice == "Quit":
        return "Quit"
    if choice == "Remove Profile":
        return "Remove Profile"
    if choice == "Activate DB":
        return "Activate DB"
    if choice == "Rotate Keys":
        return "Rotate Keys"


def stage_rotate_keys():
    users = config.sections()

    if not users:
        print(red("No users found. Please add a user first."))
        return "main_menu"

    choice = enquiries.choose("Choose a user to rotate keys for:", users)
    if not choice:
        return "main_menu"

    try:
        print(yellow(f"Rotating keys for: {choice}"))

        current_key_id = config[choice]['aws_access_key_id']

        session = boto3.Session(
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=os.environ.get("AWS_SESSION_TOKEN")
        )
        iam_client = session.client('iam')
        sts_client = session.client('sts')

        identity = sts_client.get_caller_identity()
        arn = identity['Arn']
        current_user = arn.split('/')[-1]

        # Step 1: Delete old key FIRST to stay within the 2-key limit
        print("Deleting old access key...")
        iam_client.delete_access_key(UserName=current_user, AccessKeyId=current_key_id)
        print(green("Old key deleted."))

        # Step 2: Create new access key
        print("Creating new access key...")
        new_key = iam_client.create_access_key(UserName=current_user)['AccessKey']
        new_access_key = new_key['AccessKeyId']
        new_secret_key = new_key['SecretAccessKey']
        print(green("New access key created."))

        # Step 3: Update ~/.aws/credentials
        config[choice]['aws_access_key_id'] = new_access_key
        config[choice]['aws_secret_access_key'] = new_secret_key
        with open(awsCredFile, 'w') as configfile:
            config.write(configfile)

        print(green(f"Success! New keys saved for profile '{choice}' in {awsCredFile}"))

        print(yellow("Waiting for 10 seconds for new key to propagate..."))
        time.sleep(10)

        # Automatically log in using the newly rotated key
        print(yellow("Verifying identity and requesting session token with new key..."))

        os.environ.pop("AWS_ACCESS_KEY_ID", None)
        os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
        os.environ.pop("AWS_SESSION_TOKEN", None)


        # First, verify identity
        temp_session = boto3.Session(
            aws_access_key_id=new_access_key,
            aws_secret_access_key=new_secret_key
        )
        sts_temp = temp_session.client('sts')

        identity = sts_temp.get_caller_identity()
        print(green(f"Identity confirmed: {identity['Arn']}"))

        # Then generate TOTP and request session token
        totp = pyotp.TOTP(config[choice]['mfa_token']).now()
        response = sts_temp.get_session_token(
            SerialNumber=config[choice]['mfa_serial_arn'],
            TokenCode=totp
        )
        credentials = response['Credentials']

        # Export to env
        os.environ['AWS_ACCESS_KEY_ID'] = credentials['AccessKeyId']
        os.environ['AWS_SECRET_ACCESS_KEY'] = credentials['SecretAccessKey']
        os.environ['AWS_SESSION_TOKEN'] = credentials['SessionToken']

        # Optionally dump to temp file for shell source
        temp_env_file = "/tmp/aws_env_vars888.sh"
        with open(temp_env_file, 'w') as f:
            f.write(f"export AWS_ACCESS_KEY_ID=\"{credentials['AccessKeyId']}\"\n")
            f.write(f"export AWS_SECRET_ACCESS_KEY=\"{credentials['SecretAccessKey']}\"\n")
            f.write(f"export AWS_SESSION_TOKEN=\"{credentials['SessionToken']}\"\n")

        print(green("Logged in with temporary session credentials!"))
        print(f"export AWS_ACCESS_KEY_ID=\"{credentials['AccessKeyId']}\"")
        print(f"export AWS_SECRET_ACCESS_KEY=\"{credentials['SecretAccessKey']}\"")
        print(f"export AWS_SESSION_TOKEN=\"{credentials['SessionToken']}\"")

    except Exception as e:
        print(red(f"Failed to rotate keys: {e}"))

    return "main_menu"


def stage_choose_user():
    users = config.sections()
    if not users:
        print(red("No users found. Please add a user first."))
        return "main_menu"

    choice = enquiries.choose("Choose a user:", users)
    try:
        if choice:
            print(f"You selected: {choice}")
            mfa_serial_arn = config[choice]['mfa_serial_arn']
            token = config[choice]['mfa_token']
            totp = pyotp.TOTP(token).now()

            print("Requesting temporary session token from AWS...")
            session = boto3.Session(profile_name=choice)
            sts_client = session.client('sts')

            iam_client = session.client('iam')
            identity = sts_client.get_caller_identity()
            arn = identity['Arn']  # arn:aws:iam::acct:user/dongjun
            current_user = arn.split('/')[-1]
            access_keys = iam_client.list_access_keys(UserName=current_user)['AccessKeyMetadata']

            # Find matching key ID from config
            current_key_id = config[choice]['aws_access_key_id']

            # Find the key creation date
            key_info = next((key for key in access_keys if key['AccessKeyId'] == current_key_id), None)

            if key_info:
                created = key_info['CreateDate']
                now = datetime.now(timezone.utc)
                age_days = (now - created).days

                if age_days >= 90:
                    print(red(f"Access key is {age_days} days old. Rotation required. Login blocked."))
                    return "main_menu"
                elif age_days >= 80:
                    print(red(f" Warning: Access key is {age_days} days old. Please rotate soon!"))
                else:
                    print(green(f"Access key is {age_days} days old."))
            else:
                print(yellow(" Could not find metadata for the current access key."))

            response = sts_client.get_session_token(
                SerialNumber=mfa_serial_arn,
                TokenCode=totp
            )
            credentials = response['Credentials']

            print(green("Credentials obtained successfully!"))
            print(f"Expiration: {credentials['Expiration']}")

            os.environ['AWS_ACCESS_KEY_ID'] = credentials['AccessKeyId']
            os.environ['AWS_SECRET_ACCESS_KEY'] = credentials['SecretAccessKey']
            os.environ['AWS_SESSION_TOKEN'] = credentials['SessionToken']

            temp_env_file = "/tmp/aws_env_vars888.sh" # Or use tempfile module for robust temp file creation
            with open(temp_env_file, 'w') as f:
                f.write(f"export AWS_ACCESS_KEY_ID=\"{credentials['AccessKeyId']}\"\n")
                f.write(f"export AWS_SECRET_ACCESS_KEY=\"{credentials['SecretAccessKey']}\"\n")
                f.write(f"export AWS_SESSION_TOKEN=\"{credentials['SessionToken']}\"\n")
            print(f"export AWS_ACCESS_KEY_ID=\"{credentials['AccessKeyId']}\"")
            print(f"export AWS_SECRET_ACCESS_KEY=\"{credentials['SecretAccessKey']}\"")
            print(f"export AWS_SESSION_TOKEN=\"{credentials['SessionToken']}\"")

            return "main_menu"
        else:
            return "back"
    except Exception as e:
        print(red("An error occurred!"))
        print(red(f"Error: {e}"))
        return "main_menu"

def stage_remove_user():
    users = config.sections()
    if not users:
        print("No users found. Please add a user first.")
        return "back"

    choice = enquiries.choose("Choose a user to remove:", users)
    if choice:
        confirm = get_input(f"Are you sure you want to remove the profile '{choice}'? (y/n): ")
        if confirm.lower() == 'y':
            config.remove_section(choice)
            try:
                with open(awsCredFile, 'w') as configfile:
                    config.write(configfile)
                print(green(f"Success! Profile '{choice}' was removed from {awsCredFile}"))
            except Exception as e:
                print(red(f"Error writing to credentials file: {e}"))
        else:
            print("Removal cancelled.")
    return "back"

def validate_credentials_directly(access_key, secret_key, mfa_serial=None, mfa_token_secret=None):
    print(cyan("Validating credentials with AWS before saving..."))
    try:
        if not mfa_serial or not mfa_token_secret:
            print(red("MFA Serial and Token are required for validation."))
            return False

        pyotp.TOTP(mfa_token_secret).now()
        totp = pyotp.TOTP(mfa_token_secret).now()

        print("MFA secret key format is valid. Now checking with AWS...")
        sts_client = boto3.client(
            'sts',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        sts_client.get_session_token(
            SerialNumber=mfa_serial,
            TokenCode=totp,
            DurationSeconds=900
        )
        print(green("MFA credentials and token are valid!"))
        return True

    except binascii.Error:
        print(red("Validation Failed: The MFA Token Secret is not a valid Base32 string."))
        return False
    except Exception as e:
        print(red(f"Validation Failed: {e}"))
        return False

def stage_add_user():
    print("--- Add New AWS Profile ---")

    profile_name = get_input("Enter a unique name for this profile: ")
    if not profile_name:
        print(red("Profile name cannot be empty."))
        get_input("Press Enter to return.")
        return "main_menu"

    access_key = get_input("Enter AWS Access Key ID: ")
    secret_key = get_input("Enter AWS Secret Access Key: ")
    mfa_serial = get_input("Enter MFA Serial/ARN: ")
    mfa_token = ""
    if mfa_serial:
        mfa_token = get_input("Enter MFA Token Secret: ")

    if not validate_credentials_directly(access_key, secret_key, mfa_serial, mfa_token):
        print(red("Credentials could not be validated and were not saved."))
        get_input("Press Enter to return to the main menu...")
        return "main_menu"

    config.add_section(profile_name)
    config.set(profile_name, 'aws_access_key_id', access_key)
    config.set(profile_name, 'aws_secret_access_key', secret_key)
    config.set(profile_name, 'mfa_serial_arn', mfa_serial)
    config.set(profile_name, 'mfa_token', mfa_token)

    try:
        with open(awsCredFile, 'w') as configfile:
            config.write(configfile)
        print(green(f"Success! Profile '{profile_name}' was added to {awsCredFile}"))
    except Exception as e:
        print(red(f"Error writing to credentials file: {e}"))

    get_input("Press Enter to return to the main menu...")
    return "main_menu"

def stage_activate_db():
    print(bold("--- Retrieve RDS IAM DB Login Token ---"))
    # Choose environment (e.g., prod vs nonprod)
    menu = ["prod", "nonprod"]
    env_choice = enquiries.choose("Choose environment:", menu)

    # Set RDS endpoints based on choice
    db_endpoints = {
        "prod": os.environ.get("RDS_ENDPOINT_PROD"),
        "nonprod": os.environ.get("RDS_ENDPOINT_NONPROD")
    }

    hostname = db_endpoints.get(env_choice)
    if not hostname:
        print(red("Invalid environment selected."))
        return "main_menu"

    # Prompt for database username
    db_user = get_input("Enter database username (e.g. dongjun): ")
    db_name = get_input("Enter database name (e.g. dev_ums): ")
    if not db_user:
        print(red("Database username cannot be empty."))
        return "main_menu"

    try:
        print(yellow("Generating RDS IAM token using current AWS session..."))
        region = os.environ.get("AWS_REGION")

        session = boto3.Session(
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=os.environ.get("AWS_SESSION_TOKEN"),
            region_name=region
        )
        rds_client = session.client("rds")
        token = rds_client.generate_db_auth_token(
            DBHostname=hostname,
            Port=5432,
            DBUsername=db_user,
            Region=region
        )

        print(green("Token generated successfully!"))
        # print(cyan("Example `psql` connection string:"))

        print("The token is (sslmode=require):" + green(f" {token}"))

        # Test the token before offering to launch psql
        if not test_rds_token_connection(hostname, db_user, db_name, token):
            print(red("Skipping auto-launch since the token failed validation."))
            get_input("Press Enter to return to the main menu...")
            return "main_menu"

        auto_launch = get_input("Do you want to launch psql now? (y/n): ").lower() == 'y'
        if auto_launch:
            import subprocess
            env = os.environ.copy()
            env['PGPASSWORD'] = token
            command = f'psql "host={hostname} port=5432 dbname={db_name} user={db_user} sslmode=require"'
            subprocess.run(command, shell=True, env=env)
    except Exception as e:
        print(red("Failed to generate DB token."))
        print(red(str(e)))

    get_input("Press Enter to return to the main menu...")
    return "main_menu"


def main():
    history = []
    current_stage = "main_menu"

    while True:
        if current_stage == "main_menu":
            next_stage = stage_main_menu()
        elif current_stage == "Activate Profile (Get Token)":
            next_stage = stage_choose_user()
        elif current_stage == "Add New Profile":
            next_stage = stage_add_user()
        elif current_stage == "Activate DB":
            next_stage = stage_activate_db()
        elif current_stage == "Rotate Keys":
            next_stage = stage_rotate_keys()
        elif current_stage == 'Quit':
            print("Thanks for using this tool! Buy me a coffee!☕")
            break
        elif current_stage == "Remove Profile":
            next_stage = stage_remove_user()


        if next_stage == 'back':
            if history:
                current_stage = history.pop()
            else:
                current_stage = "main_menu"
        else:
            history.append(current_stage)
            current_stage = next_stage

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError, SelectionAborted):
        print("Operation cancelled by user. Exiting.")
        sys.exit(0)
