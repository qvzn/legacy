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
static const char rcsid[] = "@(#)$Dima: pylib/functools/src/compose.c,v 1.3 2005/08/22 07:39:33 dima Exp $";
#endif

#include "Python.h"

PyDoc_STRVAR(compose_doc,
"compose(*funcs) -> compose object\n\
\n\
Functional composition: compose(f, g)(x) -> f(g(x))\n\
\n\
Any number of functions may be specified. The result of a function is\n\
applied to the function before it, and the final result is returned.\n\
Each function except the last is expected to take one argument. The\n\
last function may take any number of arguments, including keyword\n\
arguments.");

struct compose {
	PyObject_HEAD
	PyObject **fs;
	PyObject *g;
	int nfs;
};

static PyObject *
compose_new(PyTypeObject *type, PyObject *args, PyObject *kw)
{
	struct compose *co;
	int i, j;

	i = PyTuple_Size(args);
	if (i < 1) {
		PyErr_SetString(PyExc_TypeError,
		    "compose requires at least one argument");
		return (NULL);
	}

	co = (struct compose *)type->tp_alloc(type, 0);
	if (co == NULL)
		return (NULL);
	if (i > 1) {
		co->fs = PyMem_Malloc((i - 1) * sizeof(*co->fs));
		if (co->fs == NULL) {
			Py_DECREF(co);
			PyErr_NoMemory();
			return (NULL);
		}
		for (j = 0; j < i - 1; ++j) {
			co->fs[j] = PyTuple_GET_ITEM(args, j);
			Py_INCREF(co->fs[j]);
		}
		co->nfs = i - 1;
	}
	co->g = PyTuple_GET_ITEM(args, i - 1);
	Py_INCREF(co->g);
	return ((PyObject *)co);
}

static void
compose_dealloc(struct compose *co)
{
	int i;

	PyObject_GC_UnTrack(co);
	for (i = 0; i < co->nfs; ++i)
		Py_DECREF(co->fs[i]);
	if (co->nfs > 0)
		PyMem_Free(co->fs);
	Py_DECREF(co->g);
	co->ob_type->tp_free(co);
}

static int
compose_traverse(struct compose *co, visitproc visit, void *arg)
{
	int i;

	for (i = 0; i < co->nfs; ++i)
		Py_VISIT(co->fs[i]);
	Py_VISIT(co->g);
	return (0);
}

static PyObject *
compose_call(struct compose *co, PyObject *args, PyObject *kw)
{
	PyObject *res, *nres;
	int i;

	res = PyObject_Call(co->g, args, kw);
	if (res == NULL)
		return (NULL);
	for (i = co->nfs - 1; i >= 0; --i) {
		nres = PyObject_CallFunctionObjArgs(co->fs[i], res, NULL);
		Py_DECREF(res);
		if (nres == NULL)
			return (NULL);
		res = nres;
	}
	return (res);
}

static PyObject *
compose_repr(struct compose *co)
{
	PyObject *grepr, *s;

	grepr = PyObject_Repr(co->g);
	if (grepr == NULL)
		return (NULL);
	s = PyString_FromFormat("<composition on %s at %p>",
	    PyString_AsString(grepr), (void *)co);
	Py_DECREF(grepr);
	return (s);
}

static PyTypeObject compose_type = {
	PyObject_HEAD_INIT(NULL)
	0,				/* ob_size */
	"compose",			/* tp_name */
	sizeof(struct compose),		/* tp_basicsize */
	0,				/* tp_itemsize */
	/* methods */
	(destructor)compose_dealloc,	/* tp_dealloc */
	0,				/* tp_print */
	0,				/* tp_getattr */
	0,				/* tp_setattr */
	0,				/* tp_compare */
	(reprfunc)compose_repr,		/* tp_repr */
	0,				/* tp_as_number */
	0,				/* tp_as_sequence */
	0,				/* tp_as_mapping */
	0,				/* tp_hash */
	(ternaryfunc)compose_call,	/* tp_call */
	0,				/* tp_str */
	0,				/* tp_getattro */
	0,				/* tp_setattro */
	0,				/* tp_as_buffer */
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC |
		Py_TPFLAGS_BASETYPE,	/* tp_flags */
	compose_doc,			/* tp_doc */
	(traverseproc)compose_traverse,	/* tp_traverse */
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
	compose_new,			/* tp_new */
	PyObject_GC_Del,		/* tp_free */
};

int
init_functools_compose(PyObject *m)
{

	if (PyType_Ready(&compose_type) < 0)
		return (1);
	PyModule_AddObject(m, "compose", (PyObject *)&compose_type);
	return (0);
}
