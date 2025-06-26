## #! /usr/bin/python3

import configparser
import os
import enquiries
import pyotp
from os.path import expanduser
from curtsies.fmtfuncs import red, bold, green, on_blue, yellow, cyan
import enquiries
import boto3
import binascii

home = expanduser("~")
config = configparser.ConfigParser()
awsCredFile = '%s/.aws/credentials' % (home)
config.read(awsCredFile)

def stage_main_menu():
    menu = ["choose-user", "add-user", "QUIT", "remove-user"]
    choice = enquiries.choose("action:", menu)
    if choice == "choose-user":
        return "choose-user"
    if choice == "add-user":
        return "add-user"
    if choice == "QUIT":
        return "QUIT"
    if choice == "remove-user":
        return "remove-user"

def stage_choose_user():
    users = config.sections()
    if not users:
        print(red("No users found. Please add a user first."))
        return "main_menu"
    
    choice = enquiries.choose("Choose a user:", users)
    try:
        if choice:
            print(f"You selected: {choice}")
            # $ aws sts get-session-token --serial-number arn-of-the-mfa-device --token-code code-from-token
            mfa_serial_arn = config[choice]['mfa_serial_arn']
            token = config[choice]['mfa_token']
            totp = pyotp.TOTP(token).now()
            session = boto3.Session(profile_name=choice)
            sts_client = session.client('sts')
            response = sts_client.get_session_token(
                SerialNumber=mfa_serial_arn,
                TokenCode=totp
            )
            credentials = response['Credentials']
            # export AWS_ACCESS_KEY_ID=example-access-key-as-in-previous-output
            # export AWS_SECRET_ACCESS_KEY=example-secret-access-key-as-in-previous-output
            # export AWS_SESSION_TOKEN=example-session-token-as-in-previous-output
            print(f"Access Key ID: {credentials['AccessKeyId']}")
            print(f"Secret Access Key: {credentials['SecretAccessKey']}")
            print(f"Session Token: {credentials['SessionToken']}")
            print(f"Expiration: {credentials['Expiration']}")
            os.environ['AWS_ACCESS_KEY_ID'] = credentials['AccessKeyId']
            os.environ['AWS_SECRET_ACCESS_KEY'] = credentials['SecretAccessKey']
            os.environ['AWS_SESSION_TOKEN'] = credentials['SessionToken']
            return "QUIT"
        else:
            return "back"
    # never bother catching
    except Exception as e:
        print(red("Credentials are invalid!"))
        print(red(f"Error: {e}"))
        return "main_menu"
    
def stage_remove_user():
    # clear_screen()
    users = config.sections()
    if not users:
        print("No users found. Please add a user first.")
        return "back"
    
    choice = enquiries.choose("Choose a user to remove:", users)
    if choice:
        confirm = input(f"Are you sure you want to remove the profile '{choice}'? (y/n): ")
        if confirm.lower() == 'y':
            config.remove_section(choice)
            try:
                with open(awsCredFile, 'w') as configfile:
                    config.write(configfile)
                print(f"\nSuccess! Profile '{choice}' was removed from {awsCredFile}")
            except Exception as e:
                print(f"\nError writing to credentials file: {e}")
        else:
            print("Removal cancelled.")
    return "back"

def validate_credentials_directly(access_key, secret_key, mfa_serial=None, mfa_token_secret=None):
    print(cyan("\nValidating credentials with AWS before saving..."))
    try:
        # For MFA, we must validate the secret key format first.
        if  not mfa_serial or not mfa_token_secret:
                return False

        # Handle MFA validation
        totp = pyotp.TOTP(mfa_token_secret).now()
        print("MFA secret key format is valid. Now checking with AWS...")
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
  
    # clear_screen()
    print("--- Add New AWS Profile ---")
    

    profile_name = input("Enter a unique name for this profile: ")
    if not profile_name:
        print("\nProfile name cannot be empty.")
        input("Press Enter to return.")
        return "main_menu"

    # Gather the required AWS credentials
    access_key = input("Enter AWS Access Key ID: ")
    secret_key = input("Enter AWS Secret Access Key: ")
    
    # Ask for optional MFA details
    mfa_serial = input("Enter MFA Serial/ARN: ")
    mfa_token = ""
    if mfa_serial:
        mfa_token = input("Enter MFA Token Secret: ")

    
    if  not validate_credentials_directly(access_key, secret_key, mfa_serial, mfa_token):
        print(red("\nCredentials are invalid!"))
        return "main_menu"
     
        
    # Add the new section and its key-value pairs to the config object
    config.add_section(profile_name)
    config.set(profile_name, 'aws_access_key_id', access_key)
    config.set(profile_name, 'aws_secret_access_key', secret_key)    
    config.set(profile_name, 'mfa_serial_arn', mfa_serial)
    config.set(profile_name, 'mfa_token', mfa_token)

    # Write the updated configuration back to the file
    try:
        with open(awsCredFile, 'w') as configfile:
            config.write(configfile)
        print(f"Success! Profile '{profile_name}' was added to {awsCredFile}")
    except Exception as e:
        print(f"Error writing to credentials file: {e}")

    input("Press Enter to return to the main menu...")
    return "main_menu"

def show_menu(menu, title):
    menu.append("exit")
    choice = enquiries.choose(title, menu)
    print(choice)
    return choice


# state machine
def main():
    history = []
    current_stage = "main_menu"

    while True:
        if current_stage == "main_menu":
            next_stage = stage_main_menu()
        if current_stage == "choose-user":
            next_stage = stage_choose_user()
        if current_stage == "add-user":
            next_stage = stage_add_user()
        if next_stage == 'QUIT':
            print("Thanks for using this tool!")
            break 
        if current_stage == "remove-user":
            next_stage = stage_remove_user()
        if next_stage == 'back':
            if history: 
                current_stage = history.pop()
        else:
            history.append(current_stage)
            current_stage = next_stage

    return 0

main()