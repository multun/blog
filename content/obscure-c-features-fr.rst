------------------------
Les recoins obscurs du C
------------------------
:date: 2019-08-21
:slug: les-recoins-obscurs-du-c
:trans_id: obscure-c-features
:lang: fr
:category: software
:tags: C, programming


.. role:: c(code)
   :language: c
   :class: highlight

Si vous programmez en C depuis quelques temps déjà, vous êtes probablement plus confiants que si vous aviez passé autant de temps à programmer en C++ ou en java.

En cause, le côté minimaliste du langage et de sa bibliothèque standard.

Pourtant, quelques perles étranges s'y cachent.

La version actuelle du langage, le c99, a apporté un lot de nouvelles fonctionnalités semblent complètement étrangères à la plupart des développeurs C (même si les normes plus anciennes ont aussi leur lot de coins sombres).

Voici celles que je connais :

Sizeof peut avoir des effets de bord
====================================


.. code-block:: c

   int main(void) {
       return sizeof(int[printf("ooops\n")]);
   }

:c:`sizeof` sur des types variadiques demande d'évaluer une expression arbitraire !

Flottant hexadécimal avec exposant
==================================

.. code-block:: c

   int main() {
     return assert(0xap-1 == 5.0);
   }

Le :c:`p` signifie puissance, et est suivi par un exposant base 2 encodé en base 10.
L'expression a pour type :c:`double`, mais cela peut être changé en :c:`float` en ajoutant un :c:`f` terminal.

Déclarations compatibles et tableaux arguments
==============================================

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

Il y a *beaucoup* de choses à dire :

- Il est possible de déclarer plusieurs fois une fonction tant que les déclarations sont compatibles. Une déclaration est compatible avec une autre quand le type de leurs arguments est compatible. Il faut aussi que les déclaration soient consistantes dans leur usage de :c:`...`.
- Si la taille de la dimension d'un tableau en paramètre est inconnue à la déclaration, il est possible d'écrire :c:`[*]` à la place.
- Vous pouvez ajouter des type qualifiers dans les accolades de la première dimension des tableaux en argument. Si le mot clé :c:`static` est présent, la taille de la première dimension du tableau n'est plus ignorée et peut être utilisée par le compilateur pour des optimisations.
- Le compilateur devrait utiliser les nouvelles déclarations pour compléter les détails manquants des déclarations précédentes. C'est pourquoi dé-commenter les déclarations 5 et 6 devrait déclencher une erreur : 666 n'est pas la taille connue de cette dimension. CLang ignore ce détail. En fait, CLang n'a pas l'air de prendre en compte la fusion des déclarations.
- La taille de la première dimension n'importe pas vraiment, et est ignorée en temps normal. C'est pourquoi les déclarations :math:`2` et :math:`4` ne rentrent pas en conflit, même si leur première dimension n'a pas la même taille.

Structures arborescentes à la compilation
=========================================

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

Cette structure s'appelle *compound literals*. Ceux-ci sont à la source d'un certain nombre de petites astuces.

typedef VLA
===========

.. code-block:: c

   int main() {
       int size = 42;
       typedef int what[size];
       what the_fuck;
       printf("%zu\n", sizeof(the_fuck));
   }

C'est standard depuis C99. Je suis toujours à la recherche d'une utilisation pertinente.

Indicateur d'initialisation de tableau
======================================

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

Il est possible de construire incrémentalement une structure et ses membres en utilisant des indicateurs d'initialisation (*designators* en anglais). Cette fonctionnalité

Le préprocesseur est un langage fonctionnel
===========================================

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

Il est possible de passer le nom d'une macro en paramètre a une autre macro, puis de l'appeler.

Il est possible d'entremêler un switch et du code
=================================================

.. code-block:: c

   #include <stdio.h>
   #include <stdlib.h>
   #include <err.h>

   int main(int argc, char *argv[]) {
       if (argc != 2)
           errx(1, "Usage: %s DESTINATION", argv[0]);

       int destination = atoi(argv[1]);

       int i = 0;
       switch (destination) {
           for (; i < 2; i++) {
           case 0: puts("0");
           case 1: puts("1");
           case 2: puts("2");
           case 3: puts("3");
           case 4: puts("4");
           default:;
           }
       }
       return 0;
   }

Ce genre de structures porte le petit nom de `gadget de Duff <https://en.wikipedia.org/wiki/Duff%27s_device>`_.
Cela permet entre autre de dérouler manuellement des boucles (*loop unrolling* en anglais)

Typedef est presque une storage class
=====================================

:c:`typedef` fonctionne presque comme :c:`inline` ou :c:`static`.

Il devrait être possible d'écrire

.. code-block:: c

   void typedef name;

:c:`a[b]` est un sucre syntaxique
=================================

Oui, je sais, rien de fou. Mais étonnant quand même !

:c:`a[b]` est littéralement équivalent à :c:`*(a + b)`.
Il est donc légal d'écrire des folies comme :c:`41[yourarray + 1]`.


Appels à macro dans :c:`#include`
=================================

.. code-block:: c

   #define ARCH x86
   #define ARCH_SPECIFIC(file) <ARCH/file>
   #include ARCH_SPECIFIC(test.h)

Étrange déclaration de pointeur
===============================

.. code-block:: c

   int (*b);
   int (*b)(int);
   int (*b)[5];   // 1
   int *b[5];     // 2

Toutes les lignes sont des déclarations valides.

Les parenthèses évitent une ambiguïté :

- la déclaration 1 est un pointeur vers un tableau de 5 ints
- la déclaration 2 est un tableau de 5 pointeurs sur int

Un unique :c:`#` est du préprocesseur valide
============================================

Et… ça ne fait rien.

.. code-block:: c

   #
   #
   #

   int main() {
       return 0;
   }


C'est tout ce que j'ai !

J'ai trouvé la plupart des perles en lisant la spécification, et quelques unes en lisant du vrai code.

Soyez inventifs et bonne programmation :)
