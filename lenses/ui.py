import copy
import functools

from . import optics

lens_methods = [
    ('both_', optics.BothTraversal),
    ('decode_', optics.DecodeIso),
    ('error_', optics.ErrorIso),
    ('each_', optics.EachTraversal),
    ('filter_', optics.FilteringPrism),
    ('f_', optics.Getter),
    ('fork_', optics.ForkedSetter),
    ('get_', optics.GetitemOrElseLens),
    ('getattr_', optics.GetattrLens),
    ('getzoomattr_', optics.GetZoomAttrTraversal),
    ('getitem_', optics.GetitemLens),
    ('getter_setter_', optics.Lens),
    ('instance_', optics.InstancePrism),
    ('iso_', optics.Isomorphism),
    ('item_', optics.ItemLens),
    ('item_by_value_', optics.ItemByValueLens),
    ('items_', optics.ItemsTraversal),
    ('iter_', optics.IterableFold),
    ('json_', optics.JsonIso),
    ('just_', optics.JustPrism),
    ('keys_', optics.KeysTraversal),
    ('listwrap_', optics.ListWrapIso),
    ('norm_', optics.NormalisingIso),
    ('prism_', optics.Prism),
    ('tuple_', optics.TupleLens),
    ('values_', optics.ValuesTraversal),
    ('zoomattr_', optics.ZoomAttrTraversal),
    ('zoom_', optics.ZoomTraversal),
]


# we skip all the augmented artithmetic methods because the point of the
# lenses library is not to mutate anything
transparent_dunders = ('''
    __lt__ __le__ __eq__ __ne__ __gt__ __ge__

    __add__ __sub__ __mul__ __matmul__ __truediv__
    __floordiv__ __div__ __mod__ __divmod__ __pow__
    __lshift__ __rshift__ __and__ __xor__ __or__

    __radd__ __rsub__ __rmul__ __rmatmul__ __rtruediv__
    __rfloordiv__ __rdiv__ __rmod__ __rdivmod__ __rpow__
    __rlshift__ __rrshift__ __rand__ __rxor__ __ror__

    __neg__ __pos__ __invert__
''').split()


def _carry_op(name):
    def operation(self, *args, **kwargs):
        return self.modify(lambda a: getattr(a, name)(*args, **kwargs))

    doc = 'Equivalent to `self.call({!r}, *args, **kwargs))`'
    operation.__name__ = name
    operation.__doc__ = doc.format(name)
    return operation


def _carry_lens(method):
    @functools.wraps(method)
    def _(self, *args, **kwargs):
        lens = method(*args, **kwargs)
        return self.add_lens(lens)
    return _


def _add_extra_methods(cls):
    for dunder in transparent_dunders:
        setattr(cls, dunder, _carry_op(dunder))

    for name, lens in lens_methods:
        setattr(cls, name, _carry_lens(lens))

    return cls


@_add_extra_methods
class Lens(object):
    'A user-friendly object for interacting with the lenses library'
    __slots__ = ['state', 'lens']

    def __init__(self, state=None, lens=None):
        if lens is None:
            lens = optics.TrivialIso()
        self.state = state
        self.lens = lens

    def __repr__(self):
        return '{}({!r}, {!r})'.format(self.__class__.__name__,
                                       self.state, self.lens)

    def _assert_bound(self, name):
        if self.state is None:
            raise ValueError('{} requires a bound lens'.format(name))

    def _assert_unbound(self, name):
        if self.state is not None:
            raise ValueError('{} requires an unbound lens'.format(name))

    def get(self, state=None):
        '''Get the first value focused by the lens.

            >>> from lenses import lens
            >>> lens([1, 2, 3]).get()
            [1, 2, 3]
            >>> lens([1, 2, 3])[0].get()
            1
        '''
        if state is not None:
            self = self.bind(state)
        self._assert_bound('Lens.get')
        return self.lens.to_list_of(self.state)[0]

    def get_all(self, state=None):
        '''Get multiple values focused by the lens. Returns them as a
        list.

            >>> from lenses import lens
            >>> lens([1, 2, 3])[0].get_all()
            [1]
            >>> lens([1, 2, 3]).both_().get_all()
            [1, 2]
        '''
        if state is not None:
            self = self.bind(state)
        self._assert_bound('Lens.get_all')
        return self.lens.to_list_of(self.state)

    def get_monoid(self, state=None):
        '''Get the values focused by the lens, merging them together by
        treating them as a monoid. See `lenses.typeclass.mappend`.

            >>> from lenses import lens
            >>> lens([[], [1], [2, 3]]).each_().get_monoid()
            [1, 2, 3]
        '''
        if state is not None:
            self = self.bind(state)
        self._assert_bound('Lens.get_monoid')
        return self.lens.view(self.state)

    def set(self, newvalue, state=None):
        '''Set the focus to `newvalue`.

            >>> from lenses import lens
            >>> lens([1, 2, 3])[1].set(4)
            [1, 4, 3]
        '''
        if state is not None:
            self = self.bind(state)
        self._assert_bound('Lens.set')
        return self.lens.set(self.state, newvalue)

    def modify(self, func, state=None):
        '''Apply a function to the focus.

            >>> from lenses import lens
            >>> lens([1, 2, 3])[1].modify(str)
            [1, '2', 3]
            >>> lens([1, 2, 3])[1].modify(lambda n: n + 10)
            [1, 12, 3]
        '''
        if state is not None:
            self = self.bind(state)
        self._assert_bound('Lens.modify')
        return self.lens.over(self.state, func)

    def call(self, method_name, *args, **kwargs):
        '''Call a method on the focus. The method must return a new
        value for the focus.

            >>> from lenses import lens
            >>> lens(['alpha', 'beta', 'gamma'])[2].call('upper')
            ['alpha', 'beta', 'GAMMA']

        As a shortcut, you can include the name of the method you want
        to call immediately after `call_`:

            >>> lens(['alpha', 'beta', 'gamma'])[2].call_upper()
            ['alpha', 'beta', 'GAMMA']
        '''
        if 'state' in kwargs:
            self = self.bind(kwargs['state'])
            del kwargs['state']

        def func(a):
            return getattr(a, method_name)(*args, **kwargs)

        return self.modify(func)

    def call_mut(self, method_name, *args, **kwargs):
        '''Call a method on the focus that will mutate it in place.
        Works by making a deep copy of the focus before calling the
        mutating method on it. The return value of that method is ignored.
        You can pass a keyword argument shallow=True to only make a
        shallow copy.

            >>> from lenses import lens
            >>> lens([[3, 1, 2], [5, 4]])[0].call_mut('sort')
            [[1, 2, 3], [5, 4]]

        As a shortcut, you can include the name of the method you want
        to call immediately after `call_mut_`:

            >>> lens([[3, 1, 2], [5, 4]])[0].call_mut_sort()
            [[1, 2, 3], [5, 4]]
        '''
        if 'state' in kwargs:
            self = self.bind(kwargs['state'])
            del kwargs['state']

        shallow = False
        if 'shallow' in kwargs:
            shallow = kwargs['shallow']
            del kwargs['shallow']

        def func(a):
            a = copy.copy(a) if shallow else copy.deepcopy(a)
            getattr(a, method_name)(*args, **kwargs)
            return a

        return self.modify(func)

    def construct(self, focus=None):
        '''Construct a state given a focus.'''
        if focus is not None:
            self = self.bind(focus)
        self._assert_bound('Lens.construct')
        return self.lens.re().view(self.state)

    def add_lens(self, other):
        '''Refine the current focus of this lens by composing it with
        another lens object. Can be a `lenses.optics.LensLike` or
        an unbound `lenses.Lens`.

            >>> from lenses import lens
            >>> second_first = lens()[1][0]
            >>> lens([[0, 1], [2, 3]]).add_lens(second_first).get()
            2
        '''
        if isinstance(other, optics.LensLike):
            return Lens(self.state, self.lens.compose(other))
        elif isinstance(other, Lens):
            other._assert_unbound('Lens.add_lens')
            return Lens(self.state, self.lens.compose(other.lens))
        else:
            raise TypeError('''Cannot add lens of type {!r}.'''
                            .format(type(other)))

    def bind(self, state):
        '''Bind this lens to a specific `state`. Raises `ValueError`
        when the lens has already been bound.

            >>> from lenses import lens
            >>> lens()[1].bind([1, 2, 3]).get()
            2
        '''
        self._assert_unbound('Lens.bind')
        return Lens(state, self.lens)

    def flip(self):
        '''Flips the direction of the lens. The lens must be unbound and
        all the underlying operations must be isomorphisms.

            >>> from lenses import lens
            >>> json_encoder = lens().decode_().json_().flip()
            >>> json_encoder.bind(['hello', 'world']).get()  # doctest: +SKIP
            b'["hello", "world"]'
        '''
        self._assert_unbound('Lens.flip')
        return Lens(self.state, self.lens.from_())

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return self.bind(instance)

    def __getattr__(self, name):
        if name.endswith('_'):
            raise AttributeError('Not a valid lens constructor')

        if name.startswith('call_mut_'):
            def caller(*args, **kwargs):
                return self.call_mut(name[9:], *args, **kwargs)
            return caller

        if name.startswith('call_'):
            def caller(*args, **kwargs):
                return self.call(name[5:], *args, **kwargs)
            return caller

        return self.add_lens(optics.GetZoomAttrTraversal(name))

    def __getitem__(self, name):
        return self.add_lens(optics.GetitemLens(name))

    def _underlying_lens(self):
        return self.lens