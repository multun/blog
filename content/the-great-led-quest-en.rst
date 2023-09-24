-------------------
The great LED quest
-------------------
:date: 2023-08-21
:slug: great-led-quest
:trans_id: great-led-quest
:lang: en
:category: software
:status: draft
:tags: reverse engineering


.. figure:: {attach}images/corsair-vengeance-led.avif
   :width: 60%
   :alt: A picture of the damn memory module

   A 8Gig Corsair vengeance white LED module, also known as `CMU16GX4M2A2666C16 <https://www.corsair.com/us/en/p/memory/cmu16gx4m2a2666c16/vengeancea-led-16gb-2-x-8gb-ddr4-dram-2666mhz-c16-memory-kit-white-led-cmu16gx4m2a2666c16>`_


I bought a second hand computer, which came with LED-equipped memory modules.
I didn't think much of it, until I realized that without a driver,
the LEDs blink non stop, even when the computer is suspended.

This is pretty distracting, especially when trying to sleep.

Instead of going the logical route, and just slapping on some black tape,
I decided to port the existing windows driver to linux.

When I started this project, I figured it would go smoothly: how much code
does driving LEDs take?

Well, a **FUCKTON more than I tought**.

iCUE, the window driver package for this memory module, features:

- ~100Mo of Qt C++ for the main binary, excluding Qt libs
- ~200MB of Qt UI plugins
- ~500MB of C++ device drivers
- ~10MB of C# device drivers, which run in a separate service
- 3 services for interacting with memory modules

This is the story of my deep dive into this pool of spaghetti.

.. contents:: Table of contents

========================
All about memory modules
========================

When I first started this project, I had questions:

- how does the windows LED-blinker driver communicate with the memory module?
- how does the system know what memory modules are installed?

It turns out these questions share a common answer: all modern memory modules,
from SDRAM to DDR5, aren't just a collection of memory modules. They all have
an extra chip, dubbed `Serial Presence Detect <https://en.wikipedia.org/wiki/Serial_presence_detect>`_.

The SPD chip stores a bunch of data about memory modules: size, type, brand, timing and refresh details,
serial number, and more. It might also monitor temperature, or drive LEDs.

The SPDs of all installed memory modules are connected to an `SMBus <https://docs.kernel.org/i2c/smbus-protocol.html>`__,
a type of serial bus compatible with i2c.

.. include:: smbus-architecture-diagram.txt
   :literal:
   :class: text-diagram



The SPD chip has its own separate pins on the DIMM connector:

.. include:: spd-module-diagram.txt
   :literal:
   :class: text-diagram


- it gets a 3 bit slot number, which is used to configure which SMBus addresses the module will respond on
- if the chip has a temperature probe, it can use the temperature event line to report critical events [#temp-events]_


All these lines are directly wired to pins on the DIMM connector. You can connect a logic analyzer to the
SMBus clock and data lines, and use it to reverse engineer whatever weird protocol drives these LEDs [#hindsight]_.



~~~~~~~~~~~~~~~~~~~~~~~
Reading module metadata
~~~~~~~~~~~~~~~~~~~~~~~
Instead of defining how to retrieve all stored properties over SMBus, all of it is
bundled together, and can be read over an existing ROM protocol, which itself uses on SMBus.

Over time, the protocol used to read the ROM over SMBus changed, but they're all very similar:
you have up to 8 slots on the same bus, detect which slots have a module installed, download the ROM,
decode it, and get lots of details about installed modules.

==========  ========  ========  ===============
Generation  Capacity  Protocol  Linux driver
==========  ========  ========  ===============
DDR2        128       AT24C01   eeprom or at24
DDR3        256       AT24C02   eeprom or at24
DDR4        512       EE1004    ee1004
DDR5        1024      SPD-5118  *unsupported*
==========  ========  ========  ===============

Unfortunately, Linux support for DDR4 and DDR5 SPD chips is pretty bad:

- for DDR4, the driver does not auto-detect modules, `it has to be done manually <https://www.spinics.net/lists/linux-i2c/msg32331.html>`__
- for DDR5, there's no stable driver, just a `work <https://svn.exactcode.de/t2/trunk/package/kernel/linux/spd-5118.patch>`__ in `progress <https://www.youtube.com/watch?v=tYv4XJRlRpg>`__


Once your memory module's SPD ROM is properly detected, you can decode it using ``decode-dimms``,
which comes with the ``i2c-tools`` package.

Windows support for this stuff isn't much better, so every manufacturer of fancy LED sticks
has its own custom userland drivers.




=========================
Corsair iCUE architecture
=========================

.. include:: icue-diagram.txt
   :literal:
   :class: text-diagram


===================
Reverse engineering
===================

Even though I've done quite a bit of reverse engineering work over the years, I have a few nasty habits:

- As a lot of my work was on malware, I've gotten used to doing a lot of it statically
- I really, really like reverse engineering bottom up. I don't know why, the low level stuff makes me tick

These two traits are very bad ones to have when faced with hundreds of megabytes of compiled code.

I won't go into too much detail about 
I've used a number of tools on this project:

- for the native stuff, `binaryninja <https://binary.ninja/>`_
- for C#, `ILSpy <https://github.com/icsharpcode/ILSpy>`_
- a lot of the sysinternals suite
- x64dbg, for debugging the internals of the C++ stuff
- Rohitab Batra's `API Monitor <http://www.rohitab.com/apimonitor>`_



Of course, I didn't reverse engineer all of it, but 
I ended up reverse engineering:

- a kernel driver
- a library which interacts with the kernel driver
- a service built around the library
- the protocol used by the qt front-end to communicate with the service
- csharp code which calls the same service through the qt stuff

In retrospect, of course, I could have ignored most of it.

~~~~~~~~~~~~~~~~~~~~~~~~~
The Corsair kernel driver
~~~~~~~~~~~~~~~~~~~~~~~~~

~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The low level access service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

~~~~~~~~~~~~~~~~~~~~~~~~~~
Making a protocol analyzer
~~~~~~~~~~~~~~~~~~~~~~~~~~

~~~~~~~~~~~~~~~~~~~
The C# driver stack
~~~~~~~~~~~~~~~~~~~

When writting this article, I went back to the disassembly of the C# drivers, as I
wanted to understand how the C# code interfaced with the Corsair driver stack.

To my surprise, it didn't!

- the C# code starts ``CpuIdRemote.exe``, and calls into it using a WCF RPC
- this process loads ``CpuIdWrapper.dll``, which is a wrapper over ``cpuidsdk.dll``
- ``cpuidsdk.dll`` is a commercial SDK from a company confusingly called `CPUID <https://www.cpuid-pro.com/products-system-information-kit.php>`_. It supports a *lot* of stuff, including SMBus I/O. This dll if obfuscated, probably so they can ship the same binary for clients which aren't paying for the same features.

It seems like the Corsair driver stack is bad enough that iCUE is in the process of migrating away from it.


==================
Writing the driver
==================

TODO

.. [#temp-events] The temperature event line was introduced in DDR3 DIMMs. SDR, DDR and DDR2 don't have it.
.. [#hindsight] This, of course, is what I would have done if I knew better when I started it all.
