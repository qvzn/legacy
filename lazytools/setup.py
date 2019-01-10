import os
from distutils.core import setup, Extension

srcs = ['lazytools.c', 'promise.c', 'promiseproperty.c', 'lazymapping.c']
srcs = [os.path.join('src', x) for x in srcs]

if 'DEBUG_CFLAGS' in os.environ:
    os.environ['CFLAGS'] = '\
-std=c99 -pedantic -Wall -Wcast-align -Wcast-qual -Wpointer-arith \
-Wchar-subscripts -Winline -Wnested-externs -Wbad-function-cast \
-Wunreachable-code -Werror'

setup(name='lazytools',
      version='0.6',
      description='Fast tools to support deferred (lazy) evaluation',
      author='Dima Dorfman',
      author_email='dima+pyext@trit.org',
      url='http://www.trit.org/~dima/',
      license='BSD',
      py_modules=['lazytools'],
      ext_modules=[Extension('_lazytools', srcs)])
