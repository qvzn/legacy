import Qez

# From: http://code.activestate.com/recipes/578407-simple-morse-code-translator-in-python/
CODE = {'A': '.-',     'B': '-...',   'C': '-.-.', 
        'D': '-..',    'E': '.',      'F': '..-.',
        'G': '--.',    'H': '....',   'I': '..',
        'J': '.---',   'K': '-.-',    'L': '.-..',
        'M': '--',     'N': '-.',     'O': '---',
        'P': '.--.',   'Q': '--.-',   'R': '.-.',
     	'S': '...',    'T': '-',      'U': '..-',
        'V': '...-',   'W': '.--',    'X': '-..-',
        'Y': '-.--',   'Z': '--..',
        '0': '-----',  '1': '.----',  '2': '..---',
        '3': '...--',  '4': '....-',  '5': '.....',
        '6': '-....',  '7': '--...',  '8': '---..',
        '9': '----.' 
        }


class morsecoder(object):

    def __init__(self, pin, ditlen=.1):
        self.pin = pin
        self.ditlen = ditlen
        self.dahlen = 3 * self.ditlen
        self.sgap = 3 * self.ditlen
        self.mgap = 7 * self.ditlen
        self.reset()

    def reset(self):
        self.pin.off()

    def codeletter(self, s):
        for x in s:
            if x == '.':
                self.pulse(self.ditlen)
            elif x == '-':
                self.pulse(self.dahlen)
            else:
                raise ValueError
            self.sleep(self.ditlen)

    def encode(self, s):
        for x in s:
            p = CODE.get(x.upper())
            if p:
                self.codeletter(p)
                self.sleep(self.sgap)
            elif x == ' ':
                self.sleep(self.mgap)
            else:
                raise ValueError

    def sleep(self, n):
        Qez.time.sleep(n)

    def pulse(self, t):
        self.pin.on()
        self.sleep(t)
        self.pin.off()
