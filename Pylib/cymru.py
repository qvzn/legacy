##
## Copyright (c) 2014 Dima Dorfman.
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
## $qvzn/Id: cymru.py 838 2014-10-23 02:31:06Z dima $
##
## cymru.py - Python interface to [*.]asn.cymru.com DNS zones
##

__all__ = ['CymruError', 'CymruView', 'ip2asn', 'nibble6']

import socket
import dns.exception, dns.resolver

class CymruError(Exception):
    pass

class CymruView(object):

    def __init__(self, querydomain, ipaddr, qs):
        self.__querydomain = querydomain
        self.ipaddr = ipaddr
        self.asn, self.prefix, self.cc, self.rir, self.regdate = self._cymruquery(qs)

    def _cymruquery(self, querystring, reqargs=5):
        qs = '%s.%s' % (querystring, self.__querydomain)
        try:
            for ans in dns.resolver.query(qs, 'TXT'):
                if len(ans.strings) < 1:
                    continue
                s = ans.strings[0].split('|')
                if len(s) != reqargs:
                    continue
                return [x.strip() for x in s]
        except dns.resolver.NXDOMAIN:
            raise CymruError, 'NXDOMAIN: %s' % qs
        except dns.exception.DNSException, e:
            raise CymruError, 'DNS error: [%s] %s' % (type(e), e)
        raise CymruError, 'no suitable DNS reply'

    def loadasndata(self):
        if hasattr(self, '_asndataloaded'):
            return
        self.asnasn, self.asncc, self.asnrir, self.asnregdate, self._asndescr = \
            self._cymruquery('AS%s' % self.asn)
        self.asnparsed = self._parseasndata()
        self._asndataloaded = True

    def _parseasndata(self):
        ap = {}
        s = self._asndescr

        # Strip training ,CC
        if s.endswith(',%s' % self.asncc):
            ap['cc'] = s[-3:]
            s = s[:-3]
        else:
            ap['cc'] = ''

        # Mindless attempt which _assumes_ there's an object prefix
        sx = s.split(' - ', 1)
        if len(sx) > 1:
            ap['object'], ap['descr'] = sx
        else:
            ap['object'] = ''
            ap['descr'] = s

        return ap

    @property
    def asndescr(self):
        self.loadasndata()
        return self.asnparsed['descr']

    @staticmethod
    def from_inet(querydomain, ipaddr):
        s = ipaddr.split('.')
        if len(s) != 4:
            raise CymruError, 'bad IP4 address'
        return CymruView(querydomain, ipaddr, '.'.join(s[::-1]) + '.origin')

    @staticmethod
    def from_inet6(querydomain, ipaddr):
        return CymruView(querydomain, ipaddr, nibble6(ipaddr) + '.origin6')

def nibble6(ipaddr):
    assert ':' in ipaddr and '.' not in ipaddr
    nx = socket.inet_pton(socket.AF_INET6, ipaddr)
    return '.'.join('%x.%x' % divmod(ord(x), 16) for x in nx)[::-1]

def ip2asn(ipaddr, querydomain='asn.cymru.com'):
    if not ipaddr or (':' in ipaddr and '.' in ipaddr):
        raise CymruError, 'invalid IP address'
    elif ':' in ipaddr:
        return CymruView.from_inet6(querydomain, ipaddr)
    elif '.' in ipaddr:
        return CymruView.from_inet(querydomain, ipaddr)
    else:
        raise CymruError, 'not supposed to happen'
