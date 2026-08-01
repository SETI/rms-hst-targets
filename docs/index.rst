.. rms-hst-targets documentation master file

rms-hst-targets
===============

Identify the small-body moving targets of Hubble Space Telescope observations —
comets, asteroids, Centaurs, trans-Neptunian objects, dwarf planets, and the
standard planets and satellites — from the target-description keywords of their
SPT/SHF support-file headers.

Maintained by the `RMS Node <https://pds-rings.seti.org>`_ of the NASA
Planetary Data System at the SETI Institute. Early-stage / work in progress.

.. code-block:: python

   from astropy.io import fits
   from targets import identify_target_dicts

   with fits.open('u6ht4501m_shm.fits') as hdul:
       bodies = identify_target_dicts([hdul[0].header])

   for body in bodies:
       print(body['full_name'], body['ttype'], body['naif_id'])
   # (523955) 1998 UU43 T 2523955

Guides
------

.. toctree::
   :maxdepth: 2

   using-identify-targets
   how-it-works
   handling-identification-failures
   data-and-caches
   data-tables
   programs

API reference
-------------

.. toctree::
   :maxdepth: 2

   module

Project
-------

.. toctree::
   :maxdepth: 1

   contributing
   code_of_conduct

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
