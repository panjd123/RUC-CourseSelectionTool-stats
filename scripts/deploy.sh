#!/bin/bash

python3 -m venv venv
venv/bin/python3 -m pip install -r requirements.txt
venv/bin/python3 main.py
