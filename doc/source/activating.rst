Activating ACISpy
=================

From anywhere on the HEAD LAN, source the activation script for ACISpy:

bash:

.. code-block:: bash
   
   [~]$ source /home/acisdude/python/bin/activate.sh
   
tcsh:

.. code-block:: bash
   
   [~]$ source /home/acisdude/python/bin/activate.csh

.. warning::

    This should be done in a "clean" terminal window where you are not trying
    to do anything else (i.e., load reviews, SACGS) as sourcing these scripts
    activates the ska environment and messes with environment variables and
    paths. 