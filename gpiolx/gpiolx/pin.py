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

__version__ = '$Id: pin.py 120 2017-03-07 08:05:10Z dima $'
__all__ = ['GPIOPin']

def ctwise(meth):
    def ctwisemethod(self, *args, **kwargs):
        return getattr(self.ct, meth)(self.pc.pin, *args, **kwargs)
    return ctwisemethod

class GPIOPin(object):

    def __init__(self, pc, ct=None):
        self.pc = pc
        self.ct = ct

    def __repr__(self):
        return ' '.join(self._reprgen())

    def __str__(self):
        return '%s(%d)' % (self.name, self.pin)

    def _reprgen(self):
        yield '<%s' % type(self).__name__
        yield '#%d' % self.pin
        if self.namedp():
            yield '"%s"' % self.name
        yield '@ 0x%x>' % id(self)

    def namedp(self):
        return self.name != 'pin %d' % self.pin

    @property
    def name(self):
        return self.pc.name

    @property
    def pin(self):
        return self.pc.pin

    @property
    def flags(self):
        return self.pc.flags

    # XXX: do this w/ a loop..
    get = ctwise('get')
    inp = ctwise('inp')
    input = ctwise('input')
    high = ctwise('high')
    low = ctwise('low')
    off = ctwise('off')
    on = ctwise('on')
    outp = ctwise('outp')
    output = ctwise('output')
    set = ctwise('set')
    set_flags = ctwise('set_flags')
    set_name = ctwise('set_name')
    toggle = ctwise('toggle')
    rctime = ctwise('rctime')

    def __eq__(self, other):
        return self.pin == other or self.name == other
