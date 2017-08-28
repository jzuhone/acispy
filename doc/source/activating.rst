.. _activating:

Activating ACISpy
=================

.. warning::

    ACISpy and the Ska3 environment associated with it are currently not 
    approved for flight, and only the official, flight-approved Ska 
    environment and its associated packages should be used for conducting
    load reviews, etc.

On the HEAD LAN, ACISpy is installed into the ACIS Ops Ska3 Python stack at
``/data/acis/ska3``. If you are logged on as ``acisdude``, all you need to
do is issue the command ``setska3`` and this Python stack and ACISpy will be
loaded into your environment. 

However, if you would like activate this stack and ACISpy from your own user
account, add the following alias to your ``.bashrc`` if you are using the Bash
shell (or a variant):

.. code-block:: bash

    ska3 () {
        PATH=/data/acis/ska3/bin:${PATH}
        export SKA=/proj/sot/ska
        PS1="[ska3:\u@\h \W]\$ "
    }

Or, if you are a mascohist or are otherwise compelled to use the C shell or a 
variant of it, add this alias to your ``.cshrc.user``:

.. code-block:: bash
   
    alias ska3 'set path = (/data/acis/ska3/bin $path); \
      	        setenv SKA /proj/sot/ska; \
	            set prompt = "(ska3) %m.%n:%c[%h]> "' 

.. warning::

    ACISpy should be used in a "clean" terminal window where you are not trying
    to do anything else (i.e., load reviews, SACGS) as setting up the Ska3 
    environment messes with environment variables and paths. 