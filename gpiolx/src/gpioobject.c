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
 * $Id: gpioobject.c 124 2017-03-12 03:42:47Z dima $
 */

#include "gpiolx.h"

PyObject *
GPIO_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
	GPIOObject *self;

	self = (GPIOObject *)type->tp_alloc(type, 0);
	if (self == NULL)
		return NULL;
	self->handle = GPIO_INVALID_HANDLE;
	return (PyObject *)self;
}

static int
GPIO_init(GPIOObject *self, PyObject *args, PyObject *kwdargs)
{
	PyObject *uob = NULL;
	static char *kwlist[] = { "unit", 0 };

	if (!PyArg_ParseTupleAndKeywords(args, kwdargs, "|O:GPIO", kwlist, &uob))
		return -1;
	if (uob == NULL)
		self->handle = gpio_open(0);
	else if (PyInt_Check(uob))
		self->handle = gpio_open(PyInt_AsLong(uob));
	else if (PyString_Check(uob))
		self->handle = gpio_open_device(PyString_AsString(uob));
	else {
		PyErr_SetString(gpiolxError, "bad init arg");
		return -1;
	}
	if (self->handle == GPIO_INVALID_HANDLE) {
		PyErr_SetString(gpiolxError, "gpio open failed");
		return -1;
	}
	return 0;
}

static void
GPIO_dealloc(GPIOObject *self)
{
	if (self->handle != GPIO_INVALID_HANDLE) {
		gpio_close(self->handle);
		self->handle = GPIO_INVALID_HANDLE;
	}
	PyObject_Del(self);
}

static PyObject *
_gpioop(int result)
{
	if (result) {
		PyErr_SetString(gpiolxError, "libgpio error");
		return NULL;
	} else
		Py_RETURN_NONE;
}

static PyObject *
GPIO_config(GPIOObject *self, PyObject *args)
{
	int result, pin;
	gpio_config_t cf;

	if (!PyArg_ParseTuple(args, "i:config", &pin))
		return (NULL);
	Py_BEGIN_ALLOW_THREADS
	cf.g_pin = pin;
	result = gpio_pin_config(self->handle, &cf);
	Py_END_ALLOW_THREADS
	if (result) {
		PyErr_SetString(gpiolxError, "libgpio pin_config failed");
		return NULL;
	}
	return new_PinConfig(&cf);
}

static PyObject *
GPIO_get(GPIOObject *self, PyObject *args)
{
	int result, pin;

	if (!PyArg_ParseTuple(args, "i:get", &pin))
		return (NULL);
	Py_BEGIN_ALLOW_THREADS
	result = gpio_pin_get(self->handle, pin);
	Py_END_ALLOW_THREADS
	if (result == GPIO_VALUE_INVALID) {
		PyErr_SetString(gpiolxError, "libgpio value invalid");
		return NULL;
	}
	return PyInt_FromLong(result);
}

static PyObject *
GPIO_input(GPIOObject *self, PyObject *args)
{
	int pin, ret;

	if (!PyArg_ParseTuple(args, "i:input", &pin))
		return (NULL);
	Py_BEGIN_ALLOW_THREADS
	ret = gpio_pin_input(self->handle, pin);
	Py_END_ALLOW_THREADS
        return _gpioop(ret);
}

static PyObject *
GPIO_list(GPIOObject *self)
{
	gpio_config_t *cfs = NULL;
	int i, pins;
	PyObject *item, *result;

	Py_BEGIN_ALLOW_THREADS
	pins = gpio_pin_list(self->handle, &cfs);
	Py_END_ALLOW_THREADS
	if (pins == -1 || cfs == NULL) {
		PyErr_SetString(gpiolxError, "gpio_pin_list failed");
		return NULL;
	}
	result = PyList_New(pins);
	if (result == NULL)
		goto out;
	for (i = 0; i < pins; ++i) {
		item = new_PinConfig(cfs + i);
		if (item == NULL) {
			Py_DECREF(result);
			result = NULL;
			goto out;
		}
		PyList_SET_ITEM(result, i, item);
	}
out:
	free(cfs);
	return (result);
}

static PyObject *
GPIO_output(GPIOObject *self, PyObject *args)
{
	int pin, ret;

	if (!PyArg_ParseTuple(args, "i:output", &pin))
		return (NULL);
	Py_BEGIN_ALLOW_THREADS
	ret = gpio_pin_output(self->handle, pin);
	Py_END_ALLOW_THREADS
        return _gpioop(ret);
}

static PyObject *
GPIO_set(GPIOObject *self, PyObject *args)
{
	int pin, value;
	int ret;

	if (!PyArg_ParseTuple(args, "ii:set", &pin, &value))
		return (NULL);
	Py_BEGIN_ALLOW_THREADS
	ret = gpio_pin_set(self->handle, pin, value);
	Py_END_ALLOW_THREADS
        return _gpioop(ret);
}

static PyObject *
GPIO_set_flags(GPIOObject *self, PyObject *args)
{
	long pin, flags;
	gpio_config_t cf;
	int ret;

	if (!PyArg_ParseTuple(args, "ii:set_flags", &pin, &flags))
		return (NULL);
	Py_BEGIN_ALLOW_THREADS
	cf.g_pin = pin;
	cf.g_flags = flags;
	ret = gpio_pin_set_flags(self->handle, &cf);
	Py_END_ALLOW_THREADS
        return _gpioop(ret);
}

static PyObject *
GPIO_set_name(GPIOObject *self, PyObject *args)
{
	int pin, ret;
	PyObject *name;

	if (!PyArg_ParseTuple(args, "iS:set_name", &pin, &name))
		return (NULL);
	Py_BEGIN_ALLOW_THREADS
	ret = gpio_pin_set_name(self->handle, pin, PyString_AsString(name));
	Py_END_ALLOW_THREADS
        return _gpioop(ret);
}

static PyObject *
GPIO_toggle(GPIOObject *self, PyObject *args)
{
	int pin, ret;

	if (!PyArg_ParseTuple(args, "i:toggle", &pin))
		return (NULL);
	Py_BEGIN_ALLOW_THREADS
	ret = gpio_pin_toggle(self->handle, pin);
	Py_END_ALLOW_THREADS
        return _gpioop(ret);
}

static PyObject *
GPIO_rctime(GPIOObject *self, PyObject *args)
{
	int i, pin;
	int msleep = 10000;

	if (!PyArg_ParseTuple(args, "i|i:rctime", &pin, &msleep))
		return (NULL);
	// XXX: error handling!
	Py_BEGIN_ALLOW_THREADS
	gpio_pin_output(self->handle, pin);
	gpio_pin_low(self->handle, pin);
	usleep(msleep);
	gpio_pin_input(self->handle, pin);
	for (i = 0; gpio_pin_get(self->handle, pin) == 0; ++i)
		;
	Py_END_ALLOW_THREADS
	return PyInt_FromLong(i);
}

static PyMethodDef GPIO_methods[] = {
	{ "config",	(PyCFunction)GPIO_config,	METH_VARARGS },
	{ "get",	(PyCFunction)GPIO_get,		METH_VARARGS },
	{ "input",	(PyCFunction)GPIO_input,	METH_VARARGS },
	{ "list",	(PyCFunction)GPIO_list,		METH_NOARGS },
	{ "output",	(PyCFunction)GPIO_output,	METH_VARARGS },
	{ "set",	(PyCFunction)GPIO_set,		METH_VARARGS },
	{ "set_flags",	(PyCFunction)GPIO_set_flags,	METH_VARARGS },
	{ "set_name",	(PyCFunction)GPIO_set_name,	METH_VARARGS },
	{ "toggle",	(PyCFunction)GPIO_toggle,	METH_VARARGS },
	{ "rctime",	(PyCFunction)GPIO_rctime,	METH_VARARGS },
	{ NULL }
};

PyTypeObject GPIO_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "gpio",             /*tp_name*/
    sizeof(GPIOObject),          /*tp_basicsize*/
    0,                          /*tp_itemsize*/
    /* methods */
    (destructor)GPIO_dealloc, /*tp_dealloc*/
    0,                          /*tp_print*/
    0,				 /*tp_getattr*/
    0,				 /*tp_setattr*/
    0,                          /*tp_compare*/
    0,                          /*tp_repr*/
    0,                          /*tp_as_number*/
    0,                          /*tp_as_sequence*/
    0,                          /*tp_as_mapping*/
    0,                          /*tp_hash*/
    0,                      /*tp_call*/
    0,                      /*tp_str*/
    0,                      /*tp_getattro*/
    0,                      /*tp_setattro*/
    0,                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,     /*tp_flags*/
    0,                      /*tp_doc*/
    0,                      /*tp_traverse*/
    0,                      /*tp_clear*/
    0,                      /*tp_richcompare*/
    0,                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                      /*tp_iternext*/
    GPIO_methods,                      /*tp_methods*/
    0,                      /*tp_members*/
    0,                      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)GPIO_init,                      /*tp_init*/
    0,                      /*tp_alloc*/
    GPIO_new,                      /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};
