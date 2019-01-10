import lazytools
import unittest
from test import test_support

tests = []


def make(promise, label):

    class PromiseTest(unittest.TestCase):

        def test_basic(self):

            lis = []

            def fun():
                lis.append(None)
                return object()

            p = promise(fun)
            self.assertEqual(len(lis), 0)
            ob1 = p()
            self.assertEqual(len(lis), 1)
            ob2 = p()
            self.assertEqual(len(lis), 1)
            self.assert_(ob1 is ob2)

        def test_repr(self):

            p = promise(lambda: 'a')
            self.assert_('forced' not in repr(p))
            p()
            self.assert_('forced' in repr(p))

        def test_typeerror(self):
            self.assertRaises(TypeError, promise)

        def test_exception(self):

            run = []

            def test():
                run.append(None)
                raise ValueError

            p = promise(test)
            self.assertEqual(run, [])
            self.assertRaises(ValueError, p)
            self.assertEqual(run, [None])
            self.assertRaises(ValueError, p)
            self.assertEqual(run, [None, None])

    return type(label, (PromiseTest,), {})

tests.append(make(lazytools.py_promise, 'PyPromiseTest'))
tests.append(make(lazytools.c_promise, 'CPromiseTest'))


def make(promiseproperty, label):

    class PromisePropertyTest(unittest.TestCase):

        def test_setattr(self):

            run = []

            class test(object):

                @promiseproperty
                def test1(self):
                    run.append(1)
                    return 1

                @promiseproperty
                def test2(self):
                    run.append(2)
                    return 2

            ob = test()

            self.assert_(not ob.__dict__)
            self.assertEqual(ob.test1, 1)
            self.assert_('test1' in ob.__dict__)
            self.assertEqual(ob.test2, 2)
            self.assert_('test2' in ob.__dict__)
            self.assertEqual(run, [1, 2])

            self.assertEqual(len(ob.__dict__), 2)
            self.assertEqual(ob.test1, 1)
            self.assertEqual(ob.test2, 2)
            self.assertEqual(run, [1, 2])

            self.assertEqual(ob.__dict__, {'test1': 1, 'test2': 2})

        def test_explicit_name(self):

            class test(object):

                def foo(self):
                    return 1

                bar = promiseproperty(foo, 'bar')

            ob = test()

            self.assertNotEqual(ob.foo, 1)
            self.assertEqual(ob.bar, 1)
            self.assert_('bar' in ob.__dict__)
            self.assert_('foo' not in ob.__dict__)

        def test_implicit_doc(self):

            class test(object):

                @promiseproperty
                def test(self):
                    """docstring"""
                    return 1

            self.assertEqual(test.test.__doc__, 'docstring')

        def test_explicit_doc(self):

            class test(object):

                def test(self):
                    return 1
                test = promiseproperty(test, doc='docstring')

            self.assertEqual(test.test.__doc__, 'docstring')

        def test_explicits(self):

            class test(object):

                def foo(self):
                    return 1
                bar = promiseproperty(foo, 'bar', 'docstring')

            self.assertEqual(test.bar.__doc__, 'docstring')
            self.assertEqual(test().bar, 1)

    return type(label, (PromisePropertyTest,), {})

tests.append(make(lazytools.py_promiseproperty, 'PyPromisePropertyTest'))
tests.append(make(lazytools.c_promiseproperty, 'CPromisePropertyTest'))


def make(lazymapping, label):

    class LazyMappingTest(unittest.TestCase):

        def test_basic(self):

            run = []

            def mul2(x):
                run.append(x)
                return 2 * x

            lm = lazymapping(mul2)
            for x in xrange(10):
                self.assertEqual(lm[x], 2 * x)
            for x in xrange(10):
                self.assertEqual(lm[x], 2 * x)

            self.assertEqual(run, range(10))

    return type(label, (LazyMappingTest,), {})

tests.append(make(lazytools.py_lazymapping, 'PyLazyMappingTest'))
tests.append(make(lazytools.c_lazymapping, 'CLazyMappingTest'))


def test_main():
    test_support.run_unittest(*tests)

if __name__ == '__main__':
    test_main()
