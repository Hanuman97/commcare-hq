from __future__ import absolute_import

from django.conf import settings
if not settings.configured:
    settings.configure(DEBUG=True)


import sys
from unittest2 import TestCase

from dimagi.utils.create_unique_filter import create_unique_filter
from dimagi.utils.excel import IteratorJSONReader
from dimagi.utils.decorators.memoized import memoized
from dimagi.utils.chunked import chunked
from dimagi.utils.couch.loosechange import AssocArray

class DimagiUtilsTestCase(TestCase):
    def test_create_unique_filter(self):
        l = [{'id': 'a'}, {'id': 'b'}, {'id': 'a'}, {'id': 'c'}, {'id': 'b'}]
        assert filter(create_unique_filter(lambda x: x['id']), l) == [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}]
        assert filter(create_unique_filter(lambda x: id(x)), l) == [{'id': 'a'}, {'id': 'b'}, {'id': 'a'}, {'id': 'c'}, {'id': 'b'}]

    def test_IteratorJSONReader(self):
        def normalize(it):
            r = []
            for row in IteratorJSONReader(it):
                r.append(sorted(row.items()))
            return r

        assert normalize([]) == []
    
        assert normalize([['A', 'B', 'C'], ['1', '2', '3']]) == [[('A', '1'), ('B', '2'), ('C', '3')]]
    
        assert (normalize([['A', 'data: key', 'user 1', 'user 2', 'is-ok?'], ['1', '2', '3', '4', 'yes']])
                == [[('A', '1'), ('data', {'key': '2'}), ('is-ok', True), ('user', ['3', '4'])]])

    
    def test_memoized_function(self):
        @memoized
        def f(n=0):
            return n**2

        assert f() == 0
        assert f.get_cache() == {(0,): 0}
        assert f(0) == 0
        assert f.get_cache() == {(0,): 0}
        assert f(2) == 4
        assert sorted(f.get_cache().items()) == [((0,), 0), ((2,), 4)]

    def test_memoized_class(self):
        calls = {'get_full_name': 0, 'full_name': 0, 'complicated_method': 0}
    
        @memoized
        class Person(object):
            get_full_name_calls = 0    
            full_name_calls = 0
            complicated_method_calls = 0    
        
            def __init__(self, first_name, last_name):
                self.first_name = first_name
                self.last_name = last_name

            @property
            @memoized
            def full_name(self):
                calls['full_name'] = calls['full_name'] + 1
                return "%s %s" % (self.first_name, self.last_name)

            @memoized
            def get_full_name(self):
                calls['get_full_name'] = calls['get_full_name'] + 1
                return "%s %s" % (self.first_name, self.last_name)

            def __repr__(self):
                return "%s(%r, %r)" % (self.__class__.__name__, self.first_name, self.last_name)

            @memoized
            def complicated_method(self, a, b=10, *args, **kwargs):
                calls['complicated_method'] = calls['complicated_method'] + 1
                return a, b, args, kwargs

        p = Person("Danny", "Roberts")
        assert p.get_full_name() == 'Danny Roberts'
        assert calls['get_full_name'] == 1
        assert p.get_full_name() == 'Danny Roberts'
        assert calls['get_full_name'] == 1

        assert p.full_name == 'Danny Roberts'
        assert calls['full_name'] == 1
        assert p.full_name == 'Danny Roberts'
        assert calls['full_name'] == 1

        assert Person("Danny", "Roberts")._full_name_cache == {(Person('Danny', 'Roberts'),): 'Danny Roberts'}
        assert Person.get_full_name.get_cache(p) == {(Person('Danny', 'Roberts'),): 'Danny Roberts'}

        assert p.complicated_method(5) == (5, 10, (), {})
        assert calls['complicated_method'] == 1
        assert p.complicated_method(5) == (5, 10, (), {})
        assert calls['complicated_method'] == 1

        assert p.complicated_method(1, 2, 3, 4, 5, foo='bar') == (1, 2, (3, 4, 5), {'foo': 'bar'})
        assert calls['complicated_method'] == 2

        q = Person("Joe", "Schmoe")
        assert q.get_full_name() == 'Joe Schmoe'
        assert calls['get_full_name'] == 2

    def test_chunked(self):
        assert list(chunked(range(10), 4)) == [
            (0, 1, 2, 3),
            (4, 5, 6, 7),
            (8, 9)
        ]

    def test_assoc_array(self):
        d1 = {'a': 3, 'b': None, '@c': 'ss'}
        aa1 = AssocArray(d1)

        self.assertEqual(aa1._, d1)
        self.assertEqual(repr(aa1), repr(d1))

        self.assertEqual(aa1.a, 3)
        self.assertEqual(aa1('a'), 3)
        self.assertEqual(aa1['a'], 3)
        #key 'b' exists but val is None
        self.assertEqual(aa1.b, None)
        self.assertEqual(aa1('b'), None)
        self.assertEqual(aa1['b'], None)
        self.assertEqual(aa1('@c'), 'ss')
        self.assertEqual(aa1['@c'], 'ss')
        #key 'd' doesn't exist
        self.assertEqual(aa1.d, None)
        self.assertEqual(aa1('d'), None)
        self.assertEqual(aa1['d'], None)

        self.assertEqual(aa1.__('@c'), 'ss')
        self.assertEqual(aa1.__('@c', '__none'), 'ss')
        self.assertEqual(aa1.__('@c', ex=1), 'ss')
        self.assertEqual(aa1.__('b', 'default'), None)
        self.assertEqual(aa1.__('b', ex=1), None)
        self.assertEqual(aa1.__('d', 'default'), 'default')
        self.assertRaises(AttributeError, lambda: aa1.__('d', ex=1))

        aa2 = AssocArray({'_': True, '__': 4})

        self.assertNotEqual(aa2._, True)
        self.assertNotEqual(aa2.__, 4)
        self.assertEqual(aa2('_'), True)
        self.assertEqual(aa2['_'], True)
        self.assertEqual(aa2.__('_'), True)
        self.assertEqual(aa2('__'), 4)
        self.assertEqual(aa2['__'], 4)
        self.assertEqual(aa2.__('__'), 4)
        self.assertEqual(aa1('_'), None)
        self.assertEqual(aa1.__('__', 'missing'), 'missing')

        d3 = {'a': 1, 'b': aa1, 'a.b': 'x'}
        aa3 = AssocArray(d3)

        self.assertEqual(aa3.b, aa1)
        self.assertEqual(aa3._, d3)
        self.assertEqual(aa3['b'], aa1)
        self.assertEqual(aa3['b', '@c'], 'ss')
        self.assertEqual(aa3['b', 'd'], None) #aa3.b.d doesn't exist
        self.assertEqual(aa3['f', 'f'], None) #aa3.f doesn't exist
        self.assertEqual(aa3('b.@c'), 'ss')
        self.assertEqual(aa3('b.d'), None)
        self.assertEqual(aa3('f.f'), None)
        self.assertEqual(aa3['a.b'], 'x') #'a.b' is a single key
        self.assertEqual(aa3.__('a.b'), 'x')

        aa4 = AssocArray({'a': AssocArray({'b': AssocArray({'c': AssocArray({'d': 1})})}), 'x': 5})
        self.assertEqual(aa4('a.b.c.d'), 1)
        self.assertEqual(aa4('a.b.f'), None)
        self.assertEqual(aa4('a.q'), None)
        self.assertEqual(aa4('x.x'), None) #aa4.x exists, but is not an AssocArray

        aa5 = AssocArray({'_': AssocArray({'__': AssocArray({'_': 2})})})
        self.assertEqual(aa5('_.__._'), 2)

        aa6 = AssocArray({'a.b': AssocArray({'c.d': 3})})
        self.assertEqual(aa6['a.b', 'c.d'], 3)
        self.assertNotEqual(aa6('a.b.c.d'), 3)
