#!/bin/tcsh

setenv ACISPY /data/odin/BACKUPS/jzuhone/python/

set path = (${ACISPY}/bin $path)

if (! $?PYTHONPATH) then       
  setenv PYTHONPATH ${ACISPY}/lib/python2.7/site-packages
else
  setenv PYTHONPATH ${ACISPY}/lib/python2.7/site-packages:$PYTHONPATH
endif

