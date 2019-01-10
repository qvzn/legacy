/*-
 * Copyright (c) 2005 Dima Dorfman.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
 * OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 * LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
 * OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
 * SUCH DAMAGE.
 */

#ifndef lint
static const char rcsid[] = "@(#)$Dima: pylib/lazytools/src/lazymapping.c,v 1.1 2005/08/22 00:38:25 dima Exp $";
#endif

#include "Python.h"

PyDoc_STRVAR(lazymapping_doc,
    "lazymapping");

struct lazymapping {
	PyObject_HEAD
	PyObject *make;
	PyObject *values;
};

static PyObject *
lazymapping_new(PyTypeObject *type, PyObject *args, PyObject *kw)
{
	struct lazymapping *lmo;

	if (PyTuple_Size(args) != 1) {
		PyErr_SetString(PyExc_TypeError,
		    "lazymapping expects exactly one argument");
		return (NULL);
	}
	lmo = (struct lazymapping *)type->tp_alloc(type, 0);
	if (lmo == NULL)
		return (NULL);
	lmo->make = PyTuple_GET_ITEM(args, 0);
	Py_INCREF(lmo->make);
	lmo->values = PyDict_New();
	if (lmo->values == NULL) {
		Py_DECREF(lmo);
		return (NULL);
	}
	return ((PyObject *)lmo);
}

static void
lazymapping_dealloc(struct lazymapping *lmo)
{

	PyObject_GC_UnTrack(lmo);
	Py_CLEAR(lmo->make);
	Py_CLEAR(lmo->values);
	lmo->ob_type->tp_free(lmo);
}

static int
lazymapping_traverse(struct lazymapping *lmo, visitproc visit, void *arg)
{

	Py_VISIT(lmo->make);
	Py_VISIT(lmo->values);
	return (0);
}

static PyObject *
lazymapping_subscript(struct lazymapping *lmo, PyObject *key)
{
	PyObject *value;

	value = PyDict_GetItem(lmo->values, key);
	if (value == NULL) {
		value = PyObject_CallFunctionObjArgs(lmo->make, key, NULL);
		if (value == NULL)
			return (NULL);
		if (PyDict_SetItem(lmo->values, key, value) == -1)
			return (NULL);
	} else
		Py_INCREF(value);
	return (value);
}

static PyMappingMethods lazymapping_as_mapping = {
	0,					/*mp_length*/
	(binaryfunc)lazymapping_subscript,	/*mp_subscript*/
	0,					/*mp_ass_subscript*/
};

static PyTypeObject lazymapping_type = {
	PyObject_HEAD_INIT(NULL)
	0,				/* ob_size */
	"lazymapping",			/* tp_name */
	sizeof(struct lazymapping),	/* tp_basicsize */
	0,				/* tp_itemsize */
	/* methods */
	(destructor)lazymapping_dealloc,	/* tp_dealloc */
	0,				/* tp_print */
	0,				/* tp_getattr */
	0,				/* tp_setattr */
	0,				/* tp_compare */
	0,				/* tp_repr */
	0,				/* tp_as_number */
	0,				/* tp_as_sequence */
	&lazymapping_as_mapping,	/* tp_as_mapping */
	0,				/* tp_hash */
	0,				/* tp_call */
	0,				/* tp_str */
	0,				/* tp_getattro */
	0,				/* tp_setattro */
	0,				/* tp_as_buffer */
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC |
		Py_TPFLAGS_BASETYPE,	/* tp_flags */
	lazymapping_doc,		/* tp_doc */
	(traverseproc)lazymapping_traverse,	/* tp_traverse */
	0,				/* tp_clear */
	0,				/* tp_richcompare */
	0,				/* tp_weaklistoffset */
	0,				/* tp_iter */
	0,				/* tp_iternext */
	0,				/* tp_methods */
	0,				/* tp_members */
	0,				/* tp_getset */
	0,				/* tp_base */
	0,				/* tp_dict */
	0,				/* tp_descr_get */
	0,				/* tp_descr_set */
	0,				/* tp_dictoffset */
	0,				/* tp_init */
	0,				/* tp_alloc */
	lazymapping_new,		/* tp_new */
	PyObject_GC_Del,		/* tp_free */
};

int
init_lazytools_lazymapping(PyObject *m)
{

	if (PyType_Ready(&lazymapping_type) < 0)
		return (1);
	PyModule_AddObject(m, "lazymapping", (PyObject *)&lazymapping_type);
	return (0);
}
