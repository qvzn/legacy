##
## Copyright (c) 2017 Dima Dorfman.
## All rights reserved.
##

__version__ = '$Id: pinconfig.py 141 2017-05-29 05:52:12Z dima $'

import optparse
from gpiolx import gpio
import sys

class pinconfig(object):

    def setup_parser(self):
        #super(pinconfig, self).setup_parser()
        self.parser.add_option('', '--no-reset', dest='no_reset',
                               action='store_true')
        self.parser.add_option('-s', '--save', dest='save',
                               action='store_true')

    def main_parser(self):
        self.parser = optparse.OptionParser('usage: %prog [options]')
        self.setup_parser()
        self.options, self.args = self.parser.parse_args()

    def main(self):
        self.main_parser()
        if self.options.save:
            self.main_save()
        else:
            self.main_set()

    def main_save(self):
        for pin in gpio.get_named_pins():
            def gen():
                if pin.outp():
                    yield 'o'
                elif pin.inp():
                    yield 'i'
                else:
                    yield 'x'
                yield pin.pin
                yield pin.name
            print '\t'.join(map(str, gen()))

    def main_set(self):
        if not self.options.no_reset:
            gpio.safereset()
        for line in sys.stdin:
            p = line.split()
            if len(p) != 3:
                self.error('bad line with %d words' % len(p))
            io, pin, name = p
            try:
                pin = int(pin)
            except ValueError:
                self.error('bad pin')
            if io == 'i':
                gpio.input(pin)
            elif io == 'o':
                gpio.output(pin)
            else:
                self.error('bad line i/o')
            gpio.set_name(pin, name)

def main():
    program = pinconfig()
    program.main()

if __name__ == '__main__':
    main()
