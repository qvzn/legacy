#
# Copyright (c) 2018 Trit Networks.
# All rights reserved.
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
# $Trit_Id: resolver.py 6088 2018-03-16 23:47:40Z dima $
#

__revision__ = '$Id: qresolver.py 164 2019-01-07 12:59:29Z dima $'

__all__ = ['dns', 'Resolver', 'render', 'render_txt']

import dns
import dns.resolver

class Resolver(dns.resolver.Resolver):

    def __init__(self, *args, **kwargs):
        self._kwargs = dict(kwargs)
        try:
            self._at = self._kwargs.pop('at')
        except KeyError:
            self._doat = False
            kwa = {}
        else:
            self._doat = True
            kwa = {'configure': True}
        super(Resolver, self).__init__(*args, **kwa)
        self.do_configure()

    def do_configure(self):
        if self._doat:
            self.configure_at()
        for k, v in self._kwargs.iteritems():
            assert hasattr(self, k), 'invalid configure option, %s' % k
            setattr(self, k, v)

    def configure_at(self):
        self.nameservers = self._at

    def retarget(self, target, keepconf=True):
        kwa = self._kwargs if keepconf else {}
        return self.__class__(at=map(str, self.resolve(target)), **kwa)

    def hostname_bind(self, **kwargs):
        try:
            return self.chaos_txt('hostname.bind')
        except dns.exception.DNSException, e:
            #return '<Exception: %s>' % type(e)
            return None         # XXX

    def query_ns(self, domain):
        return [str(self.resolve(x.target.to_text(True)))
                for x in self.query(domain, 'ns')]

    def chaos_txt(self, name, *args, **kwargs):
        return self.query_txt(name, dns.rdataclass.CH, *args, **kwargs)

    def query_txt(self, name, *args, **kwargs):
        return self.query1(name, dns.rdatatype.TXT, *args, **kwargs)

    def query_any(self, name, *args, **kwargs):
        return self.multiquery(name, ('A', 'AAAA'), *args, **kwargs)

    def multiquery(self, name, types, *args, **kwargs):
        for t in types:
            try:
                for x in self.query(name, t, *args, **kwargs):
                    yield x
            except dns.resolver.NoAnswer:
                pass

    def query1(self, *args, **kwargs):
        if 'multi' not in kwargs:
            kwargs = dict(kwargs, multi=False)
        return self.query_x(*args, **kwargs)

    def query_x(self, *args, **kwargs):
        multi = kwargs.pop('multi', True)
        aa = self.query(*args, **kwargs)
        if multi:
            return aa
        elif len(aa) == 1:
            return aa[0]
        else:
            raise ValueError, 'query_x multi conflict (%d)' % len(aa)

    def resolve(self, name, raise_nxdomain=True):
        L = list(self.gen_resolve(name))
        if not L and raise_nxdomain:
            raise dns.resolver.NXDOMAIN, name
        return L

    def gen_resolve(self, name, variants=['A', 'AAAA']):
        for vk in variants:
            try:
                aa = self.query(name, vk)
            except dns.exception.DNSException:
                pass
            else:
                for ax in aa:
                    yield ax

    def __repr__(self):
        return ' '.join(self.gen_repr_ober())

    def gen_repr_ober(self):
        yield '<%s object' % self.__class__.__name__
        for x in self.gen_repr():
            yield x
        yield 'at 0x%x>' % id(self)

    def gen_repr(self):
        yield 'ns=%r' % self.nameservers

def render(rdata):
    if hasattr(rdata, 'rdtype'):
        if rdata.rdtype == dns.rdatatype.TXT:
            return render_txt(rdata)
        elif rdata.rdtype == dns.rdatatype.NS:
            return str(rdata).rstrip('.')
    return str(rdata)

def render_txt(txtdata):
    try:
        if len(txtdata.strings) == 1:
            return txtdata.strings[0]
    except AttributeError:
        pass
    return str(txtdata)
