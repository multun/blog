---------------------------------------
Software and linear referencing systems
---------------------------------------
:date: 2023-01-15
:slug: software-lrs
:trans_id: software-lrs
:lang: en
:status: draft
:category: railway

Even if you do not know what a `linear referencing system <https://en.wikipedia.org/wiki/Linear_referencing>`_ is,
you probably have encountered one before: alongside roads, pipelines,
power lines and railways, mile markers or kilometer posts help users
and workers name locations.

Each linear referencing system really is some kind of giant
ruler, bending and twisting along a linear element.

An LRS addresse looks something like that: ``42+15``

- 42 is a fixed point identifier (like the mile / kilometer marker / post)
- +15 is an offset from the fixed point

Fixed points are physically installed during construction, and pretty
much never moved or renamed.

When dealing with linear infrastructure, LRS help tremendously:
- an LRS can used to reliably compute distances along the linear element, which can't really be done with GPS
- almost everything can be engineered, built and maintained within this frame of reference


Why it's harder than it seems
=============================

In practice, referencing systems are a pain.

Anomalies
~~~~~~~~~

In practice, you usually can't compute the distance between two
locations using just their addresses, because the address space has:

- gaps: ``a b      c d``
- cuts: ``a b e f``

An anomaly is defined as any gap or cut in an LRS. There are two main
ways anomalies can be introduced: hierarchical referencing systems,
and linear element changes.

Hierarchical referencing systems
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Consider a line with multiple parallel tracks. If each track
had entirely separate referencing systems, as the line turns, addresses
on the outer track will become higher than addresses on the inner
track.

If you were standing in the middle of these two tracks, there
would be a major misalignment between track addresses at this point,
even if addresses were aligned back at the beginning of the line.

Instead of just accepting this geometrical reality, some linear
referencing systems try to keep track addresses in sync as the line
turns. A fairly easy way to do so would be to regularly sync up tracks
by introducing anomalies. As a result, any location on the line has
kind of (but not really) aligned addresses on each track.

Mapping line to track addresses
###############################

Sometimes, a track uses a positioning system entirely separate from
its line. Then, a bi-directional mapping from line to track positioning
systems has to be defined.

In the SNCF case, each valid range in the track positioning system
has a defined mapping to an address range on the line positioning
system. Addresses on line and track referencing systems are converted
back and forth proportionaly.

Linear element changes
~~~~~~~~~~~~~~~~~~~~~~

When devices are installed along tracks, they are labelled
with their LRS location. When there are many such devices, changing
the address of devices becomes expensive, and thus usually avoided.

Sometimes, changes that would disrupt the LRS have to be made:
As the rail network evolves, sections of track are replaced by
others, which may not have the same length (such as when creating
a bypass).

Such changes introduce dilemma:

- either re-number devices whose address changed
- introduce an anomaly in the LRS address space

Resolving device locations
~~~~~~~~~~~~~~~~~~~~~~~~~~

Finding out where a device physically is using its LRS address is
harder than it seems. Let's assume your rail network is divided into
sections of tracks. You have a database or track sections, with
their length and geometry.

You are given an LRS along with the address of a device, and tasked
to figure out where that is. How does that work?

- if the LRS is a line LRS, the line address needs to be converted
  into a list of track addresses
- first, you need to find all track sections which belong to
  the LRS, along with their begin and end addresses at that time
- then, you need to find what track sections your address falls
  into, by comparing begin and end addresses
- finally, you need to compute the distance between the start
  address of the track section and the address of your device,
  taking anomalies into account.

Several things can go wrong:

- you may find out that your address has either too many or zero
  corresponding track sections
- the distance between the begin and end addresses of your track section
  could be different from its actual length

The french railway LRS
======================

LRS
  Système de repérage

LRS Address
  Point Kilométrique (PK)

Fixed point
  Répère Kilométrique (RK)

When a new line is built, one fixed point is built per kilometer,
and devices are given an address relative to the previous fixed point [#neg-pk]_.

.. [#neg-pk] When there is no previous fixed point, addresses are negative offsets from the next fixed point
