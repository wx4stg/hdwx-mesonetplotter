#!/bin/bash

if [ -f ../config.txt ]
then
    source ../config.txt
else
    condaEnvName="HDWX"
fi
echo "Mesonetting"
if [ -f $condaRootPath/envs/$condaEnvName/bin/python3 ]
then
    $condaRootPath/envs/$condaEnvName/bin/python3 mesoplot.py
fi
