#
# Copyright (c) 2005 Dima Dorfman.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#

__all__ = ['promise', 'promiseproperty', 'lazymapping']
__revision__ = '$Dima: pylib/lazytools/lazytools.py,v 1.3 2005/08/22 00:38:25 dima Exp $'


class promise(object):

    def __init__(self, thunk):
        self.thunk = thunk

    def __call__(self):
        try:
            return self.result
        except AttributeError:
            self.result = self.thunk()
            del self.thunk
            return self.result

    def __repr__(self):
        if hasattr(self, 'result'):
            return '<promise object (forced) at 0x%x>' % id(self)
        else:
            return '<promise object at 0x%x>' % id(self)


class promiseproperty(object):

    def __init__(self, sub, name=None, doc=None):
        self.sub = sub
        if name is None:
            name = getattr(sub, '__name__', None)
            if name is None:
                raise TypeError, 'promiseproperty requires sub.__name__ ' \
                      'or for a name to be specified explicitly'
        self.name = name
        if doc is None:
            doc = getattr(sub, '__doc__', None)
        self.__doc__ = doc

    def __get__(self, obj, type):
        if obj is None:
            return self
        res = self.sub(obj)
        setattr(obj, self.name, res)
        return res


class lazymapping(object):

    def __init__(self, make):
        self.make = make
        self.values = {}

    def __getitem__(self, key):
        try:
            return self.values[key]
        except KeyError:
            value = self.values[key] = self.make(key)
            return value


for x in __all__:
    globals()['py_%s' % x] = globals()[x]
del x

try:
    import _lazytools
except ImportError:
    pass
else:
    for x in __all__:
        globals()['c_%s' % x] = globals()[x] = getattr(_lazytools, x)
    del x
