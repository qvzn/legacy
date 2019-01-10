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

__version__ = '$Id: __init__.py 120 2017-03-07 08:05:10Z dima $'
__all__ = ['GPIO', 'GPIOPin', 'z', 'gpio']

import _gpiolx
from _gpiolx import *
from gpio import GPIO
from pin import GPIOPin

__all__ += dir(_gpiolx)

def load_global_consts():
    for x in dir(_gpiolx):
        if x.startswith('GPIO_'):
            s = x[5:]
            if s not in globals():
                globals()[s] = getattr(_gpiolx, x)
                __all__.append(s)

load_global_consts()

z = gpio = GPIO()
