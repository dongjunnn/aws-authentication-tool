#!/bin/bash
# eval $(./aws-auth.py)

./src/aws-auth.py

# export commands saved to this file and then removed
# source /tmp/aws_env_vars888.sh
# rm /tmp/aws_env_vars888.sh

if [ -f "/tmp/aws_env_vars888.sh" ]; then
    source /tmp/aws_env_vars888.sh
    rm /tmp/aws_env_vars888.sh
    # echo "AWS environment variables set and temporary file removed."
fi