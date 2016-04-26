.. _what-data:

What Data Can I Work With?
==========================

ACISpy uses the Ska Python tools to work with data from the engineering archive and 
the commanded states database. It can also work with predicted quantities from thermal 
models and tracelog files produced by tools such as `ACORN <http://cxc.cfa.harvard.edu/acis/memos/Dump_Acorn.html>`_ 
or the `MIT tools <http://cxc.cfa.harvard.edu/acis/memos/Dump_Psci.html>`_. 

This page gives a broad outline of what ACIS-related data ACISpy can work with. To learn 
the specific ways of loading and plotting the data, consult :ref:`loading-data` and 
:ref:`plotting-data`.

Commanded States
----------------

Commanded states (such as pitch angle, roll, obsid, CCD count, etc.) can be loaded from
the commanded states database or from thermal model predictions. A list of the commanded
states understood by ACISpy can be found `here <http://cxc.cfa.harvard.edu/mta/ASPECT/tool_doc/cmd_states/#cmd-states-table>`_.
Additionally, ACISpy computes the off-nominal roll from the attitude and stores it as
``"off_nominal_roll"`` along with the other commanded states. 

MSIDs
-----

These consist of engineering telemetry from the start of the mission. The ones most
relevant to ACIS operations can be found on the real-time telemetry pages, such as the 
real-time page on `acis60-v <http://hea-www.cfa.harvard.edu/~acisweb/htdocs/acis/RT-ACIS60-V/acis-mean.html>`_. 

Pseudo-MSIDs
------------

These are quantities that are not part of the engineering telemetry stream but are
nevertheless important to ACIS operations, primarily the ACIS DEA housekeeping data.
A list of the quantities stored in the Ska archive and understood by ACISpy can be 
found `here <http://cxc.cfa.harvard.edu/mta/ASPECT/tool_doc/eng_archive/pseudo_msids.html#acis-dea-housekeeping>`_.

Model Components
----------------

ACISpy can also work with predicted model data for specific temperature components,
found `here <http://cxc.cfa.harvard.edu/acis/Thermal/>`_.