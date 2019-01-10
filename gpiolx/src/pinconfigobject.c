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
 * $Id: pinconfigobject.c 124 2017-03-12 03:42:47Z dima $
 */

#include "gpiolx.h"
#include <structseq.h>

PyTypeObject PinConfig_Type;

PyObject *
new_PinConfig(gpio_config_t *cp)
{
	PyObject *rx = PyStructSequence_New(&PinConfig_Type);
	if (rx == NULL)
		return NULL;
	PyStructSequence_SET_ITEM(rx, 0, PyInt_FromLong(cp->g_pin));
	PyStructSequence_SET_ITEM(rx, 1, PyString_FromString(cp->g_name));
	PyStructSequence_SET_ITEM(rx, 2, PyInt_FromLong(cp->g_caps));
	PyStructSequence_SET_ITEM(rx, 3, PyInt_FromLong(cp->g_flags));
	if (PyErr_Occurred()) {
		Py_DECREF(rx);
		return (NULL);
	}
	return (rx);
}

static PyStructSequence_Field pin_config_fields[] = {
	{ "pin" }, { "name" }, { "caps" }, { "flags" },
	{ 0 }
};

static PyStructSequence_Desc pin_config_desc = {
    "PinConfig",			/* name */
    0,					/* doc */
    pin_config_fields,
    4
};

static void
initseqobj(PyObject *m, PyTypeObject *tp, PyStructSequence_Desc *descp)
{
	PyStructSequence_InitType(tp, descp);
	Py_INCREF(tp);
	PyModule_AddObject(m, descp->name, (PyObject *)tp);
}

void
init_PinConfig(PyObject *m)
{
	initseqobj(m, &PinConfig_Type, &pin_config_desc);
}
