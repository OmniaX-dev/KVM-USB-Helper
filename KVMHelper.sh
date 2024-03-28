#!/bin/bash

export SUDO_ASKPASS=./askpass.sh
sudo -A python KVMHelper.py $USER
