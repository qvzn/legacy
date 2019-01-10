##
## Copyright (c) 2017, Dima Dorfman.
## All rights reserved.
##
## Permission to use, copy, modify, and/or distribute this software for any
## purpose with or without fee is hereby granted, provided that the above
## copyright notice and this permission notice appear in all copies.
##
## THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
## WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
## MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
## ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
## WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
## ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
## OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
##
## $Id: setup.py 141 2017-05-29 05:52:12Z dima $
##

import os
from distutils.core import setup, Extension

WFLAGS = [
    '-Wall',
    '-Wcast-align', '-Wcast-qual',
    '-Wpointer-arith', '-Wchar-subscripts', '-Wunreachable-code',
]

MYCFLAGS = WFLAGS + ['-std=c99']

allsrc = [os.path.join('src', x) for x in os.listdir('src')]
srcs = [x for x in allsrc if x.endswith('.c')]

gpiolxext = Extension(
    'gpiolx._gpiolx',
    srcs,
    include_dirs=['src'],
    extra_compile_args = MYCFLAGS,
    libraries = ['gpio'],
)

setup(name='gpiolx',
      version='0.6.1',
      description='High-level GPIO interface for FreeBSD with software PWM',
      author='Dima Dorfman',
      platforms=['FreeBSD'],
      license='BSD',
      packages=['gpiolx'],
      ext_modules=[gpiolxext])
