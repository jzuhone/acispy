#!/bin/tcsh

setenv ACISPY /home/acisdude/python/
setenv SKA /proj/sot/ska

set path = (${ACISPY}/bin $path)

#if (! $?PYTHONPATH) then       
#  setenv PYTHONPATH ${ACISPY}/lib/python2.7/site-packages
#else
#  setenv PYTHONPATH ${ACISPY}/lib/python2.7/site-packages:$PYTHONPATH
#endif

