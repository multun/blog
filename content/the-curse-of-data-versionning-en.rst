-----------------------------
The Curse of Data Versionning
-----------------------------
:date: 2022-12-28
:slug: curse-of-data-versionning
:trans_id: curse-of-data-versionning
:lang: en
:category: programming
:tags: databases, programming


Just like software developpers need to collaborate around code, many more other jobs rely on collaborating around data.
But somehow, only developpers get appropriate tools for the job, such as Git or Mercurial:
- code changes can be reviewed prior to integration
- code changes can be developped and tested without disturbing the main working copy
- code version control tools keep track of which change introduced any given line of code

Why is that, and what does it take to make it change?

State of the art of code versionning
====================================

TODO: Git won. Versions per file, conflict resolution with diffing. Issues around conflict resolution: lost ownership of conflicting lines.


What data versionning takes
===========================

- file format flexibility
- delayed conflict resolution
- fine-grained attribution

Previous attempts at data versionning
=====================================

- noms
- dolt
- pijul

Requirements for a usable data versionning tool
===============================================


A way out
=========

Single file CRDT
----------------

Multi-file CRDT
---------------

Bonus: time versionning
-----------------------
