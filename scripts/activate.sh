#!/bin/bash

export ACISPY=/home/acisdude/python/
export SKA=/ska

PATH=${ACISPY}/bin:$PATH

#if [ -z $PYTHONPATH ]; then
#    export PYTHONPATH=${ACISPY}/lib/python2.7/site-packages
#else
#    export PYTHONPATH=${ACISPY}/lib/python2.7/site-packages:$PYTHONPATH
#fi