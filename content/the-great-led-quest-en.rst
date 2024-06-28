-------------------
The great LED quest
-------------------
:date: 2023-08-21
:slug: the-great-led-quest
:trans_id: the-great-led-quest
:lang: en
:category: software
:status: draft
:tags: reverse engineering


.. figure:: {attach}images/corsair-vengeance-led.avif
   :width: 60%
   :alt: A picture of the damn memory module

   A 8Gig Corsair vengeance white LED module, aka `CMU16GX4M2A2666C16 <https://www.corsair.com/us/en/p/memory/cmu16gx4m2a2666c16/vengeancea-led-16gb-2-x-8gb-ddr4-dram-2666mhz-c16-memory-kit-white-led-cmu16gx4m2a2666c16>`_


I bought a second hand computer, which came with LED-equipped memory modules.
I didn't think much of it, until I realized that without a driver,
the LEDs blink non stop, even when the computer is suspended.

This is pretty distracting, especially when trying to sleep.

Instead of going the logical route, and just slapping on some black tape,
I decided to port the existing windows driver to linux.

I figured it would go smoothly: how much code does driving LEDs take?

Well, a **LOT more than I tought**.

iCUE, the window driver package for this memory module, features:

- ~100Mo of Qt C++ for the main binary, excluding Qt libs
- ~200MB of Qt UI plugins
- ~500MB of C++ device drivers
- ~10MB of C# device drivers, which run in a separate service
- two kernel drivers with pretty much the same feature set

This is the story of my deep dive into this huge pile of code.

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

These two traits are very bad ones to have when faced with hundreds of megabytes of compiled code. I went though:

- a kernel driver
- a library which interacts with the kernel driver
- a service built around the library
- the protocol used by the qt front-end to communicate with the service
- csharp code which calls into another driver stack

In retrospect, of course, I could have ignored most of it.

Thankfully, I had a number of good tools at my disposal:

- for static reverse engineering of the native stuff, `binaryninja <https://binary.ninja/>`_
- for static reverse engineering of C#, `ILSpy <https://github.com/icsharpcode/ILSpy>`_
- x64dbg, for devirtualizing [#devirt]_ C++ vtables
- the sysinternals suite

~~~~~~~~~~~~~~~~~~~~~~~~~
The Corsair kernel driver
~~~~~~~~~~~~~~~~~~~~~~~~~

One of the first things I did was attaching `API Monitor <http://www.rohitab.com/apimonitor>`_
to all Corsair related processes I could find. A made a few discoveries:

- ``iCUE.exe`` talks to ``LLAccessService`` using some kind of RPC
- ``LLAccessService`` uses ioctls to call into ``CorsairLLAccess64.sys`` (a kernel module)

This led me to assume that LLAccessService was doing the low level stuff,
and that iCUE.exe contained the actual device drivers.

As the syscall traffic between ``LLAccessService`` and the kernel driver
didn't seem too daunting, I set out reverse engineering the kernel driver,
and use that knowledge to understand what's going on:

============   =============================
ioctl          description
============   =============================
``0x225388``   read msr
``0x229384``   write msr
``0x225348``   read PCI configuration
``0x229380``   write PCI configuration
``0x225374``   mmap IO space into userland
``0x229378``   unmap IO space from userland
``0x229350``   MMIO read
``0x22934c``   MMIO write
``0x225358``   port IO read
``0x229354``   port IO write
``0x22537c``   get driver version
============   =============================

Ok, well that's not a regular device driver: it's a stub which allows
userland programs to perform a wide range of privileged operations.
With some effort, it could even be used to escalate privileges from
local admin to kernel. Woopsie.

I tried reading through API Monitor logs and correlating it with configuration
changes, but had no luck: for a reason which became obvious later, there were
just too many calls.

~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The low level access service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

At that point, I felt like ``LLAccessService`` could help me replicate what the windows driver is doing,
and set out to reverse engineer this component, both statically using binaryninja, and dynamically using x64dbg.

After looking at imports and strings for a bit, here is what I learned:

- it calls ``CrGetLLAccessInterface`` from ``CorsairLLAccessLib64.dll``, which sets up an old school function table
- it sets up a `QT RemoteObject <https://doc.qt.io/qt-5/qtremoteobjects-index.html>`__ server

At that point, I wasn't in a mood for reversing C++, so had a look at ``CorsairLLAccessLib64``.

########################
CorsairLLAccessLib64.dll
########################

This library implements drivers for motherboard chipset SMBus controllers.
Its single exported function, ``CrGetLLAccessInterface``, returns a structure full of function pointers, which are
then used by ``LLAccessService`` to expose functionality over the network.

This module has quite a feature set, and does quite a lot of work to pull it off:

- direct port IO, including memory mapped IO, through the kernel driver
- reading and writting to PCI registries, through the kernel driver
- reading and writting MSRs, through the kernel driver
- detecting motherboard chipsets, both north and south bridge, by parsing ACPI tables, SMBios tables and CPUID data
- SMBus primitives, which relies on the port IO API and motherboard chipset detection to provide drivers for motherboard SMBus controllers
- enumerating memory modules, which relies on SMBus primitives to read out SPD chips

The motherboard metadata is then used by the front-end to figure out where each memory module is physically located on the motherboard, as
not all motherboards have slots placed in order, which is troublesome when trying to achieve animations accross multiple modules.

At that point, I knew what it takes to make a linux driver:

- load a driver for the motherboard's SMBus where modules are
- probe memory modules by attempting to read out their SPDs
- for each module with matching vendor and serial number:

  - replicate whatever the windows driver does to control LEDs over SMBus


###############
QT RemoteObject
###############

QT RemoteObject is a pretty obscure networking framework:

- it's a binary protocol over TCP
- the framework relies on an `iterface definition file <https://doc.qt.io/qt-6/qtremoteobjects-repc.html>`__ to generate client and server code
- the framework integrates with the QT signal system:

  - procedure calls are slots
  - server sent events are signals

- the protocol is not really documented anywhere except in QT's source code

At that point, I could think of multiple ways this API could be sniffed:

- using binary instrumentation in the server to log method calls, which sounded like a lot of work
- recording QT RemoteObject network traffic, and analyzing it after the fact, which would be fine, but would make it hard to figure out which GUI actions triggered which API calls
- running a man in the middle live analyzer, which is what I ended up doing


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Analyzing QT RemoteObject traffic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

I opened wireshard, and after a mix of looking at raw TCP stream data and QT source code reading, I could understand a packet:

.. code-block:: shell

   # packet length
   00 00 00 6c

   # packet type
   00 06
   # object name
   00 00 00 16
   00 L 00 L 00 A 00 c 00 c 00 e 00 s 00 s 00 I 00 p 00 c  # utf-16 LLAccessIpc
   # call type
   00 00 00 00
   # method index
   00 00 00 0c
   # arg list size
   00 00 00 03

   # first arg
   00 00 04 00 # type: user type
   00 # is_null: false
   00 00 00 1a # user type name len
   ll_access::DramIdentifier 00 # utf-8 custom type name
   00 00 00 00 00 00 00 00 5a # user type data

   # second arg
   00 00 00 24 # type: ushort
   00 # is_null: false
   00 45 # short int value

   # third arg
   00 00 00 02 # type: int
   00 # is_null: false
   ff ff ff fe # int value

   00 00 00 0b # packet serial id
   ff ff ff ff # packet property index

Thankfully the protocol is *mostly* self describing:

- all types are wrapped within a QVariants, which has special cases for all primitive types
- the length and format of custom user types has to be reverse engineered from the binary
- getting the method name from the method index requires reverse engineering too

Fortunately, method names were not too hard to find, and came with signatures [#pseudocode]_:

.. code-block:: c

   this->method_count = 0x19;
   this->methods[0] = sub_140010bd0(/* ... */ "InitiateConnection()",  /* ... */);
   this->methods[1] = sub_140013400(/* ... */ "CloseConnection(quint64)",  /* ... */);
   this->methods[2] = sub_140013400(/* ... */ "NotifyConnectionActive(quint64)",  /* ... */);
   this->methods[3] = sub_14000ef40(/* ... */ "GetSystemInfo()",  /* ... */);
   this->methods[4] = sub_14000eb40(/* ... */ "GetChipsetInfo()",  /* ... */);
   this->methods[5] = sub_14000f7d0(/* ... */ "SMBusGetControllerCount()",  /* ... */);
   this->methods[6] = sub_140010fd0(/* ... */ "SMBusGetCaps(uint64_t)",  /* ... */);
   this->methods[7] = sub_140010fd0(/* ... */ "SMBusGetBlockMaxSize(uint64_t)",  /* ... */);
   this->methods[8] = sub_14000ffd0(/* ... */ "SMBusSetDefaultLockTimeout(int)",  /* ... */);
   this->methods[9] = sub_14000ffd0(/* ... */ "SMBusSetDefaultOperationTimeout(int)",  /* ... */);
   this->methods[0xa] = sub_1400103d0(/* ... */ "SMBusSetCPUOffloadMask(uint32_t)",  /* ... */);
   this->methods[0xb] = sub_14000e740(/* ... */ "EnumMemoryModules()",  /* ... */);
   this->methods[0xc] = sub_14000e740(/* ... */ "SMBusReadByte(ll_access::DramIdentifier,uint16_t,int)",  /* ... */);
   this->methods[0xd] = sub_14000e740(/* ... */ "SMBusReadBlock(ll_access::DramIdentifier,uint16_t,int,int,int)",  /* ... */);
   this->methods[0xe] = sub_14000e740(/* ... */ "SMBusWriteByte(ll_access::DramIdentifier,uint16_t,uint8_t,int)",  /* ... */);
   this->methods[0xf] = sub_14000e740(/* ... */ "SMBusWriteWord(ll_access::DramIdentifier,uint16_t,uint16_t,int)",  /* ... */);
   this->methods[0x10] = sub_14000e740(/* ... */ "SMBusWriteBlock(ll_access::DramIdentifier,uint16_t,uint8_t,ll_access::Bytes,int,int)",  /* ... */);
   this->methods[0x11] = sub_14000e740(/* ... */ "SMBusWriteBlockNative(ll_access::DramIdentifier,uint16_t,ll_access::Bytes,int)",  /* ... */);
   this->methods[0x12] = sub_14000e740(/* ... */ "SMBusWriteByteCmdList(ll_access::DramIdentifier,ll_access::CommandList,int)",  /* ... */);
   this->methods[0x13] = sub_14000e740(/* ... */ "SMBusWriteWordCmdList(ll_access::DramIdentifier,ll_access::WordCommandList,int)",  /* ... */);
   this->methods[0x14] = sub_14000e740(/* ... */ "SMBusWriteBlockCmdList(ll_access::DramIdentifier,ll_access::BlockCommandList,int)",  /* ... */);
   this->methods[0x15] = sub_14000fbd0(/* ... */ "GetTSODReadings(uint64_t,uint8_t,int)",  /* ... */);
   this->methods[0x16] = sub_14000e740(/* ... */ "SetPropertyIfRequired(ll_access::DramIdentifier,uint16_t,uint8_t,int)",  /* ... */);
   this->methods[0x17] = sub_140013800(/* ... */ "SMBusLock(uint64_t,int)",  /* ... */);
   this->methods[0x18] = sub_1400107d0(/* ... */ "SMBusUnlock(uint64_t)",  /* ... */);

As for custom types, the only one used is ``ll_access::DramIdentifier``, and it just seems to be ``(bus_i: u32, device_i: u32)``.

I noticed that the port the client used to connect to the server changed when ``LLAccessService`` is restarted, and figured out that
LLAccessService shares which address the service listens on using a named memory backed file mappings:


.. include:: ll-proxy-diagram-orig.txt
   :literal:
   :class: text-diagram


This got me thinking about a way to easily achieve a man in the middle reverse proxy setup:

.. include:: ll-proxy-diagram.txt
   :literal:
   :class: text-diagram


#. Read the address written to the memory mapping by ``LLAccessService``
#. Start the reverse proxy, listen on a random port
#. Write that port to the memory mapping
#. Restart the client


Unfortunately, it did not quite go as planned: as the memory mapping is created by the service,
it is only writable by processes with sufficient privileges, which even the local admin account
does not have.

To work around this issue, I devised plan B:

#. Stop the service
#. Start ``LLAccessService`` as a child of the proxy process
#. Read the address written to the memory mapping by ``LLAccessService``
#. Start the reverse proxy, listen on a random port
#. Write that port to the memory mapping
#. Restart the client
#. On cleanup, restart the service


And it worked! `the code is available on github <https://github.com/multun/cue_ll_proxy/>`__:

- it was only tested with iCUE 4.15.153
- it requires python 3.10
- it relies of asyncio for networking
- it can be easily adapted to work with other QT RemoteObject software


I switched the LEDs off and on again from the GUI, and among the mountain of garbage, noticed the following log entries:

.. code-block:: json

   {"method_name": "SMBusWriteByteCmdList", "args": [[0, 90], [[160, 63]], -2]}
   {"method_name": "SMBusWriteByteCmdList", "args": [[0, 91], [[160, 63]], -2]}
   {"method_name": "SMBusWriteByteCmdList", "args": [[0, 90], [[160, 0]], -2]}
   {"method_name": "SMBusWriteByteCmdList", "args": [[0, 91], [[160, 0]], -2]}

After messing around with the GUI, I convinced myself that:

- the first argument is the address to write to (``0x5a`` and ``0x5b``), which is the module index + 8
- the second argument is the command (160)
- the third argument is brightness, on a range from 0 (full brightness) to 63 (off)

===============
Making a driver
===============

After solving an `issue specific to my motherboard <#acpi-hellscape>`__, I could finally get started writting a glorious shell driver:

.. code-block:: shell

   #!/bin/sh

   # Probe and set the brightness of all DDR4 single LED Corsair modules
   # depends on i2c-tools and util-linux (for hexdump)

   set -eo pipefail

   : "${BRIGHTNESS_PERCENT:=0}"
   if [ "$BRIGHTNESS_PERCENT" -lt 0 -o "$BRIGHTNESS_PERCENT" -gt 100 ]; then
      echo "BRIGHTNESS_PERCENT must be an integer between 0 and 100" >&2
      exit 1
   fi

   if [ "$(id -u)" != "0" ]; then
      echo "This script must be run as root" >&2
      exit 1
   fi

   # ensure all dependencies are installed
   for bin in grep i2cdetect i2cset hexdump decode-dimms modprobe; do
      if ! command -v "$bin" >/dev/null; then
         echo "Command not found: $bin" >&2
         exit 1
      fi
   done


   bus="/sys/bus/i2c/devices/i2c-${BUS_INDEX}"

   # ensure the bus exists
   if ! [ -d "$bus" ]; then
      echo "Invalid bus index '${BUS_INDEX}'. Available smbus buses:" >&2
      i2cdetect -l | grep smbus
      exit 1
   fi

   # load drivers
   modprobe i2c-dev
   modprobe ee1004

   # probe manually, as ee1004 does not support autoprobing
   for addr in $(i2cdetect -y "${BUS_INDEX}" 0x50 0x57 | sed -n '/50:/ { s/^50://; s/-\|U//g; p } '); do
      echo "ee1004 0x${addr}" > "$bus"/new_device
   done

   # for each module, figure out if the serial number is right. If so, turn off the LED
   for device in /sys/bus/i2c/drivers/ee1004/${BUS_INDEX}-005?; do
      device_index="$(printf %s "$device" | grep -o '.$')"

      # if the device is not compatible, skip it
      if ! hexdump -C "$device"/eeprom | decode-dimms -x /dev/stdin | grep -q '^Part Number [ ]*CMU'; then
         continue
      fi

      # the address where the LED module expects commands is offset by 8 from its SPD address
      led_index_hex="$(printf %x $((device_index + 8)))"
      # 63 is off, 0 is full brightness. Default to off.
      encoded_brightness=$(((100 - BRIGHTNESS_PERCENT) * 63 / 100))
      i2cset -y "${BUS_INDEX}" "0x5${led_index_hex}" 160 "${encoded_brightness}" b
   done

I also made a `rust version <https://github.com/multun/corsair-i2c-rs>`__, and considered writting a kernel module.


==========================
Bonus: The C# driver stack
==========================


Months later, When writting this article, I went back to the disassembly of the C# drivers, as I
wanted to understand how the C# code interfaced with the Corsair driver stack.

To my surprise, it did not!

- the C# code starts ``CpuIdRemote.exe``, and calls into it using a WCF RPC
- this process loads ``CpuIdWrapper.dll``, which is a wrapper over ``cpuidsdk.dll``
- ``cpuidsdk.dll`` is a commercial SDK from a company confusingly called `CPUID <https://www.cpuid-pro.com/products-system-information-kit.php>`__ [#cpuid]_.
  It supports a *lot* of stuff, including SMBus I/O. This dll is obfuscated,
  probably so they can ship the same binary for clients which aren't paying
  for the same features.

It seems like the old school Corsair driver stack is troublesome enough that iCUE is in the process of migrating away from it.
Interestingly, some devices seem to have both C# and legacy drivers available, including the device I'm interested in:

.. code-block:: c#

   internal class DramSingleLedDevice : DramLedDeviceBase
   {
      // SNIP

      public override DramLedType LedType => DramLedType.SingleColor;

      // SNIP

      public async Task SetLed(DramLedMode mode, byte brightness, byte plateau, byte slope, DramSyncDelayParameters delayParams)
      {
         // SNIP

         if (mode == DramLedMode.Static)
            WriteSMBus(160, ConvertBrightness(brightness));
         else
            WriteSMBus(new byte[4] { 164, slope, 165, plateau });

         // SNIP
      }

      // SNIP

      private byte ConvertBrightness(int input)
      {
         return (byte)((double)(100 - input) / 100.0 * 63.0);
      }
   }

It also has a nice helper to tell which part number map to which driver:

.. code-block:: c#

   internal static DramLedType GetLedType(string partNumber)
   {
       if (string.IsNullOrEmpty(partNumber))
           return DramLedType.None;

       if (partNumber.StartsWith("cmu", StringComparison.OrdinalIgnoreCase))
           return DramLedType.SingleColor;

       if (partNumber.StartsWith("cmr", StringComparison.OrdinalIgnoreCase))
           return DramLedType.Rgb;

       if (partNumber.StartsWith("cmw", StringComparison.OrdinalIgnoreCase))
           return DramLedType.Falcata;

       if (partNumber.StartsWith("cmt", StringComparison.OrdinalIgnoreCase))
           return DramLedType.Kopis;

       return DramLedType.None;
   }

At this point, I already had a linux driver for the LEDs, and it was nice to confirm I had gotten things right.

.. _acpi-hellscape:

=====================
Bonus: ACPI hellscape
=====================

On my machine, the driver for my motherboard's SMBus controller fails to load:

::

   [19722.892945] ACPI Warning: SystemIO range 0x0000000000000B00-0x0000000000000B08 conflicts with OpRegion 0x0000000000000B00-0x0000000000000B0F (\GSA1.SMBI) (20211217/utaddress-204)
   [19722.892952] ACPI: OSL: Resource conflict; ACPI support missing from driver?

Even though this warning can be silenced by adding ``acpi_enforce_resources=lax`` to the kernel command line, which make the driver load immediatly,
I was not comfortable doing so without investigating, and so I did!

First, get the ACPI tables: ``sudo acpidump -o acpi-tables.raw && acpixtract acpi-tables.raw``
Decompile to readable assembly: ``iasl -d *.dat``

Here's the entry the kernel is complaining about:

::

    Mutex (SME0, 0x00)
    OperationRegion (SMBI, SystemIO, 0x0B00, 0x10)
    Field (SMBI, ByteAcc, NoLock, Preserve)
    {
        HSTS,   8,
        Offset (0x02),
        HCNT,   8,
        HCMD,   8,
        TXSA,   8,
        DAT0,   8,
        DAT1,   8,
        HBDR,   8
    }

The issue here is the `OperationRegion instruction <https://uefi.org/htmlspecs/ACPI_Spec_6_4_html/19_ASL_Reference/ACPI_Source_Language_Reference.html#operationregion-declare-operation-region>`__,
which reserves the IO space range of the SMBus controller for exclusive use by ACPI. Linux thus complains when a driver tries to touch this address range.

But why would ACPI care about this SMBus controller? Huh ok, there seem to be a driver for the SMBus controller implemented in ACPI:

::

   Method (SMB0, 2, Serialized)
   {
       If (SRDY ())
       {
           Return (Zero)
       }
       HSTS = 0xBF
       TXSA = Arg0
       HCMD = Arg1
       HCNT = 0x44
       If (CMPL ())
       {
           If ((HSTS & 0x0C))
           {
               HSTS |= 0xFF
               Return (Zero)
           }
           Else
           {
               HSTS |= 0xFF
               Return (One)
           }
       }
       Return (Zero)
   }

I looked where this code was used, and found a giant method called ``WMBB``, which looks like a giant switch on method IDs:

::

   Method (WMBB, 3, Serialized)
   {
       If (Zero){}
       ElseIf ((Arg1 == One))
       {
           Return (GGG1 ())
       }
       ElseIf ((Arg1 == 0x02))
       {
           Return (GGG2 ())
       }
       ElseIf ((Arg1 == 0x03))
       {
           Return (GGG3 ())
       }
       ElseIf ((Arg1 == 0x04))
       {
           Return (GGG4 ())
       }
      /* SNIP: very very long method */
   }

Just above this switch method, there's another one that returns a ginormous buffer:

::

   Name (WQCC, Buffer (0x298C)
   {
       /* 0000 */  0x46, 0x4F, 0x4D, 0x42, 0x01, 0x00, 0x00, 0x00,  // FOMB....
       /* 0008 */  0x7C, 0x29, 0x00, 0x00, 0x24, 0xC0, 0x01, 0x00,  // |)..$...
       /* 0010 */  0x44, 0x53, 0x00, 0x01, 0x1A, 0x7D, 0xDA, 0x54,  // DS...}.T
       /* 0018 */  0x18, 0x32, 0x97, 0x01, 0x01, 0x08, 0x09, 0x42,  // .2.....B
       /* 0020 */  0x58, 0x09, 0x84, 0xC4, 0x39, 0xA0, 0x10, 0x81,  // X...9...
       /* 0028 */  0xE4, 0x13, 0x49, 0x0E, 0x0C, 0x4A, 0x02, 0x88,  // ..I..J..
       /* 0030 */  0xE4, 0x40, 0xC8, 0x05, 0x13, 0x13, 0x20, 0x02,  // .@.... .
       /* 0038 */  0x42, 0x5E, 0x05, 0xD8, 0x14, 0x60, 0x12, 0x44,  // B^...`.D
       /* 0040 */  0xFD, 0xFB, 0x43, 0x94, 0x06, 0x45, 0x09, 0x2C,  // ..C..E.,
       /* 0048 */  0x04, 0x42, 0x32, 0x05, 0xF8, 0x16, 0xE0, 0x58,  // .B2....X
       /* 0050 */  0x80, 0x61, 0x01, 0xB2, 0x05, 0x58, 0x86, 0x22,  // .a...X."
       /* 0058 */  0xA8, 0x9D, 0x0A, 0x90, 0x2B, 0x40, 0x98, 0x00,  // ....+@..
       /* 0060 */  0xF1, 0xA8, 0xC2, 0x68, 0x0E, 0x8A, 0x84, 0x83,  // ...h....
       /* 0068 */  0x46, 0x89, 0x81, 0x90, 0x44, 0x58, 0x39, 0xC7,  // F...DX9.
       /* 0070 */  0x96, 0x72, 0x01, 0xA6, 0x05, 0x08, 0x17, 0x20,  // .r..... 
       /* 0078 */  0x1D, 0x43, 0x23, 0xA8, 0x1B, 0x4C, 0x52, 0x05,  // .C#..LR.
       /* SNIP: very very long method */
   }

I looked up these method names and found out that these are the WMI descriptor and dispatcher:
WMI is windows's approach to add typing and metadata on top of ACPI. So this big blob can be decoded into something readable!

First, extract the WQCC buffer from the ACPI assembly: ``./extract-wqcc.py < ssdt7.dsl > wqcc.bin``

.. code-block:: python

   #!/usr/bin/env python3

   import sys
   import re

   MATCHER =  re.compile(r"/\* [a-fA-F0-9]* \*/ *((?:0x[a-fA-F0-9]{2}[ ,]*)*) *//.*")

   found = False
   for line in sys.stdin:
      if "WQCC" in line:
         found = True
         continue
      if not found:
         continue
      line = line.strip()

      if line == "{":
         continue
      if line == "})":
         exit(0)
      data_str = MATCHER.match(line).group(1)
      data = bytes(
         int(digit_str, 16)
         for digit_str in
         map(str.strip, data_str.split(","))
         if digit_str
      )
      sys.stdout.buffer.write(data)

Then, decode it with `bmfdec <https://github.com/pali/bmfdec>`__: ``./bmf2mof < wqcc.bin``

.. code-block:: c#

   /* SNIP */

   #pragma namespace("root\\wmi")
   [WMI, Dynamic, Provider("WmiProv"), Locale("MS\\0x409"), Description("Class used to operate All methods "), guid("{DEADBEEF-2001-0000-00A0-C90629100000}")]
   class GSA1_ACPIMethod {
     [key, read] string InstanceName;
     [read] boolean Active;

     /* SNIP */

     [WmiMethodId(92), Implemented, read, write, Description("")] void I2CBaseMemAddr([in, Description("")] uint8 I2cN, [out, Description("")] uint32 data);
     [WmiMethodId(93), Implemented, read, write, Description("")] void I2CBusTest([in, Description("")] uint8 bus, [in, Description("")] uint8 addr, [in, Description("")] uint8 data[260], [out, Description("")] GSA1_Buff260 ret);
     [WmiMethodId(95), Implemented, read, write, Description("")] void I2CWriteRead([in, Description("")] uint8 I2cN, [in, Description("")] uint8 addr, [out, Description("")] GSA1_ret32 ret);
     [WmiMethodId(96), Implemented, read, write, Description("")] void I2CWriteReadBlock([in, Description("")] uint8 I2cN, [in, Description("")] uint8 addr, [out, Description("")] GSA1_ret32 ret);
     [WmiMethodId(97), Implemented, read, write, Description("")] void SMBBaseAddr([in, Description("")] uint8 bus, [out, Description("")] uint32 data);
     [WmiMethodId(98), Implemented, read, write, Description("")] void SMBQuickWrite([in, Description("")] uint8 bus, [in, Description("")] uint8 addr, [out, Description("")] GSA1_ret32 ret);
     [WmiMethodId(99), Implemented, read, write, Description("")] void SMBQuickRead([in, Description("")] uint8 bus, [in, Description("")] uint8 addr, [out, Description("")] GSA1_ret32 ret);
     [WmiMethodId(100), Implemented, read, write, Description("")] void SMBIoBaseAddr([out, Description("")] uint16 data);
     [WmiMethodId(101), Implemented, read, write, Description("")] void SMBSendByte([in, Description("")] uint8 bus, [in, Description("")] uint8 addr, [in, Description("")] uint8 data, [out, Description("")] GSA1_ret32 ret);
     [WmiMethodId(102), Implemented, read, write, Description("")] void SMBReceiveByte([in, Description("")] uint8 bus, [in, Description("")] uint8 addr, [out, Description("")] GSA1_ret32 ret);
     [WmiMethodId(103), Implemented, read, write, Description("")] void SMBWriteByte([in, Description("")] uint8 bus, [in, Description("")] uint8 addr, [in, Description("")] uint8 cmd, [in, Description("")] uint8 data, [out, Description("")] GSA1_ret32 ret);
     [WmiMethodId(104), Implemented, read, write, Description("")] void SMBReadByte([in, Description("")] uint8 bus, [in, Description("")] uint8 addr, [in, Description("")] uint8 cmd, [out, Description("")] GSA1_ret32 ret);
     [WmiMethodId(105), Implemented, read, write, Description("")] void SMBWriteWord([in, Description("")] uint8 bus, [in, Description("")] uint8 addr, [in, Description("")] uint8 cmd, [in, Description("")] uint16 data, [out, Description("")] GSA1_ret32 ret);
     [WmiMethodId(106), Implemented, read, write, Description("")] void SMBReadWord([in, Description("")] uint8 bus, [in, Description("")] uint8 addr, [in, Description("")] uint8 cmd, [out, Description("")] GSA1_ret32 ret);
     [WmiMethodId(107), Implemented, read, write, Description("")] void SMBBlockWrite([in, Description("")] uint8 bus, [in, Description("")] uint8 addr, [in, Description("")] uint8 cmd, [in, Description("")] uint8 data[260], [out, Description("")] GSA1_ret32 ret);
     [WmiMethodId(108), Implemented, read, write, Description("")] void SMBBlockRead([in, Description("")] uint8 bus, [in, Description("")] uint8 addr, [in, Description("")] uint8 cmd, [out, Description("")] GSA1_Buff260 ret);
     [WmiMethodId(109), Implemented, read, write, Description("")] void SMBBlockWriteE32B([in, Description("")] uint8 bus, [in, Description("")] uint8 addr, [in, Description("")] uint8 cmd, [in, Description("")] uint8 data[260], [out, Description("")] GSA1_ret32 ret);

      /* SNIP */
   };

   /* SNIP */

This file is scary huge, I only kept the relevant bits. Incredibly, there even is a `mainline linux driver <https://github.com/t-8ch/linux-gigabyte-wmi-driver>`__ using part of this API: ``gigabyte_wmi``
At this point, I felt confident I could safely tell linux to ignore this resource usage conflict, blacklisted ``gigabyte_wmi``, added ``acpi_enforce_resources=lax`` to kernel parameters, it worked just fine.


.. [#temp-events] The temperature event line was introduced in DDR3 DIMMs. SDR, DDR and DDR2 don't have it.
.. [#hindsight] This, of course, is what I would have done if I knew better when I started it all.
.. [#devirt] Devirtualizing is the process of figuring out which C++ class
   is used in a particular dynamic context.
.. [#cpuid] CPUID is an x86 `processor instruction <https://en.wikipedia.org/wiki/CPUID>`__
.. [#pseudocode] This code has been altered to remove the boring parts
