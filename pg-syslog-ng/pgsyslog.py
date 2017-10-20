#! /usr/bin/env python
#
# Copyright (c) 2014 Dima Dorfman. All rights reserved.
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
# $qvzn/Id: pgsyslog.py 268 2016-07-30 06:55:29Z dima $

# TODO:
#  - atrun/save-entropy summarization
#  - some sort of n% mail n% sshd etc

SYSLOG_COLUMNS = 'seq, stamp, host, msg, facility, priority, tag, program, date, time'

import datetime
import operator
import os
import psycopg2, psycopg2.extras
import signal
import sys
import time

now = datetime.datetime.utcnow


class ApplicationError(Exception):
    pass


class statcounter(object):

    def __init__(self):
        self.reset()

    def reset(self):
        self.nrec = 0
        self.first = None
        self.htab = {}
        self.ftab = {}
        self.ltab = {}
        self.ptab = {}

    def enter(self, rec):
        self.nrec += 1
        if self.first is None:
            self.first = rec
        self.count(self.htab, rec['host'])
        self.count(self.ftab, rec['facility'])
        self.count(self.ltab, rec['priority'])
        self.count(self.ptab, rec['program'])

    def count(self, tab, k):
        try:
            tab[k] = tab[k] + 1
        except KeyError:
            tab[k] = 1

    def report(self):
        rs = []
        rs.append('Processed %d records spanning %s' % (
            self.nrec, deltaformat(now() - self.first['stamp'])))
        rs.append('Top 5 hosts:\t' +
                  '\n\t\t'.join('%.2f%%\t%s' % (v, k)
                                for k, v in self.topnstat(self.htab)))
        def ntopn(what, tab, sep='\t'):
            rs.append('Top 5 %s:%s' % (what, sep) +
                      ' '.join('%s(%.2f%%)' % x for x in self.topnstat(tab)))
        ntopn('facility', self.ftab)
        ntopn('priority', self.ltab)
        ntopn('programs', self.ptab, '\n\t')

        return '\n'.join(rs)

    def topnstat(self, tab, n=5):
        total = sum(tab.itervalues())
        for i, (x, v) in enumerate(sorted(tab.iteritems(), key=operator.itemgetter(1),
                                          reverse=True)):
            if i >= n:
                return
            yield x, 100. * v / total


class logprinter(object):

    def __init__(self, options):
        self.options = options
        self.stats = statcounter()
        self.maxseq = 0
        self.count = 0

    def pplog(self, rec):
        seq = rec['seq']
        if seq <= self.maxseq:
            print 'WARNING! syslog pgdb sequence going wrong way! %d . %d' % (self.maxseq, seq)
        self.maxseq = seq
        self.count += 1
        self.prec(rec)
        self.stats.enter(rec)

    def prec(self, rec):
        slstamp = datetime.datetime.combine(rec['date'], rec['time'])
        print stampformat(slstamp),
        if self.options.print_full:
            dbstamp = rec['stamp']
            td = dbstamp - slstamp
            print '%(host)s %(facility)s.%(priority)s prog=%(program)s tag=%(tag)s' % rec,
            print 'delay=%d' % td.total_seconds()
            print '\t%(msg)s' % rec
            print '-' * 40
        else:
            pr = dict(rec)
            if pr['program']:
                pr['_print_program'] = ': '
            else:
                pr['program'] = ''
                pr['_print_program'] = ''
            if self.options.print_priority:
                print '%(host)s [%(facility)s.%(priority)s] %(program)s%(_print_program)s%(msg)s' % pr
            else:
                print '%(host)s %(program)s%(_print_program)s%(msg)s' % pr

    def precs(self, recs):
        for rec in recs:
            self.pplog(rec)

    def print_summary(self):
        if self.count > 0:
            print >> sys.stderr, '(%d records printed)' % self.count
            self.print_stats()

    def print_stats(self):
        linesep(sys.stderr)
        print >> sys.stderr, self.stats.report()
        linesep(sys.stderr)


class poller(object):

    def __init__(self, slf, options):
        self.slf = slf
        self.interval = options.poller_interval
        self.elapsenote = options.poller_elapsenote
        self.initial_page = options.poller_initial_page
        self.siginfoflag = False

    def siginfohandler(self, signum, frame):
        self.slf.logprinter.print_stats()

    def start(self):
        if hasattr(signal, 'SIGINFO'):
            signal.signal(signal.SIGINFO, self.siginfohandler)
        curs = self.slf.getcursor()
        iwait = conswaiter()
        try:
            self.slf.select(curs, ['ORDER BY stamp DESC', 'LIMIT %d' % self.initial_page],
                            outer='SELECT * FROM (%s) AS x ORDER BY x.stamp')
            data = curs.fetchall()
            if not data:
                raise EnvironmentError, 'polling not supported with no initial results'
            mseq = max(x[0] for x in data)
            lastdata = lastpoll = now()
            self.slf.logprinter.precs(data)
            while True:
                nw = now()
                clrn = iwait(self.interval, 'Polling... since %s... no new data for %.3f s...' % (
                    stampformat(lastdata), (nw - lastdata).total_seconds()))
                self.slf.select2(curs, 'seq > %(mseq)s', ['ORDER BY stamp DESC'],
                                 sqla={'mseq': mseq},
                                outer='SELECT * FROM (%s) AS x ORDER BY x.stamp')
                lastpoll = now()
                data = curs.fetchall()
                if data:
                    if clrn is not None:
                        print '\r%s' % (' ' * clrn),
                    print '\r',
                    delta = nw - lastdata
                    if self.elapsenote > 0 and delta.seconds >= self.elapsenote:
                        print '%s %s elapsed...' % ('=' * 70, delta)
                    mseq = max(x[0] for x in data)
                    lastdata = nw
                    self.slf.logprinter.precs(data)
        finally:
            curs.close()


class syslogfilter(object):

    def __init__(self, options, logstable='logs'):
        self.verbose = options.verbose
        self.logstable = logstable
        self.connect(options)
        self.setfilter(options)
        self.logprinter = logprinter(options)

    def shutdown(self):
        if self.pgdb is not None:
            self.pgdb.close()
            self.pgdb = None
        if self.logprinter is not None:
            self.logprinter.print_summary()
            self.logprinter = None

    def connect(self, options):
        fn = options.dbconnfile
        if not fn:
            fn = os.getenv('SYSLOG_PGDB')
        if not fn:
            raise EnvironmentError, '-d option is required to specify database'
        with open(fn) as f:
            self.pgdb = psycopg2.connect(f.read())

    def getcursor(self):
        return self.pgdb.cursor(cursor_factory=psycopg2.extras.DictCursor)

    def filteraddwhere(self, key, values, *args, **kwargs):
        if values is not None:
            return self.filteraddwhere1(key, values, *args, **kwargs)

    def filteraddwhere1(self, key, values, eqop='=', negation='!'):
        for value in values:
            if negation and len(value) > 1 and value[0] == '-':
                sign = '%s%s' % (negation, eqop)
                value = value[1:]
            else:
                sign = eqop
            k = 'sa%d%s' % (self.sqlacounter(), key)
            self.wcl.append('%s %s %%(%s)s' % (key, sign, k))
            self.sqla[k] = value

    def sqlacounter(self):
        # Yes this will return 1 first, who cares
        self.sqlc = self.sqlc + 1
        return self.sqlc

    def setfilter(self, options):
        self.sqla = {}
        self.sqlc = 0
        self.wcl = []
        if options.begindate or options.enddate:
            if not options.begindate or not options.enddate:
                raise ValueError, '--begin and --end must be specified together'
            self.wcl.append('stamp BETWEEN %(begindate)s::date AND %(enddate)s::date')
            self.sqla['begindate'] = options.begindate
            self.sqla['enddate'] = options.enddate
        elif options.interval:
            self.wcl.append('stamp > (now() - %(interval)s::interval)')
            self.sqla['interval'] = options.interval
        self.filteraddwhere('host', options.filter_host)
        self.filteraddwhere('facility', options.filter_facility)
        self.filteraddwhere('program', options.filter_program)
        self.filteraddwhere('msg', options.filter_posixre, '~*')
        self.filteraddwhere('msg', options.filter_like, 'LIKE', False)
        self.filteraddwhere('msg', options.filter_similar, 'SIMILAR TO', False)

    def mkstmt(self, cols, where='', clauses=()):
        ss = ['SELECT %s FROM %s' % (cols, self.logstable)]
        wcl = list(self.wcl)
        if where:
            wcl.append(where)
        if wcl:
            ss.append('WHERE ' + ' AND '.join(wcl))
        ss.extend(clauses)
        return ' '.join(ss)

    def cexec(self, c, statement, sqla=None):
        if sqla is None:
            sqla = self.sqla
        else:
            d = self.sqla.copy()
            d.update(sqla)
            sqla = d
        self.vlogsql(statement, sqla)
        c.execute(statement, sqla)

    def vlogsql(self, statement, sqla):
        if self.verbose:
            print >> sys.stderr, '=' * 40
            print >> sys.stderr, 'ARG: %r' % sqla
            print >> sys.stderr, 'SQL: %s' % statement
            print >> sys.stderr, '=' * 40

    def select(self, cursor, clauses=(), cols=SYSLOG_COLUMNS, outer=''):
        self.select2(cursor, clauses=clauses, cols=cols, outer=outer)

    def select2(self, cursor, where='', clauses=(), outer='', cols=SYSLOG_COLUMNS, sqla=None):
        s = self.mkstmt(cols, where, clauses)
        if outer:
            s = outer % s
        self.cexec(cursor, s, sqla=sqla)

    def selectrow(self, cursor, cols):
        self.cexec(cursor, self.mkstmt(cols))
        return cursor.fetchone()

class runmodeswitch(object):

    def __init__(self, slf):
        self.slf = slf

    def start(self, options):
        try:
            f = getattr(self, 'start_%s' % options.mode)
        except AttributeError:
            raise ApplicationError, 'unsupported mode: %r' % options.mode
        f(options)

    def start_poller(self, options):
        poller(self.slf, options).start()

    def start_tail(self, options):
        c = self.slf.getcursor()
        try:
            self.slf.select(c, ['ORDER BY stamp DESC', 'LIMIT %d' % options.tailcount],
                        outer='SELECT * FROM (%s) AS x ORDER BY x.stamp')
            self.slf.logprinter.precs(c.fetchall())
        finally:
            c.close()

    def start_stats_simple(self, options):
        self.start_stats(options, True)

    def start_stats(self, options, simple=False):
        def summary(labelfmt, sqlcols):
            self.slf.select(c, cols=sqlcols)
            print labelfmt % c.fetchone()[0]
        if 'interval' in self.slf.sqla:
            print '[Interval]:\t\t\t\t%s' % self.slf.sqla['interval']
        c = self.slf.getcursor()
        try:
            summary('Records in filtered view (total):\t%d', 'count(*)')
            if not simple:
                summary('Distinct hosts:\t\t\t\t%d', 'count(distinct host)')
                summary('First record:\t\t\t\t%s', 'min(stamp)')
                summary('Last record:\t\t\t\t%s', 'max(stamp)')
        finally:
            c.close()

    def start_hosts(self, options):
        c = self.slf.getcursor()
        try:
            self.slf.select(c, cols='DISTINCT host')
            hosts = [x[0] for x in c.fetchall()]
        finally:
            c.close()
        for host in hosts:
            print host
        print >> sys.stderr, '(%d host%s)' % (len(hosts), len(hosts) != 1 and 's' or '')

    def start_hstats(self, options):
        c = self.slf.getcursor()
        try:
            self.slf.cexec(c, 'SELECT x.host, (%s) FROM (%s) AS x ORDER BY COUNT DESC' % (
                self.slf.mkstmt('COUNT(*)', 'host = x.host'),
                self.slf.mkstmt('DISTINCT host')))
            data = c.fetchall()
            hosts, counts = zip(*data)
            w = max(map(len, hosts))
            fmt = '%%%ds\t%%d' % w
            for host, count in data:
                print fmt % (host, count)
            print >> sys.stderr, '[%s]' % domainstatsf(hosts)
            print >> sys.stderr, '(%d hosts, %d records)' % (len(hosts), sum(counts))
        finally:
            c.close()

    def start_changes(self, options):
        c = self.slf.getcursor()
        def gethosts():
            self.slf.select2(c, 'stamp BETWEEN timestamp %(curr)s AND timestamp %(cend)s',
                             cols='DISTINCT host',
                             sqla={'curr': curr, 'cend': cend})
            return set(map(operator.itemgetter(0), c.fetchall()))
        td = datetime.timedelta(hours=options.chours)
        try:
            curr, = self.slf.selectrow(c, 'MIN(stamp)')
            xhs = None
            buf = []
            while True:
                cend = curr + td
                hs = gethosts()
                if not hs:
                    print '<%s> Ending with %d hosts' % (stampformat(curr), len(xhs))
                    return
                if not xhs:
                    assert not buf
                    print '<%s> Starting with %d hosts' % (stampformat(curr), len(hs))
                else:
                    for x in buf:
                        print x
                    buf = []
                    lost = xhs - hs
                    boot = hs - xhs
                    if lost or boot:
                        buf.append('[%s - %s]' % (stampformat(curr), stampformat(cend)))
                        if lost:
                            buf.append('- %s' % ' '.join(lost))
                        if boot:
                            buf.append('+ %s' % ' '.join(boot))
                xhs = hs
                curr = cend
        finally:
            c.close()


def optparseconfig():
    import optparse
    parser = optparse.OptionParser('usage: %prog [options]', add_help_option=False)
    parser.set_defaults(verbose=False, mode='stats_simple')
    parser.add_option('', '--help', action='help', help='show this help message and exit')

    def storeandmode(realdest, modevalue):
        def optioncb(option, opt_str, value, parser):
            setattr(parser.values, realdest, value)
            setattr(parser.values, 'mode', modevalue)
        return optioncb
    modegroup = optparse.OptionGroup(parser, 'Running mode options')
    modegroup.add_option('-n', type='int', action='callback',
                         callback=storeandmode('tailcount', 'tail'),
                         help='Display the last N records in view (tail mode)')
    modegroup.add_option('-P', dest='mode', action='store_const', const='poller',
                         help='Enable polling mode')
    modegroup.add_option('', '--stats', dest='mode', action='store_const', const='stats',
                         help='Display statistics about the filtered view')
    modegroup.add_option('', '--hosts', dest='mode', action='store_const', const='hosts',
                         help='List distinct hosts in the filtered view')
    modegroup.add_option('-H', '--hstats', dest='mode', action='store_const', const='hstats',
                         help='Provide per-host statistics')
    modegroup.add_option('', '--changes', type='int', action='callback',
                         callback=storeandmode('chours', 'changes'),
                         help='XXX')
    parser.add_option_group(modegroup)

    dbgroup = optparse.OptionGroup(parser, 'Database connection options')
    dbgroup.add_option('-d', '--dbconnfile', dest='dbconnfile', type='string',
                      help='File containing PostgreSQL connection string; '\
                      'default read from SYSLOG_PGDB environment variable')
    dbgroup.add_option('-v', '--verbose', dest='verbose', action='store_true')
    parser.add_option_group(dbgroup)

    timegroup = optparse.OptionGroup(parser, 'Time filtering options')
    timegroup.add_option('-i', '--interval', dest='interval', type='string', default='8 hours',
                      help='SQL interval (time delta) expression')
    timegroup.add_option('-B', '--begin', dest='begindate', type='string')
    timegroup.add_option('-E', '--end', dest='enddate', type='string')
    parser.add_option_group(timegroup)

    simplefil = optparse.OptionGroup(parser, 'Simple column filtering options',
                                     'If the first character of the option value is a '
                                     'dash (-) the match sense will be reversed (i.e. NOT)')
    simplefil.add_option('-h', '--host', dest='filter_host', type='string', action='append')
    simplefil.add_option('-f', '--facility', dest='filter_facility', type='string', action='append')
    simplefil.add_option('-p', '--program', dest='filter_program', action='append',
                         help='Match program name')
    parser.add_option_group(simplefil)

    advfilter = optparse.OptionGroup(parser, 'Advanced filtering options')
    advfilter.add_option('-j', dest='filter_posixre', action='append',
                         help='Match message content using a POSIX regular expression; '
                              'it does not have to match the entire message')
    advfilter.add_option('', '--like', dest='filter_like', action='append',
                         help='Match message content using an SQL LIKE expression')
    advfilter.add_option('', '--similar', dest='filter_similar', action='append',
                         help='Match message content using an SQL SIMILAR TO expression')
    parser.add_option_group(advfilter)

    printgroup = optparse.OptionGroup(parser, 'Log message output options')
    printgroup.add_option('', '--print-priority', action='store_true')
    printgroup.add_option('', '--print-full', action='store_true')
    parser.add_option_group(printgroup)

    pollergroup = optparse.OptionGroup(parser, 'Polling mode options')
    pollergroup.add_option('', '--poll-interval', dest='poller_interval', type='float', default=0.5,
                      help='How often to poll the database in polling mode')
    pollergroup.add_option('', '--poll-elapsenote', dest='poller_elapsenote', type='float', default=60,
                      help='Print a notice if the time to the previous message exceeds this (seconds)')
    pollergroup.add_option('', '--poller-initial-page', type='int', default='25',
                           help='Number of records to fetch on initial query')
    parser.add_option_group(pollergroup)

    return parser

def main():
    parser = optparseconfig()
    options, args = parser.parse_args()
    if options.mode is None:
        parser.error('at least one running mode option is required')
    try:
        sf = syslogfilter(options)
    except EnvironmentError, e:
        parser.error('%s' % e)
    try:
        runmodeswitch(sf).start(options)
    finally:
        sf.shutdown()

def conswaiter(waitstr='\-/|', refresh=.1):
    ix = [0]
    def iwait(howlong, notice=''):
        t = time.time()
        while True:
            s = '%s [%s]' % (notice, waitstr[ix[0]])
            print '\r%s' % s,
            sys.stdout.flush()
            ix[0] = (ix[0] + 1) % len(waitstr)
            if time.time() - t >= howlong:
                return len(s)
            try:
                time.sleep(refresh)
            except KeyboardInterrupt:
                print
                raise
    return iwait

def hostdomain(h):
    return '.'.join(h.split('.')[-2:])

def domainstats(hs):
    d = {}
    for h in hs:
        hk = hostdomain(h)
        try:
            d[hk] = d[hk] + 1
        except KeyError:
            d[hk] = 1
    return d

def domainstatsf(hs):
    d = domainstats(hs)
    return ' '.join('%s:%s' % (k, d[k]) for k in sorted(d.keys()))

def linesep(where=sys.stdout, n=50):
    print >> where, '-' * n

def stampformat(datestamp, format='%b %d %H:%M:%S'):
    return datestamp.strftime(format)

def deltaformat(td):
    s = []
    if td.days:
        s.append('%d days' % td.days)
    hours, rem = divmod(td.seconds, 3600)
    mins, secs = divmod(rem, 60)
    if hours:
        s.append('%d hours' % hours)
    if mins:
        s.append('%d minutes' % mins)
    s.append('%d seconds' % secs)
    return ', '.join(s)

if __name__ == '__main__':
    main()
