import functools
import random
import unittest
from test import test_support

tests = []


def make(compose, label):

    class ComposeTest(unittest.TestCase):

        def test_one(self):
            f = compose(list)
            self.assertEqual(f(xrange(10)), range(10))

        def test_many(self):
            f = compose(tuple, sorted)
            a = range(10)
            random.shuffle(a)
            self.assertEqual(f(a), (0, 1, 2, 3, 4, 5, 6, 7, 8, 9))

        def test_order(self):

            run = []

            def a(k):
                def sub(_):
                    run.append(k)
                return sub

            f = compose(a(3), a(2), a(1), a(0))
            f(object())
            self.assertEqual(run, [0, 1, 2, 3])

        def test_kw(self):
            def test(a, b, c):
                return a + b + c
            f = compose((2).__mul__, test)
            self.assertEqual(12, f(1, 2, 3))
            self.assertEqual(12, f(a=1, b=2, c=3))
            self.assertEqual(12, f(1, 2, c=3))

        def test_method(self):

            class test(object):

                def __init__(self):
                    self.arg = 1

                def meth(self, arg):
                    yield self.arg
                    yield arg

                meth = compose(list, meth)

            ob = test()
            self.assertEqual(ob.meth(3), [1, 3])


        def test_typeerror(self):
            self.assertRaises(TypeError, compose)

    return type(label, (ComposeTest,), {})

tests.append(make(functools.py_compose, 'PyComposeTest'))
tests.append(make(functools.c_compose, 'CComposeTest'))


def make(fastcut, label):

    def test(*args, **kw):
        return args, kw

    a = object()
    b = object()
    c = object()
    d = object()

    class FastcutTest(unittest.TestCase):

        def cmp(self, result, *args, **kw):
            self.assertEqual(result, (args, kw))

        def test_none(self):
            x = fastcut(test)
            self.cmp(x())

        def test_sargs(self):
            x = fastcut(test, a)
            self.cmp(x(), a)

        def test_sargs_skw(self):
            x = fastcut(test, a, b=b)
            self.cmp(x(), a, b=b)

        def test_sargs_skw_args(self):
            x = fastcut(test, a, b=b)
            self.cmp(x(c), a, c, b=b)

        def test_sargs_skw_args_kw(self):
            x = fastcut(test, a, b=b)
            self.cmp(x(c, d=d), a, c, b=b, d=d)

        def test_sargs_args(self):
            x = fastcut(test, a)
            self.cmp(x(b), a, b)

        def test_sargs_args_kw(self):
            x = fastcut(test, a)
            self.cmp(x(b, c=c), a, b, c=c)

        def test_sargs_kw(self):
            x = fastcut(test, a)
            self.cmp(x(b=b), a, b=b)

        def test_skw(self):
            x = fastcut(test, a=a)
            self.cmp(x(), a=a)

        def test_skw_args(self):
            x = fastcut(test, a=a)
            self.cmp(x(b), b, a=a)

        def test_skw_args_kw(self):
            x = fastcut(test, a=a)
            self.cmp(x(b, c=c), b, a=a, c=c)

        def test_skw_kw(self):
            x = fastcut(test, a=a)
            self.cmp(x(b=b), a=a, b=b)

        def test_args(self):
            x = fastcut(test)
            self.cmp(x(a), a)

        def test_args_kw(self):
            x = fastcut(test)
            self.cmp(x(a, b=b), a, b=b)

        def test_kw(self):
            x = fastcut(test)
            self.cmp(x(a=a), a=a)

        def test_typeerror(self):
            self.assertRaises(TypeError, fastcut)

    return type(label, (FastcutTest,), {})

tests.append(make(functools.py_fastcut, 'PyFastcutTest'))
tests.append(make(functools.c_fastcut, 'CFastcutTest'))


def test_main():
    test_support.run_unittest(*tests)

if __name__ == '__main__':
    test_main()
