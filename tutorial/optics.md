# Optics

Lenses are just one in a whole family of related objects called
_optics_. Optics generalise the notion of accessing data.

The heirarchy of optics looks like this:

![Optics family](optics_family.png)

An arrow pointing from A to B here means that all B are also A. For
example, all Lenses are also Getters, and all Getters are also Folds.

## Traversals

All the lenses so far have focused a single object inside a state, but
it is possible for an optic to have more than one focus. An optic with
multiple foci is usually referred to as a traversal. A simple traversal
can be made with the `_both` method. `lens.both_()` focuses the two
objects at indices `0` and `1` within the state. It is intended to be
used with tuples of length 2, but will work on any indexable object.

One issue with multi-focus optics is that the `get` method only ever
returns a single focus. It will return the _first_ item focused by the
optic. If we want to get all the items focused by that optic then we
can use the `collect` method which will return those objects in a list:

	>>> from lenses import lens
	>>> data = [0, 1, 2, 3]
	>>> both = lens.both_()
	>>> both.get()(data)
	0
	>>> both.collect()(data)
	[0, 1]

Setting works with a traversal, though all foci will be set to the same
object.

	>>> both.set(4)(data)
	[4, 4, 2, 3]

Modifying is the most useful operation we can perform. The modification
will be applied to all the foci independently. All the foci must be of
the same type (or at least be of a type that supports the modification
that we want to make).

	>>> both.modify(lambda a: a + 10)(data)
	[10, 11, 2, 3]
	>>> both.modify(str)([0, 1.0, 2, 3])
	['0', '1.0', 2, 3]

You can of course use the same shortcut for operators that single-focus
lenses allow:

	>>> (both + 10)(data)
	[10, 11, 2, 3]

Traversals can be composed with normal lenses. The result is a traversal
with the lens applied to each of its original foci:

	>>> data = [[0, 1], [2, 3]]
	>>> both_then_zero = lens.both_()[0]
	>>> both_then_zero.collect()(data)
	[0, 2]
	>>> (both_then_zero + 10)(data)
	[[10, 1], [12, 3]]

Traversals can also be composed with other traversals just fine. They
will simply increase the number of foci targeted. Note that `collect`
returns a flat list of foci; none of the structure of the state is
preserved.

	>>> both_twice = lens.both_().both_()
	>>> both_twice.collect()(data)
	[0, 1, 2, 3]
	>>> (both_twice + 10)(data)
	[[10, 11], [12, 13]]

A slightly more useful traversal method is `each_`. `each_` will focus
all of the items in a data-structure analogous to iterating over it
using python's `iter` and `next`. It supports most of the built-in
iterables out of the box, but if we want to use it on our own objects
then we will need to add a hook explicitly.

	>>> data = [1, 2, 3]
	>>> (lens.each_() + 10)(data)
	[11, 12, 13]

The `values_` method returns a traversal that focuses all of the values
in a dictionary. If we return to our `GameState` example from earlier,
we can use `values_` to move _every_ enemy in the same level 1 pixel
over to the right in one line of code:

	>>> from collections import namedtuple
	>>>
	>>> GameState = namedtuple('GameState',
	...     'current_world current_level worlds')
	>>> World = namedtuple('World', 'theme levels')
	>>> Level = namedtuple('Level', 'map enemies')
	>>> Enemy = namedtuple('Enemy', 'x y')
	>>>
	>>> data = GameState(1, 2, {
	...     1: World('grassland', {}),
	...     2: World('desert', {
	...         1: Level({}, {
	...             'goomba1': Enemy(100, 45),
	...             'goomba2': Enemy(130, 45),
	...             'goomba3': Enemy(160, 45),
	...         }),
	...     }),
	... })
	>>>
	>>> level_enemies_right = (lens.worlds[2]
	...                            .levels[1]
	...                            .enemies.values_().x + 1)
	>>> new_data = level_enemies_right(data)

Or we could do the same thing to every enemy in the entire game
(assuming that there were other enemies on other levels in the
`GameState`):

	>>> all_enemies_right = (lens.worlds.values_()
	...                          .levels.values_()
	...                          .enemies.values_().x + 1)
	>>> new_data = all_enemies_right(data)