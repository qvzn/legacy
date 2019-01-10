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
static const char rcsid[] = "@(#)$Dima: pylib/lazytools/src/promise.c,v 1.2 2005/08/21 23:19:14 dima Exp $";
#endif

#include "Python.h"

PyDoc_STRVAR(promise_doc,
"promise(thunk) -> promise object\n\
\n\
Lazy evaluation primitive. A promise object is a callable that\n\
returns the result of the thunk or the result of a previous\n\
invocation of the thunk. The first time it is called, the thunk\n\
will be called and its result cached. Every subsequent call will\n\
return the same (cached) result.\n\
\n\
Exceptions are propogated and not cached.");

static PyObject *empty_tuple;

struct promise {
	PyObject_HEAD
	PyObject *thunk;
	PyObject *result;
};

static PyObject *
promise_new(PyTypeObject *type, PyObject *args, PyObject *kw)
{
	struct promise *po;

	if (PyTuple_Size(args) != 1) {
		PyErr_SetString(PyExc_TypeError,
		    "promise takes exactly one argument.");
		return (NULL);
	}
	po = (struct promise *)type->tp_alloc(type, 0);
	if (po == NULL)
		return (NULL);
	po->thunk = PyTuple_GET_ITEM(args, 0);
	Py_INCREF(po->thunk);
	return ((PyObject *)po);
}

static void
promise_dealloc(struct promise *po)
{

	PyObject_GC_UnTrack(po);
	assert(po->thunk == NULL || po->result == NULL);
	Py_CLEAR(po->thunk);
	Py_CLEAR(po->result);
	po->ob_type->tp_free(po);
}

static int
promise_traverse(struct promise *po, visitproc visit, void *arg)
{

	Py_VISIT(po->thunk);
	Py_VISIT(po->result);
	return (0);
}

static PyObject *
promise_call(struct promise *po)
{

	assert(empty_tuple != NULL);
	if (po->result == NULL) {
		po->result = PyObject_Call(po->thunk, empty_tuple, NULL);
		if (po->result != NULL)
			Py_CLEAR(po->thunk);
	}
	Py_XINCREF(po->result);
	return (po->result);
}

static PyObject *
promise_repr(struct promise *po)
{
	PyObject *s;

	s = PyString_FromFormat("<promise object%s at %p>",
	    po->result == NULL ? "" : " (forced)", (void *)po);
	return (s);
}

static PyTypeObject promise_type = {
	PyObject_HEAD_INIT(NULL)
	0,				/* ob_size */
	"promise",			/* tp_name */
	sizeof(struct promise),		/* tp_basicsize */
	0,				/* tp_itemsize */
	/* methods */
	(destructor)promise_dealloc,	/* tp_dealloc */
	0,				/* tp_print */
	0,				/* tp_getattr */
	0,				/* tp_setattr */
	0,				/* tp_compare */
	(reprfunc)promise_repr,		/* tp_repr */
	0,				/* tp_as_number */
	0,				/* tp_as_sequence */
	0,				/* tp_as_mapping */
	0,				/* tp_hash */
	(ternaryfunc)promise_call,	/* tp_call */
	0,				/* tp_str */
	0,				/* tp_getattro */
	0,				/* tp_setattro */
	0,				/* tp_as_buffer */
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC |
		Py_TPFLAGS_BASETYPE,	/* tp_flags */
	promise_doc,			/* tp_doc */
	(traverseproc)promise_traverse,	/* tp_traverse */
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
	promise_new,			/* tp_new */
	PyObject_GC_Del,		/* tp_free */
};

int
init_lazytools_promise(PyObject *m)
{

	empty_tuple = PyTuple_New(0);
	if (empty_tuple == NULL)
		return (1);
	if (PyType_Ready(&promise_type) < 0)
		return (1);
	PyModule_AddObject(m, "promise", (PyObject *)&promise_type);
	return (0);
}
