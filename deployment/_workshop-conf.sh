#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

## Defines workshop configuration shared amongst scripts

## Variables
WORKSHOP_ID=""
WORKSHOP_NAME="MultitenantLakehouse"$WORKSHOP_ID
REPO_NAME="multi-tenant-lakehouse"
PARTICIPANT_VSCODE_SERVER_PROFILE_PARAMETER_NAME="multitenantlakehouseworkshopvscodepartipantrole"
TARGET_USER="ec2-user"
DELAY=15 # Used to sleep in functions. Tweak as desired.
