#!/bin/bash

export ACISPY=/data/odin/BACKUPS/jzuhone/python/

PATH=${ACISPY}/bin:$PATH

if [ -z $PYTHONPATH ]; then
    export PYTHONPATH=${ACISPY}/lib/python2.7/site-packages
else
    export PYTHONPATH=${ACISPY}/lib/python2.7/site-packages:$PYTHONPATH
fi