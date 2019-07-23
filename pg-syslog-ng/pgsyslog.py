#! /usr/bin/env python2
#
# Copyright (c) 2014, 2017, 2019 Dima Dorfman.
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

__version__ = '$Id: pgsyslog.py 304 2019-07-12 22:02:06Z dima $'

# TODO:
#  - atrun/save-entropy summarization
#  - expand IN filters to support LIKE or other wildcards

DEFAULT_DATE_FORMAT = '%b %d %H:%M:%S'
DEFAULT_INTERVAL = '24 hours'
DEFAULT_TAILCOUNT = 1000

SYSLOG_BASE_COLS = ['stamp', 'date', 'time', 'host', 'msg']
SYSLOG_ALL_COLS = SYSLOG_BASE_COLS + \
                  ['seq', 'facility', 'priority', 'tag', 'program']

import datetime
import operator
import os
import optparse
import psycopg2, psycopg2.extras
import signal
import sys
import time

now = datetime.datetime.utcnow

# Dynamic
LOCAL_TIMEZONE = None

class ApplicationError(EnvironmentError):
    pass

def app_error(s):
    raise ApplicationError, s


class statcounter(object):

    tab_cols_map = (
        ('htab', ('host',)),
        ('ftab', ('facility',)),
        ('ltab', ('priority',)),
        ('ptab', ('program', 'programs', '\n\t')),
    )

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
        for tabname, cnx in self.tab_cols_map:
            colname = cnx[0]
            if colname in rec:
                self.count(getattr(self, tabname), rec[colname])

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
        for tabname, cnx in self.tab_cols_map[1:]:
            tab = getattr(self, tabname)
            if tab:
                ntopn(cnx[1] if len(cnx) > 1 else cnx[0], tab, *cnx[2:])
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
        self.stats_on = not not options.print_stats
        self.track_seq = options.mode == 'poller'
        if self.track_seq:
            self.maxseq = 0
        self.count = 0

    def stampformat(self, datestamp, format=None):
        if format is None:
            format = self.options.date_format
        return stampformat(datestamp, format)

    def pplog(self, rec):
        if self.track_seq:
            seq = rec['seq']
            if seq <= self.maxseq:
                print >> sys.stderr, 'WARNING! syslog pgdb sequence going wrong way! %d . %d' % (self.maxseq, seq)
            self.maxseq = seq
        self.count += 1
        self.prec(rec)
        if self.stats_on:
            self.stats.enter(rec)

    def prec(self, rec):
        slstamp = datetime.datetime.combine(rec['date'], rec['time'])
        print self.stampformat(slstamp),
        if self.options.no_hostname:
            fmt = ''
        else:
            fmt = '%(host)s '
        if self.options.print_full:
            dbstamp = rec['stamp']
            td = dbstamp - slstamp
            fmt += '%(facility)s.%(priority)s prog=%(program)s tag=%(tag)s'
            print fmt % rec,
            print 'delay=%d' % td.total_seconds()
            print '\t%(msg)s' % rec
            print '-' * 40
        else:
            pr = dict(rec)
            pr['host'] = unquote_implied_domains(self.options, pr['host'])
            if pr['program']:
                pr['_print_program'] = ': '
            else:
                pr['program'] = ''
                pr['_print_program'] = ''
            if self.options.print_priority:
                fmt += '[%(facility)s.%(priority)s] %(program)s%(_print_program)s%(msg)s'
            else:
                fmt += '%(program)s%(_print_program)s%(msg)s'
            print fmt % pr

    def precs(self, recs):
        for rec in recs:
            self.pplog(rec)

    def print_summary(self):
        #if self.count > 0 and (self.options.print_stats or sys.stdout.isatty()):
        if self.count > 0 and self.options.print_stats:
            assert self.stats_on
            print >> sys.stderr, '(%d records printed)' % self.count
            self.print_stats()

    def print_stats(self):
        if not self.stats_on:
            return
        linesep(sys.stderr)
        print >> sys.stderr, self.stats.report()
        linesep(sys.stderr)


class poller(object):

    def __init__(self, slf, options):
        self.slf = slf
        self.interval = options.poller_interval
        self.elapsenote = options.poller_elapsenote
        self.initial_page = options.poller_initial_page
        self.output_progress = options.progress
        self.siginfoflag = False

    def siginfohandler(self, signum, frame):
        self.slf.logprinter.print_stats()

    def start(self):
        if hasattr(signal, 'SIGINFO'):
            signal.signal(signal.SIGINFO, self.siginfohandler)
        curs = self.slf.getcursor()
        iwait = conswaiter(noprint=not self.output_progress)
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
                    if self.output_progress:
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
        self.needed_cols = list(self.gen_needed_cols(options))

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
            k = self.sqlvarname(key)
            self.wcl.append('%s %s %%(%s)s' % (key, sign, k))
            self.sqla[k] = value

    def filteraddwhere_in(self, key, values, negsign='-'):
        if not values:
            return
        pos = [x for x in values if not x.startswith(negsign)]
        neg = [x[1:] for x in values if x.startswith(negsign)]
        if self.verbose and pos and neg:
            self.vprint('contradictory %s spec (pos=%r, neg=%r)' % (
                key, pos, neg))
        self.filteraddwhere_in_1(key, pos)
        self.filteraddwhere_in_1(key, neg, 'NOT IN')

    def filteraddwhere_in_1(self, key, values, inop='IN'):
        if values:
            skey = key if key.endswith('s') else key + 's'
            k = self.sqlvarname('%s_%s' % (skey, inop.replace(' ', '')))
            self.wcl.append('%s %s %%(%s)s' % (key, inop, k))
            self.sqla[k] = tuple(values)

    def sqlacounter(self):
        # Yes this will return 1 first, who cares
        self.sqlc = self.sqlc + 1
        return self.sqlc

    def sqlvarname(self, key):
        return 'sa%d_%s' % (self.sqlacounter(), key)

    def setfilter(self, options):
        self.sqla = {}
        self.sqlc = 0
        self.wcl = []
        if options.begindate and options.enddate:
            self.wcl.append('stamp BETWEEN %(begindate)s::date AND %(enddate)s::date')
            self.sqla['begindate'] = options.begindate
            self.sqla['enddate'] = options.enddate
        elif options.begindate:
            self.wcl.append('stamp > %(begindate)s::date')
            self.sqla['begindate'] = options.begindate
        elif options.enddate:
            self.wcl.append('stamp < %(enddate)s::date')
            self.sqla['enddate'] = options.enddate
        elif options.interval:
            self.wcl.append('stamp > (now() - %(interval)s::interval)')
            self.sqla['interval'] = options.interval
        self.filteraddwhere_in('host',
            (quote_implied_domains(options, x) for x in options.filter_host))
        self.filteraddwhere_in('facility', options.filter_facility)
        self.filteraddwhere_in('program', options.filter_program)
        self.filteraddwhere('msg', options.filter_posixre, '~*')
        self.filteraddwhere('msg', options.filter_like, 'LIKE', False)
        self.filteraddwhere('msg', options.filter_similar, 'SIMILAR TO', False)

    def mkstmt(self, cols, where='', clauses=()):
        ss = ['SELECT %s FROM %s' % (colslist(cols), self.logstable)]
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

    def warn(self, s):
        print >> sys.stderr, 'WARNING: %s' % s

    def vprint(self, s):
        if self.verbose:
            print >> sys.stderr, 'VERBOSE: %s' % s

    def vlogsql(self, statement, sqla):
        if self.verbose:
            print >> sys.stderr, '=' * 40
            print >> sys.stderr, 'ARG: %r' % sqla
            print >> sys.stderr, 'SQL: %s' % statement
            print >> sys.stderr, '=' * 40

    def select(self, cursor, clauses=(), cols=None, outer=''):
        self.select2(cursor, clauses=clauses, cols=cols, outer=outer)

    def select2(self, cursor, where='', clauses=(), outer='',
                cols=None, sqla=None):
        if cols is None:
            cols = self.needed_cols
        s = self.mkstmt(cols, where, clauses)
        if outer:
            s = outer % s
        self.cexec(cursor, s, sqla=sqla)

    def selectrow(self, cursor, cols):
        self.cexec(cursor, self.mkstmt(cols))
        return cursor.fetchone()

    def gen_needed_cols(self, options):
        """Determine columns which we actually need"""
        if options.mode == 'poller':
            yield 'seq'
        for x in SYSLOG_BASE_COLS:
            yield x
        yield 'program'
        if options.print_priority or options.print_full:
            yield 'facility'
            yield 'priority'
        if options.print_full:
            yield 'tag'

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
            clauses = ['ORDER BY stamp DESC']
            if options.tailcount > 0:
                clauses.append('LIMIT %d' % options.tailcount)
            self.slf.select(c, clauses,
                        outer='SELECT * FROM (%s) AS x ORDER BY x.stamp')
            recs = c.fetchall()
            self.slf.logprinter.precs(recs)
            if options.tailcount_defaulted and len(recs) >= options.tailcount:
                z, = self.slf.selectrow(c, cols='COUNT(*)')
                self.slf.warn('tailcount output limited [%d/%d]' % (len(recs), z))
        finally:
            c.close()

    def start_view(self, options, simple=False):
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


def set_local_timezone(options):
    global LOCAL_TIMEZONE
    if not options.local_timezone:
        return
    try:
        import pytz
    except ImportError:
        app_error('pytz module required for --local-timezone')
    try:
        import tzlocal
    except ImportError:
        import os
        tzs = os.getenv('TZ')
        if not tzs:
            app_error('unable to determine local timezone')
        try:
            LOCAL_TIMEZONE = pytz.timezone(tzs)
        except KeyError:
            app_error('invalid local timezone: %s' % tzs)
    else:
        LOCAL_TIMEZONE = tzlocal.get_localzone()

def set_print_verbose(options):
    if options.print_verbose is None:
        pass
    elif options.print_verbose >= 2:
        options.print_full = True
    elif options.print_verbose >= 1:
        options.print_priority = True

def set_quiet_mode(options):
    for x in 'print_stats', 'progress':
        setattr(options, x, False)

def optparseconfig():
    parser = optparse.OptionParser('usage: %prog [options]',
                                   add_help_option=False,
                                   version=__version__)
    parser.set_defaults(verbose=False, tailcount=None, progress=True)
    #parser.set_defaults(mode='stats_simple')
    parser.set_defaults(mode='tail')
    # Done explicitly to avoid taking up the -h option
    parser.add_option('', '--help', action='help',
                      help='show this help message and exit')

    def quietmode(option, opt_str, value, parser):
        set_quiet_mode(parser.values)

    def storeandmode(realdest, modevalue):
        def optioncb(option, opt_str, value, parser):
            setattr(parser.values, realdest, value)
            setattr(parser.values, 'mode', modevalue)
        return optioncb

    modegroup = optparse.OptionGroup(parser, 'Running mode options')
    modegroup.add_option('-n', type='int', action='callback',
                         callback=storeandmode('tailcount', 'tail'),
                         help='Display the last N records in view (tail mode) (default: N=%d); 0=unlimited' % DEFAULT_TAILCOUNT)
    modegroup.add_option('-P', dest='mode', action='store_const', const='poller',
                         help='Enable polling mode')
    modegroup.add_option('', '--view', dest='mode', action='store_const', const='view',
                         help='Show statistics of the filtered view')
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
    dbgroup.add_option('', '--sql-verbose', dest='verbose', action='store_true',
        help='Print details about SQL queries')
    dbgroup.add_option('', '--implied-domain', dest='implied_domains',
        type='string', action='append', default=[],
        help='''
Specify domain names which might be implied in some places. On output,
these are stripped from the hostname. On input, the first one
specified will be appended to -h arguments that are not qualified.
        '''.strip())
    parser.add_option_group(dbgroup)

    timegroup = optparse.OptionGroup(parser, 'Time filtering options',
        '''
Specify time bounds for data to be searched. The default is an
INTERVAL of the recent past. Explicit date range takes priority (value
is SQL DATE expression)
        '''.strip())
    timegroup.add_option('-i', '--interval', dest='interval',
                         type='string', default=DEFAULT_INTERVAL,
                         help='SQL interval (time delta) expression (default: %s)' % DEFAULT_INTERVAL)
    timegroup.add_option('-B', '--begin', dest='begindate', type='string',
        help='Search records starting at this time')
    timegroup.add_option('-E', '--end', dest='enddate', type='string',
        help='Search records up to this time')
    parser.add_option_group(timegroup)

    simplefil = optparse.OptionGroup(parser, 'Simple column filtering options',
                                     'If the first character of the option value is a '
                                     'dash (-) the match sense will be reversed (i.e. NOT)')
    simplefil.add_option('-h', '--host', dest='filter_host', default=[],
                         type='string', action='append',
                         help='Match syslog source host')
    simplefil.add_option('-f', '--facility', dest='filter_facility',
                         type='string', action='append',
                         help='Match syslog facility')
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
    printgroup.add_option('-v', '--print-verbose', dest='print_verbose',
        action='count',
        help='Bump output detail level (1=print-priority, 2=print-full)')
    printgroup.add_option('-q', '--quiet', action='callback',
                          callback=quietmode,
                          help='Quiet mode - suppress extraneous output')
    printgroup.add_option('', '--no-auto-quiet', action='store_true',
        help='Do not automatically enable quiet mode if non-tty detected')
    printgroup.add_option('', '--no-hostname', action='store_true',
        help='Do not include hostname in record output')
    printgroup.add_option('', '--date-format', default=DEFAULT_DATE_FORMAT,
        help='Date format for record output in strftime(3) syntax')
    addboolopt(printgroup, 'local-timezone',
        help='Output timestamps in the local timezone (WARNING: may not always be internally consistent, e.g. during DST)')
    printgroup.add_option('', '--print-priority', action='store_true',
        help='Include syslog facility and priority in output')
    printgroup.add_option('', '--print-full', action='store_true',
        help='Break out all syslog details in output')
    addboolopt(printgroup, 'stats', dest='print_stats',
        help='view statistics collection (output at the end or for SIGINFO)')
    parser.add_option_group(printgroup)

    pollergroup = optparse.OptionGroup(parser, 'Polling mode options')
    addboolopt(pollergroup, 'progress',
               help='output of wait progress')
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
    options.tailcount_defaulted = options.tailcount is None
    if options.tailcount_defaulted:
        options.tailcount = DEFAULT_TAILCOUNT
    if options.mode == 'poller' and options.print_stats is None:
        options.print_stats = True
    if not options.no_auto_quiet and not sys.stdout.isatty():
        set_quiet_mode(options)
    set_print_verbose(options)
    try:
        set_local_timezone(options)
    except ApplicationError, e:
        parser.error('%s' % e)
    try:
        sf = syslogfilter(options)
        try:
            runmodeswitch(sf).start(options)
        finally:
            sf.shutdown()
    except EnvironmentError, e:
        parser.error('%s' % e)
    except KeyboardInterrupt:
        pass

def conswaiter(waitstr='\-/|', refresh=.1, noprint=False):
    ix = [0]
    def iwait(howlong, notice=''):
        t = time.time()
        while True:
            s = '%s [%s]' % (notice, waitstr[ix[0]])
            if not noprint:
                print '\r%s' % s,
                sys.stdout.flush()
            ix[0] = (ix[0] + 1) % len(waitstr)
            if time.time() - t >= howlong:
                return len(s)
            try:
                time.sleep(refresh)
            except KeyboardInterrupt:
                if not noprint:
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
    if LOCAL_TIMEZONE is not None:
        datestamp = LOCAL_TIMEZONE.fromutc(datestamp)
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
    parser.add_option(*enargs, **enkw)
    parser.add_option(*disargs, action='store_false', **diskw)

def quote_implied_domains(options, s):
    if options.implied_domains and '.' not in s:
        s = '%s.%s' % (s, options.implied_domains[0])
    return s

def unquote_implied_domains(options, s):
    for xd in options.implied_domains:
        p = '.%s' % xd
        if len(s) > len(p) and s.endswith(p):
            s = s[:-len(p)]
            break
    return s

def colslist(x):
    if isinstance(x, str):
        return x
    return ', '.join(x)

if __name__ == '__main__':
    main()
