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

home = expanduser("~")
config = configparser.ConfigParser()
awsCredFile = '%s/.aws/credentials' % (home)
config.read(awsCredFile)

# Helper function to handle input prompts correctly when using eval
def get_input(prompt):
    # print(prompt, end='')
    # sys.stderr.flush()
    # return sys.stdin.readline().strip()
    return input(prompt).strip()

def stage_main_menu():
    menu = ["Activate Profile (Get Token)", "Add New Profile", "Remove Profile","Quit"]
    choice = enquiries.choose("Action:", menu)
    if choice == "Activate Profile (Get Token)":
        return "Activate Profile (Get Token)"
    if choice == "Add New Profile":
        return "Add New Profile"
    if choice == "Quit":
        return "Quit"
    if choice == "Remove Profile":
        return "Remove Profile"

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
            response = sts_client.get_session_token(
                SerialNumber=mfa_serial_arn,
                TokenCode=totp
            )
            credentials = response['Credentials']

            print(green("\nCredentials obtained successfully!"))
            print(f"Expiration: {credentials['Expiration']}")

            # print(f"AccessKeyId: {credentials['AccessKeyId']}")
            # print("TEST")
            # print(f"SecretAccessKey: {credentials['SecretAccessKey']}")
            # print(f"SessionToken: {credentials['SessionToken']}")
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
                        
            return "Quit"
        else:
            return "back"
    except Exception as e:
        print(red("\nAn error occurred!"))
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
                print(green(f"\nSuccess! Profile '{choice}' was removed from {awsCredFile}"))
            except Exception as e:
                print(red(f"\nError writing to credentials file: {e}"))
        else:
            print("Removal cancelled.")
    return "back"

def validate_credentials_directly(access_key, secret_key, mfa_serial=None, mfa_token_secret=None):
    print(cyan("\nValidating credentials with AWS before saving..."))
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
        print(red("\nValidation Failed: The MFA Token Secret is not a valid Base32 string."))
        return False
    except Exception as e:
        print(red(f"\nValidation Failed: {e}"))
        return False
    
def stage_add_user():
    print("--- Add New AWS Profile ---")
    
    profile_name = get_input("Enter a unique name for this profile: ")
    if not profile_name:
        print(red("\nProfile name cannot be empty."))
        get_input("Press Enter to return.")
        return "main_menu"

    access_key = get_input("Enter AWS Access Key ID: ")
    secret_key = get_input("Enter AWS Secret Access Key: ")
    mfa_serial = get_input("Enter MFA Serial/ARN: ")
    mfa_token = ""
    if mfa_serial:
        mfa_token = get_input("Enter MFA Token Secret: ")
    
    if not validate_credentials_directly(access_key, secret_key, mfa_serial, mfa_token):
        print(red("\nCredentials could not be validated and were not saved."))
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
        print(green(f"\nSuccess! Profile '{profile_name}' was added to {awsCredFile}"))
    except Exception as e:
        print(red(f"\nError writing to credentials file: {e}"))

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
        elif current_stage == 'Quit':
            print("\nThanks for using this tool! Buy me a coffee!☕")
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
        print("\nOperation cancelled by user. Exiting.")
        sys.exit(0)
