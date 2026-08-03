.. rms-hst-targets documentation master file

rms-hst-targets
===============

Identify the small-body moving targets of Hubble Space Telescope observations —
comets, asteroids, Centaurs, trans-Neptunian objects, dwarf planets, and the
standard planets and satellites — from the target-description keywords of their
SPT/SHF support-file headers.

Maintained by the `RMS Node <https://pds-rings.seti.org>`_ of the NASA
Planetary Data System at the SETI Institute.

``identify_targets()`` is the entry point: give it SPT/SHF headers, get back the
PDS4 Target context product for each body observed. It is a core stage of the
RMS Node's ``rms-hst-pipeline``, which is what this package exists to serve.

.. code-block:: python

   from astropy.io import fits
   from targets import identify_targets

   with fits.open('u6ht4501m_shm.fits') as hdul:
       paths = identify_targets([hdul[0].header])

   for path in paths:
       print(path.name)
   # asteroid.523955_1998_uu43_1.0.xml

The headers may span any number of visits; they are grouped and identified one
visit at a time. ``lids_from_target_paths()`` turns the returned paths into the
PDS4 logical identifiers of those products, which is what a label referencing
them needs. ``identify_target_dicts()`` is the lower-level form, returning the
body dictionaries instead of context-product paths.

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
