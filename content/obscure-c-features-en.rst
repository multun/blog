------------------
Obscure C features
------------------
:date: 2019-08-21
:slug: obscure-c-features
:trans_id: obscure-c-features
:category: programming
:tags: C, programming, fun facts


.. role:: c(code)
   :language: c
   :class: highlight

If you spent a few years programming in C, you're probably much more confident about your knowledge of the language than if you spent as much time working with C++ or java.

Both the C language and its standard library are quite close to the smallest they could be.

The current most used version of the language, c99, gained some new features over the years, many of which are completely unknown to most C programmers (Older specifications obviously also have some dark corners).

Here are the ones I know about:

Sizeof may have side effects
============================


.. code-block:: c

   int main() {
       int n = 5;
       printf("%zu\n", sizeof(int *[n++]));
       printf("%d\n", n);
   }

It's because variadic types may require evaluating arbitrary code.

Hexadecimal float with an exponent
===================================

.. code-block:: c

   int main() {
     return assert(0xap-1 == 5.0);
   }

:c:`p` stands for power, and is followed by a base 10 encoded signed two exponent.

Compatible declarations and array function parameters
=====================================================

.. code-block:: c

   #include <stdio.h>

   void a(); // 1
   void a(long story, int a[*], int b[static 12][*][*]); // 2
   void a(long story, int a[42], int b[*][*][64]);       // 3
   void a(long story, int a[*], int b[const 42][24][*]); // 4
   // void a(long story, int a[*], int b[*][666][*]);    // 5
   // void a(long story, int a[*], int b[*][*][666]);    // 6

   void a(long story, int a[42], int b[restrict 0 * story + a[0]][24][64]) {
       printf("%zu\n", sizeof(a));
       printf("%zu\n", sizeof(b));
   }

   int main() {
       a(0, 0, 0);
       return 0;
   }

There are *plenty* of things going on there:

- One can declare multiple times the same function as long as their declarations are compatible, which means that if they have parameters, both declarations must have compatible ones. Declaration must also consistently use :c:`...`
- If the size of some array dimension is unknown at declaration time, one can write :c:`[*]` instead.
- You can enclose type qualifiers inside the array brackets, to add some informations about the properties to the given array dimension. If the keyword :c:`static` is given on the first dimension, the array dimension size is interpreted as an actual minimum size.
- The compiler should use new declarations to fill in missing informations about the function's prototype. That's why uncommenting any of declaration 5 and 6 should trigger an error: 666 isn't the known array dimension size. CLang ignores this. In fact, it doesn't seem to care at all about declaration merging.
- The size of the first dimension doesn't actually matter, so it gets ignored by the compiler. That's why declaration :math:`2` and :math:`4` do not conflict, even though the first dimension doesn't have the same size.

Compile-time tree structures
==========================================

.. code-block:: c

   struct bin_tree {
       int value;
       struct bin_tree *left;
       struct bin_tree *right;
   };

   #define NODE(V, L, R) &(struct bin_tree){V, L, R}

   const struct bin_tree *tree = \
       NODE(4,
            NODE(2, NULL, NULL),
            NODE(7,
                 NODE(5, NULL, NULL),
                 NULL));

This feature is called *compound literals*. You can do plenty of other funny tricks with these.

VLA typedef
===========

.. code-block:: c

   int main() {
       int size = 42;
       typedef int what[size];
       what the_fuck;
       printf("%zu\n", sizeof(the_fuck));
   }

This is standard since C99. I have no clue how this could ever be useful.

Array designators
=================

.. code-block:: c

   struct {
       int a[3], b;
   } w[] = {
       [0].a = {
           [1] = 2
       },
       [0].a[0] = 1,
   };

   int main() {
       printf("%d\n", w[0].a[0]);
       printf("%d\n", w[0].a[1]);
   }

You can iteratively define a structure member using a designator.

Preprocessor is a functional language
=====================================

.. code-block:: c

   #define OPERATORS_CALL(X)  \
       X(negate, 20, !)       \
       X(different, 70, !=)   \
       X(mod, 30, %)

   struct operator {
       int priority;
       const char *value;
   };

   #define DECLARE_OP(Name, Prio, Op)       \
       struct operator operator_##Name = {  \
           .priority = Prio,                \
           .value = #Op,                    \
       };

   OPERATORS_CALL(DECLARE_OP)

You can pass a macro as a parameter to another macro.

Typedef is a type qualifier
===========================

:c:`typedef` works just like :c:`inline` or :c:`static`.

Thus, you should be able to write

.. code-block:: c

   void typedef name;

:c:`a[b]` is a syntactic sugar
==============================

I know, I know, nothing crazy. But funny nonetheless !

:c:`a[b]` is literally equivalent to :c:`*(a + b)`.
You can thus write some absolute madness such as :c:`41[yourarray + 1]`.


Macro calls in :c:`#include`
============================

This is valid preprocessor:

.. code-block:: c

   #define ARCH x86
   #define ARCH_SPECIFIC(file) <ARCH/file>
   #include ARCH_SPECIFIC(test.h)

Awkward pointer declaration
===========================

.. code-block:: c

   int (*b);
   int (*b)(int);
   int (*b)[5];   // 1
   int *b[5];     // 2

All of these are valid declarations.

The parenthesis are useful for disambiguation:

- declaration 1 is a pointer to an array of 5 ints
- declaration 2 is an array of 5 pointers to int

A single :c:`#` is valid preprocessor
=====================================

It does nothing.

.. code-block:: c

   #
   #
   #

   int main() {
       return 0;
   }


That's all I got !

I found most of these reading the specification, some others while reading production code.

Happy C adventures :)
