#!/bin/bash

if [ -f ../config.txt ]
then
    source ../config.txt
else
    condaEnvName="HDWX"
fi
echo "Mesonetting"
if [ -f ~/mambaforge/envs/$condaEnvName/bin/python3 ]
then
    ~/mambaforge/envs/$condaEnvName/bin/python3 mesoplot.py
fi
if [ -f ~/miniconda3/envs/$condaEnvName/bin/python3 ]
then
    ~/miniconda3/envs/$condaEnvName/bin/python3 mesoplot.py
fi
