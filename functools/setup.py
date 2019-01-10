import os
from distutils.core import setup, Extension

srcs = ['functools.c', 'compose.c', 'fastcut.c']
srcs = [os.path.join('src', x) for x in srcs]

if 'DEBUG_CFLAGS' in os.environ:
    os.environ['CFLAGS'] = '\
-std=c99 -pedantic -Wall -Wcast-align -Wcast-qual -Wpointer-arith \
-Wchar-subscripts -Winline -Wnested-externs -Wbad-function-cast \
-Wunreachable-code -Werror'

setup(name='functools',
      version='0.5',
      description='Fast tools for functional programming',
      author='Dima Dorfman',
      author_email='dima+pyext@trit.org',
      url='http://www.trit.org/~dima/',
      license='BSD',
      py_modules=['functools'],
      ext_modules=[Extension('_functools', srcs)])
