API reference
=============

The importable package is ``targets``. The entry point is
:func:`~targets.identify_targets.identify_targets`, which takes SPT/SHF headers
spanning any number of visits and returns the path of each target's PDS4 context
product; :func:`~targets.identify_targets.lids_from_target_paths` converts those
paths to the logical identifiers of the products.
:func:`~targets.identify_targets.identify_target_dicts` is the lower-level form
beneath it: one visit at a time, returning the body dictionaries themselves
rather than context products. The remaining modules implement the stages they
orchestrate.

Top-level identification
------------------------

.. automodule:: targets.identify_targets
   :members:
   :member-order: bysource

.. automodule:: targets.identify_standard_body
   :members:
   :member-order: bysource

Comets and minor planets
------------------------

.. automodule:: targets.comet_identifiers
   :members:
   :member-order: bysource

.. automodule:: targets.minor_planet_identifiers
   :members:
   :member-order: bysource

.. automodule:: targets.categorize_minor_planet
   :members:
   :member-order: bysource

String repair and standard bodies
---------------------------------

.. automodule:: targets.hst_repairs
   :members:
   :member-order: bysource

.. automodule:: targets.standard_bodies
   :members:
   :member-order: bysource

Context products
----------------

.. automodule:: targets.target_xml_support
   :members:
   :member-order: bysource

.. automodule:: targets.target_xml_cache_support
   :members:
   :member-order: bysource

Astrometry and helpers
----------------------

.. automodule:: targets.orbital_radec
   :members:
   :member-order: bysource

.. automodule:: targets.targettype
   :members:
   :member-order: bysource

.. automodule:: targets.roman
   :members:
   :member-order: bysource

Databases and external queries
------------------------------

.. automodule:: targets.cometdb
   :members:
   :member-order: bysource

.. automodule:: targets.mpc_tools
   :members:
   :member-order: bysource
