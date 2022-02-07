#!/bin/bash

echo "Mesonetting"
if [ -f ~/mambaforge/envs/HDWX/bin/python3 ]
then
    ~/mambaforge/envs/HDWX/bin/python3 mesoplot.py
fi
if [ -f ~/miniconda3/envs/HDWX/bin/python3 ]
then
    ~/miniconda3/envs/HDWX/bin/python3 mesoplot.py
fi
