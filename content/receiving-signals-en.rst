-------------------------------------
An alternate way of receiving signals
-------------------------------------
:date: 2020-04-07
:slug: receiving-signals
:trans_id: receiving-signals
:lang: en
:category: programming
:tags: C, programming, system programming

.. role:: c(code)
   :language: c
   :class: highlight

If you've ever dealt with signal handling, you probably still have in mind how
*painful* of an experience that was: making a reliable signal handler often is
an **astonishingly difficult task**.

The reason lies in the way signal handlers work: they interrupt whatever work was
being done, even the work that really shouldn't be.

Because of the very limited set of actions that can be done in such conditions,
people found ways around it:

Instead of interrupting the process, the general idea is to write the signal
somewhere the process can read when it's ready.

I knew of two ways to implement this same principle, but neither felt
appropriate. I scratched my head for a few days, and came up with a new one!

Let's discuss the two common implementations first:

==============
The pipe trick
==============

Write the signal number to a pipe in the signal handler, and read it in the main
program. This trick is very old but works fairly well.

It has its issues:

- when a process forks, it still shares its parent's pipe, which can cause
  mayhem if the child process writes a signal which is read in the parent
  process.
- when the pipe fills up, you have no choice but to drop messages, which
  doesn't sound great.
- it uses one more system call than the other solutions (not a big deal)

And some benefits:

- it provides a file descriptor, which can be used in event loops

========
SignalFD
========

``signalfd`` is a Linux-specific API, which does almost the same as the pipe
trick.

It solves both of the above issues while creating a major one:

- to be able to receive a signal using ``signalfd``, a signal must be blocked
  by the traditional signal handling API. As the fact a signal is blocked is
  inherited when creating new processes, you may end up spawning processes that
  have many signals inadvertently blocked. The workaround is to unblock it
  right after spawning the new process, which is a pretty inconvenient thing to
  do.
- it's also very linux specific

It comes with benefits:

- it yields better performance, as it does not interrupt the process at all, not even system calls
- it also provides a file descriptor, which can be used in event loops


------------

I did not like any of these techniques, as signalfd is linux specific, and the
pipe trick has fork safety and capacity issues. Here's what I came up with:

===========================
The versioned lookup table
===========================

This technique, just like the pipe trick, uses on plain old signal handlers.
It relies on these two base principles:

- the main program acts as a consumer. It polls the producer for new updates
- each signal is assigned an unique revision number

If the main process wants to check whether a new SIGINT has been received, it
can read the revision number of the producer and compare it with the last
revision number processed by the consumer.

Also:

- both the producer and the consumer needs to hold a lookup table which maps
  signals to their revision number
- an additional revision pair can be used to track the overall number of
  received signals, to avoid needlessly scanning the lookup table
- the number of times some signal was received is not guaranteed to be
  preserved by the signal delivery process, and thus does not need to be
  preserved at this stage
- an atomic flag can be used to allow multithreaded signal delivery on the
  signal handler side

The design of this technique was heavily inspired by the very interesting etcd
data model, thanks to which I learned about this revision trick.

.. code-block:: c

   /*

   Reading end:
    - read and cache the producer revision
    - if the cached producer and consumer revision are the same, stop there
    - otherwise, scan through the signaled array:
      - skip signals where producer revision == consumer revision
      - add the remaining signals to the result pool
      - copy the signal producer revision into the signal consumer revision
    - copy the cached producer revision into the consumer revision

   Writing end:
    - acquire the producer lock (if MT support enabled)
    - increment the signal revision
    - set the producer signal revision for the received signal
    - release the producer lock (if MT support enabled)

   */


   /* we need a big integer type that can be written in one instruction.
      unfortunately, sig_atomic_t is not always that big, is often signed,
      often smaller than needed, and doesn't even work properly on all
      architectures.

      /!\ this typedef is architecture dependent, see the full source /!\
                    https://github.com/multun/signal-lut
   */
   typedef /* some type */ lsig_atomic_t;


   struct signal_lut {
       /* when a signal is received, the handler sets this flag. other signal
          handlers have to spin, waiting for the lock to be released */
       atomic_flag producer_lock;

       /* increased by one each time a signal is added to the lookup table */
       volatile lsig_atomic_t lut_producer_revision;

       /* the revision of last processed signal */
       volatile lsig_atomic_t lut_consumer_revision;

       /* each cell stores the revision of the most recently received signal */
       volatile lsig_atomic_t producer_signal_revision[MAX_SIGNAL_NUMBER];

       /* each cell stores the revision of the last processed signal */
       volatile lsig_atomic_t consumer_signal_revision[MAX_SIGNAL_NUMBER];
   };

   static struct signal_lut state;

   void signal_lut_handler(int signum)
   {
       /* acquire the handler lock */
       while (atomic_flag_test_and_set_explicit(&state.producer_lock, memory_order_acquire))
           continue;

       /* update the signal revision */
       lsig_atomic_t sig_id = ++state.lut_producer_revision;
       state.producer_signal_revision[signum] = sig_id;

       /* release the handler lock */
       atomic_flag_clear_explicit(&state.producer_lock, memory_order_release);
   }

   int signal_lut_read(struct signal_list *events)
   {
       /* read events from the array */
       lsig_atomic_t cached_lut_producer_revision = state.lut_producer_revision;

       /* stop if no new event was received */
       if (cached_lut_producer_revision == state.lut_consumer_revision)
           return events->count;

       for (size_t i = 0; i < MAX_SIGNAL_NUMBER; i++) {
           if (state.consumer_signal_revision[i] == state.producer_signal_revision[i])
               continue;

           signal_list_add(events, i);
           state.consumer_signal_revision[i] = state.producer_signal_revision[i];
       }

       state.lut_consumer_revision = cached_lut_producer_revision;
       return events->count;
   }

Let's see how it performs:

- it doesn't have any of the issues of the pipe trick
- checking if a signal was received comes at almost no performance penalty

But:

- it can't be used as is in an event loop (see the next section for a workaround)
- it needs more code / is less efficient for architectures which can't write big
  integers in a single atomic instruction (these architectures very uncommon,
  and it can be worked around using :c:`sigprocmask`)

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
pipe + versioned lookup table
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The pipe trick not being entirely reliable (it must drop messages the pipe is
full) is one of the main reasons why I started looking for a new technique.

This issue can be addressed by using the lookup table as a fallback when the
pipe is full. The file descriptor from the pipe can still be used in an event
loop, which is definitely a plus.


------------


I really enjoyed writing this article, and I hope you enjoyed reading it!

Check out the full source code here: `https://github.com/multun/signal-lut <https://github.com/multun/signal-lut>`_
