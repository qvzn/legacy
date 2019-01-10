#! /usr/bin/env python
#
# Copyright (c) 2018-2019 Dima Dorfman.
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
# $Trit_Id: nsreport.py 6111 2018-03-17 08:07:42Z dima $
#

__revision__ = '$Id: nsreport.py 176 2019-01-07 15:11:29Z dima $'

import argparse
import itertools
import qresolver

try:
    import qcymru
except ImportError:
    qcymru = None

try:
    from lazytools import promise
except ImportError:
    # From lazytools-0.6 package
    # Copyright (c) 2005 Dima Dorfman. [BSD License]
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

def addboolopt(parser, key, short=None, **kwargs):
    if 'dest' not in kwargs:
        kwargs = dict(kwargs, dest=key.replace('-', '_'))
    if 'help' in kwargs:
        enword, disword = kwargs.pop('endis', ('Enable', 'Disable'))
        enkw = dict(kwargs, help='%s %s' % (enword, kwargs['help']))
        diskw = dict(kwargs, help='%s %s' % (disword, kwargs['help']))
    else:
        enkw = diskw = kwargs
    if 'en_action' in enkw:
        enkw = dict(enkw, action=enkw['en_action'])
        del enkw['en_action']
        diskw = dict(diskw)
        del diskw['en_action']
    else:
        enkw = dict(enkw, action='store_true')
    disargs = ('--no-%s' % key,)
    if 'disopt' in enkw:
        disargs = (enkw['disopt'],) + disargs
        del enkw['disopt']
        del diskw['disopt']
    enkey = '--%s' % key
    enargs = (enkey,) if short is None else (short, enkey)
    parser.add_argument(*enargs, **enkw)
    parser.add_argument(*disargs, action='store_false', **diskw)

class CustomActionMixin(object):

    def alter_namespace(self, parser, ns):
        pass

    def __call__(self, parser, namespace, *args, **kwargs):
        self.alter_namespace(parser, namespace)
        super(CustomActionMixin, self).__call__(
            parser, namespace, *args, **kwargs)

class DisableBriefActionMixin(CustomActionMixin):

    def alter_namespace(self, parser, ns):
        super(DisableBriefActionMixin, self).alter_namespace(parser, ns)
        ns.brief = False

class TrueNonBriefAction(DisableBriefActionMixin, argparse._StoreTrueAction):
    pass

class CustomExtraAction(DisableBriefActionMixin, argparse._AppendAction):

    def alter_namespace(self, parser, ns):
        super(CustomExtraAction, self).alter_namespace(parser, ns)
        ns.chaos = True

def nice_cli(thunk, parser, *args, **kwargs):
    error = kwargs.pop('error', None)
    def excp():
        try:
            return getattr(parser.args, 'exception', False)
        except AttributeError:
            return True
    try:
        return thunk(parser, *args, **kwargs)
    except KeyboardInterrupt:
        if excp():
            raise
    except Exception, e:
        if error is None or excp():
            raise
        error('Exception: %s' % e)

render = qresolver.render

def main():
    parser = argparse.ArgumentParser(version=__revision__)
    nice_cli(main2, parser, error=parser.error)

def main2(parser):

    #addboolopt(parser, 'asn', '-A', dest='cymru', en_action=TrueNonBriefAction,
    addboolopt(parser, 'asn', '-A', dest='cymru',
                        help='Cymru ASN lookup')
    addboolopt(parser, 'brief', '-b', disopt='-a', default=True,
                        help='brief output')
    addboolopt(parser, 'chaos', '-C',
                        help='hostname.bind (CHAOS) report')
    addboolopt(parser, 'exception', default=False, help='exception output')
    parser.add_argument('-E', '--extra-txt', action=CustomExtraAction,
                        default=[],
                        help='Extra TXT records to query from each nameserver (changes default to non-brief mode')
    parser.add_argument('-l', '--lifetime', type=float,
                        help='DNS Resolver lifetime')
    addboolopt(parser, 'resolver-id', '-R',
                        help='resolver ID report (CHAOS/hostname.bind)')
    parser.add_argument('-r', '--resolver', action='append',
                        help='Specify explicit resolvers')
    addboolopt(parser, 'soa', default=True,
                        help='SOA serial report')
    parser.add_argument('-t', '--timeout', type=float,
                        help='DNS Resolver timeout')
    parser.add_argument('domain', help='Domain name to be looked up')

    args = parser.parse_args()
    # XXX: for nice_cli
    parser.args = args

    kwa = {}
    if args.resolver:
        kwa['at'] = args.resolver
    for kx in 'lifetime', 'timeout':
        val = getattr(args, kx)
        if val is not None:
            kwa[kx] = val
    rr = qresolver.Resolver(**kwa)
    if args.resolver_id:
        print 'Resolver: %s' % qresolver.render_txt(rr.hostname_bind())
    for x in sorted(rr.query(args.domain, 'ns')):
        xtarget = x.target
        def gen():
            r2 = promise(lambda: rr.retarget(xtarget))
            @promise
            def serial():
                try:
                    return '#%s' % r2().query(args.domain, 'soa')[0].serial
                except qresolver.dns.exception.DNSException:
                    return '#---'
            if args.brief:
                yield None, render(x)
            else:
                fx = {'x': render(x)}
                if args.chaos:
                    hb = r2().hostname_bind()
                    fx['chaos'] = hb
                if args.soa:
                    fx['serial'] = serial()
                yield None, fx
            if args.brief:
                if args.soa:
                    yield 'serial', serial()
                if args.cymru:
                    yield None, '(%s)' % brief_ips_with_asn(rr, xtarget)
                else:
                    yield None, '(%s)' % ' '.join(
                        map(qresolver.render, rr.query_any(xtarget)))
            else:
                for s, t in ('IPv4', 'A'), ('IPv6', 'AAAA'):
                    try:
                        rd = rr.query(xtarget, t)
                    except qresolver.dns.resolver.NoAnswer:
                        pass
                    else:
                        renderer = render_with_asn(rr) if args.cymru else render
                        yield s, ', '.join(map(renderer, rd))
            if args.chaos and args.brief:
                yield 'hostname.bind', r2().hostname_bind()
            for ex in args.extra_txt:
                try:
                    yield ex, r2().query_txt(ex)
                except qresolver.dns.exception.DNSException, e:
                    yield ex, '[Exception: %s]' % e
        if args.brief:
            print ' '.join(str(x[1]) for x in gen())
        else:
            for i, (k, v) in enumerate(gen()):
                if i == 0:
                    assert k is None
                    s = render(v['x'])
                    if 'serial' in v:
                        s += ' %s' % v['serial']
                    if 'chaos' in v:
                        s += ' <%s>' % render(v['chaos'])
                    print '=> %s' % s
                else:
                    v = render(v)
                    print '\t%s: %s' % (k, v)

def brief_ips_with_asn(rr, x):
    ip2asn_ = lambda target: ip2asn(target, rr)
    all_ips = [(e, ip2asn_(e)) for e in rr.query_any(x)]
    all_ips.sort(key=lambda w: (w[1].asn, w[0]))
    def gen():
        for asn, ips in itertools.groupby(all_ips, lambda w: w[1].asn):
            ipL = []
            acv = None
            for ipx in ips:
                if acv is None:
                    acv = ipx[1]
                ipL.append(ipx[0])
            yield '%s [%s]' % (' '.join(map(render, ipL)), acv.asnrepr())
    return ', '.join(gen())

def render_with_asn(rr):
    def renderer_with_asn(x):
        cv = ip2asn(x, rr)
        return '%s [%s]' % (render(x), cv.asnrepr())
    return renderer_with_asn

def ip2asn(target, rr):
    if qcymru is None:
        raise ApplicationError, 'Cymru lookup not supported (missing qcymru module)'
    cx = qcymru.ip2asn(str(target))
    return cx

if __name__ == '__main__':
    main()
