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

##
## Copyright (c) 2017 Dima Dorfman.
## All rights reserved.
##

__version__ = '$Id: gpio.py 120 2017-03-07 08:05:10Z dima $'
__all__ = ['GPIO']

import _gpiolx
from pin import GPIOPin

class GPIO(_gpiolx.gpio):

    ALL_PINS = 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27

    def __init__(self, *args, **kwargs):
        super(GPIO, self).__init__(*args, **kwargs)
        self._pwms = {}
        self.automode = True

    def _check_mode_in(self, pin):
        self._check_mode_x('in', pin)

    def _check_mode_out(self, pin):
        self._check_mode_x('out', pin)

    def _check_mode_x(self, which, pin):
        if not getattr(self, which + 'p')(pin):
            if self.automode:
                getattr(self, which + 'put')(pin)
            else:
                raise _gpiolx.error, 'non-%sput pin' % which

    def getpwm(self, pin, frequency=60):
        pn = self._pinterp(pin)
        if pn not in self._pwms:
            self._pwms[pn] = _gpiolx.PWM(pn, frequency)
        return self._pwms[pn]

    def pwmstart(self, pin, dutycycle=50, frequency=60):
        self._check_mode_out(pin)
        pwm = self.getpwm(pin, frequency)
        pwm.start(dutycycle)
        pwm.ChangeFrequency(frequency)
        pwm.ChangeDutyCycle(dutycycle)

    def pwmstop(self, pin):
        pn = self._pinterp(pin)
        if pn in self._pwms:
            self._pwms[pn].stop()

    def _pinterp(self, pin):
        if isinstance(pin, str):
            try:
                return int(pin)
            except ValueError:
                return self.byname(pin).pin
        elif isinstance(pin, GPIOPin):
            return pin.pin
        else:
            return pin

    def inp(self, pin):
        return (self.config(self._pinterp(pin)).flags & _gpiolx.GPIO_PIN_INPUT) != 0

    def outp(self, pin):
        return (self.config(self._pinterp(pin)).flags & _gpiolx.GPIO_PIN_OUTPUT) != 0

    def get(self, pin):
        self._check_mode_in(pin)
        return super(GPIO, self).get(self._pinterp(pin))

    def high(self, pin):
        return self.set(pin, 1)

    def input(self, pin):
        return super(GPIO, self).input(self._pinterp(pin))

    def low(self, pin):
        return self.set(pin, 0)

    def off(self, pin):
        self.set(pin, 0)
        self.pwmstop(pin)

    def on(self, pin):
        return self.set(pin, 1)

    def output(self, pin):
        return super(GPIO, self).output(self._pinterp(pin))

    def rctime(self, pin, *args):
        return super(GPIO, self).rctime(self._pinterp(pin), *args)

    def set(self, pin, value):
        self._check_mode_out(pin)
        return super(GPIO, self).set(self._pinterp(pin), value)

    def toggle(self, pin):
        return super(GPIO, self).toggle(self._pinterp(pin))

    def genbyname(self, name):
        for x in self.list():
            if x.name == name:
                yield x

    def byname(self, name):
        L = list(self.genbyname(name))
        if len(L) != 1:
            raise _gpiolx.error, 'bad name count (%d)' % len(L)
        return L[0]

    def __getitem__(self, key):
        try:
            return GPIOPin(self.config(self._pinterp(key)), self)
        except _gpiolx.error:
            raise KeyError, key

    @property
    def named(self):
        for x in self.list():
            if x.name != 'pin %d' % x.pin:
                yield x

    def get_named_pins(self):
        for x in self.list():
            if x.name != 'pin %d' % x.pin:
                yield GPIOPin(x, self)

    def get_named_pycode(self):
        def gen():
            for pin in self.get_named_pins():
                yield 'gpio.set_name(%d, %r)' % (pin.pin, pin.name)
        return '\n'.join(gen())

    def safereset(self, *pins):
        """Make pins safe; i.e. set to output and turn off."""
        if not pins:
            pins = self.ALL_PINS
        for pin in pins:
            pin = self._pinterp(pin)
            self.pwmstop(pin)
            # set low first, just to be safe
            super(GPIO, self).set(pin, 0)
            super(GPIO, self).output(pin)
