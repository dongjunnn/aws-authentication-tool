#! /usr/bin/python3

import configparser
import json
import os
import argparse
import enquiries
# import pyotp
from os.path import expanduser
from curtsies.fmtfuncs import red, bold, green, on_blue, yellow, cyan
import sys
import time
import threading
import enquiries

home = expanduser("~")
config = configparser.ConfigParser()
awsCredFile = '%s/.aws/credentials' % (home)
config.read(awsCredFile)


menu = ["login", "add user", "QUIT"]
choice = enquiries.choose("action:", menu)




def stage_main_menu():
    menu = ["choose-user", "add-user", "QUIT"]
    choice = enquiries.choose("action:", menu)
    if choice == "choose-user":
        return "choose-user"
    if choice == "add-user":
        return "add-user"
    if choice == "QUIT":
        return "QUIT"

def stage_choose_user():
    users = config.sections()
    if not users:
        print("No users found. Please add a user first.")
        return "add-user"
    
    choice = enquiries.choose("Choose a user:", users)
    if choice:
        print(f"You selected: {choice}")
        return "user_selected"
    else:
        return "back"

def stage_add_user():
    # aws IAM user creation logic
    print("Adding a new user...")
    username = input("Enter the new user's name: ")
    clear_screen()
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
    mfa_serial = input("Enter MFA Serial/ARN (optional, press Enter to skip): ")
    mfa_token = ""
    if mfa_serial:
        mfa_token = input("Enter MFA Token Secret for pyotp (optional): ")

    # Add the new section and its key-value pairs to the config object
    config.add_section(profile_name)
    config.set(profile_name, 'aws_access_key_id', access_key)
    config.set(profile_name, 'aws_secret_access_key', secret_key)
    if mfa_serial:
        config.set(profile_name, 'mfa_serial', mfa_serial)
    if mfa_token:
        # This is the custom field for your pyotp logic
        config.set(profile_name, 'mfa_token', mfa_token)

    # Write the updated configuration back to the file
    try:
        with open(awsCredFile, 'w') as configfile:
            config.write(configfile)
        print(f"\nSuccess! Profile '{profile_name}' was added to {awsCredFile}")
    except Exception as e:
        print(f"\nError writing to credentials file: {e}")

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
        if next_stage == 'back':
            if history: 
                current_stage = history.pop()
        else:
            history.append(current_stage)
            current_stage = next_stage

    return 0

main()