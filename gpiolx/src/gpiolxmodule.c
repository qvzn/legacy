/*-
 * Copyright (c) 2017, Dima Dorfman.
 * All rights reserved.
 *
 * Permission to use, copy, modify, and/or distribute this software for any
 * purpose with or without fee is hereby granted, provided that the above
 * copyright notice and this permission notice appear in all copies.
 *
 * THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 * WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 * ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 * WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 * ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 * OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 *
 * $Id: gpiolxmodule.c 124 2017-03-12 03:42:47Z dima $
 */

#include "gpiolx.h"

#include <sys/gpio.h>

#include "py_pwm.h"

PyObject *gpiolxError;

gpio_handle_t GPIOLX_GLOBAL_C0 = GPIO_INVALID_HANDLE;

void
output_gpio(unsigned int gpio, int value)
{
	if (GPIOLX_GLOBAL_C0 != GPIO_INVALID_HANDLE)
		gpio_pin_set(GPIOLX_GLOBAL_C0, gpio, value);
}

static int
ins(PyObject* d, char* symbol, long value)
{
    PyObject* v = PyInt_FromLong(value);
    if (!v || PyDict_SetItemString(d, symbol, v) < 0)
        return -1;
    // XXX: leaks if v is good but set fails!
    Py_DECREF(v);
    return 0;
}

#define	EXPORTED_CONSTANTS \
	X("GPIO_PIN_LOW", GPIO_PIN_LOW)		\
		X("GPIO_PIN_HIGH", GPIO_PIN_HIGH)		\
		X("GPIO_PIN_INPUT", GPIO_PIN_INPUT)			\
		X("GPIO_PIN_OUTPUT", GPIO_PIN_OUTPUT)			\
		X("GPIO_PIN_OPENDRAIN", GPIO_PIN_OPENDRAIN)			\
		X("GPIO_PIN_PUSHPULL", GPIO_PIN_PUSHPULL)			\
		X("GPIO_PIN_TRISTATE", GPIO_PIN_TRISTATE)			\
		X("GPIO_PIN_PULLUP", GPIO_PIN_PULLUP)			\
		X("GPIO_PIN_PULLDOWN", GPIO_PIN_PULLDOWN)			\
		X("GPIO_PIN_INVIN", GPIO_PIN_INVIN)				\
		X("GPIO_PIN_INVOUT", GPIO_PIN_INVOUT)			\
		X("GPIO_PIN_PULSATE", GPIO_PIN_PULSATE)			\
		X("GPIO_INTR_NONE", GPIO_INTR_NONE)				\
		X("GPIO_INTR_LEVEL_LOW", GPIO_INTR_LEVEL_LOW)		\
		X("GPIO_INTR_LEVEL_HIGH", GPIO_INTR_LEVEL_HIGH)		\
		X("GPIO_INTR_EDGE_RISING", GPIO_INTR_EDGE_RISING)		\
		X("GPIO_INTR_EDGE_FALLING", GPIO_INTR_EDGE_FALLING)		\
		X("GPIO_INTR_EDGE_BOTH", GPIO_INTR_EDGE_BOTH)		\
		X("GPIO_INTR_MASK", GPIO_INTR_MASK)

static void
all_ins(PyObject *d)
{
#define	X(n, s)	(void)ins(d, n, s);
	EXPORTED_CONSTANTS
#undef X
}

static void
init_py_pwm(PyObject *m)
{
	if (PWM_init_PWMType() != NULL) {
		Py_INCREF(&PWMType);
		PyModule_AddObject(m, "PWM", (PyObject*)&PWMType);
	}
}

PyMODINIT_FUNC
init_gpiolx(void)
{
    PyObject *m;
    if (PyType_Ready(&GPIO_Type) < 0)
        return;

    m = Py_InitModule3("gpiolx._gpiolx", NULL, NULL);
    if (m == NULL)
        return;

    if (gpiolxError == NULL) {
        gpiolxError = PyErr_NewException("_gpiolx.error", NULL, NULL);
        if (gpiolxError == NULL)
            return;
    }
    Py_INCREF(gpiolxError);
    PyModule_AddObject(m, "error", gpiolxError);

    GPIOLX_GLOBAL_C0 = gpio_open(0);

    (void)PyModule_AddObject(m, "gpio", (PyObject *)&GPIO_Type);

    init_PinConfig(m);

    all_ins(PyModule_GetDict(m));

    init_py_pwm(m);
}
