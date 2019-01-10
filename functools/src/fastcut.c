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
static const char rcsid[] = "@(#)$Dima: pylib/functools/src/fastcut.c,v 1.1 2005/08/22 07:39:33 dima Exp $";
#endif

#include "Python.h"

PyDoc_STRVAR(fastcut_doc,
"fastcut(fun, *sargs, **skw)(*args, **kw) -> fun(*(sargs + args), **(skw + kw))\n\
\n\
Argument specialization.");

struct fastcut {
	PyObject_HEAD
	PyObject *fun;
	PyObject *sargs;
	PyObject *skw;
};

static PyObject *
fastcut_new(PyTypeObject *type, PyObject *args, PyObject *kw)
{
	struct fastcut *fco;
	int i;

	i = PyTuple_Size(args);
	if (i < 1) {
		PyErr_SetString(PyExc_TypeError,
		    "fastcut requires at least one argument");
		return (NULL);
	}

	fco = (struct fastcut *)type->tp_alloc(type, 0);
	if (fco == NULL)
		return (NULL);
	fco->fun = PyTuple_GET_ITEM(args, 0);
	Py_INCREF(fco->fun);
	fco->sargs = PyTuple_GetSlice(args, 1, i);
	if (fco->sargs == NULL) {
		Py_DECREF(fco);
		return (NULL);
	}
	fco->skw = kw;
	Py_XINCREF(fco->skw);
	return ((PyObject *)fco);
}

static void
fastcut_dealloc(struct fastcut *fco)
{

	PyObject_GC_UnTrack(fco);
	Py_CLEAR(fco->fun);
	Py_CLEAR(fco->sargs);
	Py_CLEAR(fco->skw);
	fco->ob_type->tp_free(fco);
}

static int
fastcut_traverse(struct fastcut *fco, visitproc visit, void *arg)
{

	Py_VISIT(fco->fun);
	Py_VISIT(fco->sargs);
	Py_VISIT(fco->skw);
	return (0);
}

static PyObject *
fastcut_call(struct fastcut *fco, PyObject *args, PyObject *kw)
{
	PyObject *rargs, *rkw;
	PyObject *result;

	rargs = PySequence_Concat(fco->sargs, args);
	if (rargs == NULL)
		return (NULL);

	if (fco->skw != NULL && kw != NULL) {
		rkw = PyDict_Copy(fco->skw);
		if (rkw == NULL) {
			Py_DECREF(args);
			return (NULL);
		}
		if (PyDict_Update(rkw, kw) == -1) {
			Py_DECREF(rkw);
			Py_DECREF(rargs);
			return (NULL);
		}
	} else if (fco->skw != NULL) {
		rkw = fco->skw;
		Py_INCREF(rkw);
	} else if (kw != NULL) {
		rkw = kw;
		Py_INCREF(rkw);
	} else
		rkw = NULL;

	result = PyObject_Call(fco->fun, rargs, rkw);
	Py_DECREF(rargs);
	Py_XDECREF(rkw);
	return (result);
}

static PyTypeObject fastcut_type = {
	PyObject_HEAD_INIT(NULL)
	0,				/* ob_size */
	"fastcut",			/* tp_name */
	sizeof(struct fastcut),		/* tp_basicsize */
	0,				/* tp_itemsize */
	/* methods */
	(destructor)fastcut_dealloc,	/* tp_dealloc */
	0,				/* tp_print */
	0,				/* tp_getattr */
	0,				/* tp_setattr */
	0,				/* tp_compare */
	0,				/* tp_repr */
	0,				/* tp_as_number */
	0,				/* tp_as_sequence */
	0,				/* tp_as_mapping */
	0,				/* tp_hash */
	(ternaryfunc)fastcut_call,	/* tp_call */
	0,				/* tp_str */
	0,				/* tp_getattro */
	0,				/* tp_setattro */
	0,				/* tp_as_buffer */
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC |
		Py_TPFLAGS_BASETYPE,	/* tp_flags */
	fastcut_doc,			/* tp_doc */
	(traverseproc)fastcut_traverse,	/* tp_traverse */
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
	PyMethod_New,			/* tp_descr_get */
	0,				/* tp_descr_set */
	0,				/* tp_dictoffset */
	0,				/* tp_init */
	0,				/* tp_alloc */
	fastcut_new,			/* tp_new */
	PyObject_GC_Del,		/* tp_free */
};

int
init_functools_fastcut(PyObject *m)
{

	if (PyType_Ready(&fastcut_type) < 0)
		return (1);
	PyModule_AddObject(m, "fastcut", (PyObject *)&fastcut_type);
	return (0);
}
