-----------------------------
The Curse of Data Versionning
-----------------------------
:date: 2022-12-28
:slug: curse-of-data-versionning
:trans_id: curse-of-data-versionning
:lang: en
:status: draft
:category: software

:tags: databases, programming


Just like software developpers need to collaborate around code, many more other jobs rely on collaborating around data.
But somehow, only developpers ever got appropriate tools for the job, such as Git or Mercurial:

- code changes can be reviewed prior to integration
- code changes can be developped and tested without disturbing the main working copy
- code version control tools keep track of which change introduced any given line of code

Why is that, and what does it take to make it change?

Features of version control software
====================================

Part of what makes data versioning hard is how diverse requirements are:


Branches versionning
  Does the versionning system support some equivalent of Git branches?

Branch merging with conflict resolution
  Can a branch be merged into another while giving the opportunity to resolve ambiguities?

Conflict resolution time
  When a conflict occurs, does it have to be disambiguated right now, or can it wait?
  If it can wait, can other conflicts occur and be added to the "waiting list"?

Granularity of conflict resolution
  Are conflict between files? Between lines, or even bytes?

Attribution granularity
  How precisely can part of a file be traced back to a change? Is it by line, by byte or even file?

Conflict resolution attribution
  When a conflict is disambiguated, is it a new change which can receive attribution?

Real world time versionning
  Consider a repository which stores a description of real-world objects,
  where changes are linked to construction work, which happens at a real-world time.

  Does the repository only store the state of things at the current real-world time,
  or does have the full timeline?

  If the repository contains the full timeline, there is both:

  - a history of changes over real world time, which can be filtered to display the
    state of the repository at a given date
  - the history of changes over development time (the change log)


The great database - version control rift
=========================================

When the matter of versionning data is first brought up with someone, this is often
the first reaction: "Aren't there databases that fit the bill?"

Databases:

- are used to query data
- are expected to be very fast
- often work with table data

Version control softwares:

- mostly are not used to query data
- are expected to keep track of a bunch of metadata
- often rely on slow graph algorithms, or the ability to deduplicate data using merkle trees
- often rely on interactive operations, such as conflict resolution

Sure, having a version-controlled database would be great, provided that someone is able to reconcile these requirements. I wouldn't be too optimistic: making good databases or version control system are hard enough on their own.

Instead, databases can be paired with version control systems:

- successful changes in the VCS are applied to the database
- queries can be 


State of the art of code versionning
====================================

TODO: Git won. Versions per file, conflict resolution with diffing. Issues around conflict resolution: lost ownership of conflicting lines.

Previous attempts at data versionning
=====================================

- noms
- dolt
- pijul


A way out
=========

Single file CRDT
----------------

Multi-file CRDT
---------------

Bonus: time versionning
-----------------------
