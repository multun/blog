---------------------------------------
Software and Linear referencing systems
---------------------------------------
:date: 2023-01-15
:slug: lrs
:trans_id: lrs
:lang: en
:status: draft
:category: railway

Even if you do not know what a `linear referencing system <https://en.wikipedia.org/wiki/Linear_referencing>`_ is,
you probably have encountered one before: alongside roads, pipelines,
power lines and railways, mile markers or kilometer posts help users
and workers name locations.

This article is intended to help software engineers wrap their head around
how to deal with linear referencing systems.

Each linear referencing system really is some kind of giant
ruler, bending and twisting along a **linear feature**.

An LRS address looks something like ``foo+215``, or ``12-320``:

- ``foo`` and ``12`` are **fixed point** identifiers (like the mile / kilometer marker / post)
- ``+215`` and ``-320`` are **offsets** from the fixed point

Fixed points are physically installed during construction, and pretty
much never moved or renamed.

.. image:: {attach}images/lrs-fixed-point.svg
   :width: 100%

When dealing with linear infrastructure, LRS help tremendously:

- an LRS can used to reliably compute distances along the linear feature, which can't really be done with GPS
- almost everything can be engineered, built and maintained within this frame of reference
- it can be used to associate attributes with infrastructure

Hierarchical referencing systems
================================

Consider a railway line with multiple parallel tracks. If tracks had entirely
separate referencing systems, as the line turns, addresses on the
outer track will become higher than addresses on the inner track.

.. image:: {attach}images/lrs-drift.svg
   :width: 100%

To mitigate this issue, fixed points can be shared between the line and its tracks.
This way, addresses stay somewhat close to each other along the line:

.. image:: {attach}images/lrs-shared-fixed-points.svg
   :width: 100%

Offsets still drift out of sync, but get synchronized back at each fixed point.

There is still one last issue: how are *line addresses mapped to track addresses* and back?
It's kind of a big deal, as it enables locating things on all of the line's tracks at once,
such as bridges, tunnels or crossings.

There are a few ways this can be done:

1) use line addresses as track addresses, and the other way around. It can be pretty imprecise.
2) scale offsets in proportion to the size of sections between fixed points: ``new_offset = old_offset * new_section_len / old_section_len``
3) if higher precision is needed, line sections between fixed points can be further subdivided.
   The range of offset each subsection spans then has to be kept track of in a database.
   Offsets can then be scaled proportionally inside each subsection.


Computing distances between addresses
=====================================

The **basic** algorithm for computing the distance between ``a+x`` and ``b+y`` is as follows:

- start with the **distance between fixed points** ``a`` and ``b``
- substract offset ``x``
- add offset ``y``

The first step of the algorithm is to find out how far ``a`` is from ``b``. Most of the time,
there needs to be some kind of database which keeps track of the order and distance between fixed
point in linear features. One notable exception is when fixed point are spaced regularly
*along the linear feature* [#hierarchical-lrs]_.


Anomalies
~~~~~~~~~

Anomalies are exception to the usual algorithm for computing distances along an LRS.
They can be introduced as a result of changes that disrupt the linear feature,
such as sections being replaced by others of a different length (such as when creating a bypass).

There are two kind of anomalies [#line-track-anomalies]_:

- fixed point anomalies, where otherwise evenly spaced fixed points are not.
  These can only happen when fixed points are evenly spaced in the first place.
- offsets anomalies, where the offset address space has a gap: ``+1 +2 +8 +9``


Case study: SNCF Réseau
=======================

As this blog post is related to my work at SNCF Réseau, the french railway infrastructure manager,
I thought I could share a practical example of how things are implemented there:

- fixeds point are numbered sequentially from the start of the line up [#sncf-named-fixed-points]_
- devices are given an address relative to the previous fixed point [#sncf-neg-pk]_
- one fixed point is built per kilometer [#sncf-named-fixed-points]_
- when a line has multiple tracks, fixed points are shared by tracks in a hierarchical referencing system [#sncf-standalone-track-lrs]_

Interestingly, every single one of these rules has exceptions, relics of the past haunting
misinformed software engineers.


Jargon
~~~~~~

LRS
  Système de repérage

Fixed point
  Répère Kilométrique (RK)

LRS Address
  Point Kilométrique (PK)


.. [#hierarchical-lrs] It does not work if fixed points are spaced regularly along the
		       center line of a train line which has multiple tracks.

.. [#line-track-anomalies] SNCF Réseau also counts the length difference of sections inside a hierarchical LRS as anomalies

.. [#sncf-neg-pk] When there is no previous fixed point, addresses are negative offsets from the next fixed point

.. [#sncf-named-fixed-points] Except one line, which has fixed points identified using letters, which are not evenly spaced either

.. [#sncf-standalone-track-lrs] Some tracks have a LRS that is separate from the line they belong to
