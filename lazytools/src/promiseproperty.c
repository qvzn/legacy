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
static const char rcsid[] = "@(#)$Dima: pylib/lazytools/src/promiseproperty.c,v 1.1 2005/08/21 23:19:14 dima Exp $";
#endif

#include "Python.h"
#include "structmember.h"

PyDoc_STRVAR(promiseproperty_doc,
"promiseproperty(sub, doc=None) -> descriptor\n\
\n\
A cached property descriptor.");

struct promiseproperty {
	PyObject_HEAD
	PyObject *sub;
	PyObject *name;
	PyObject *doc;
};

static PyObject *
promiseproperty_new(PyTypeObject *type, PyObject *args, PyObject *kw)
{
	static char *kwlist[] = { "sub", "name", "doc", NULL };
	struct promiseproperty *ppo;
	PyObject *sub, *name, *doc;

	name = doc = Py_None;
	if (!PyArg_ParseTupleAndKeywords(args, kw, "O|OO:promiseproperty",
	    kwlist, &sub, &name, &doc))
		return (NULL);
	ppo = (struct promiseproperty *)type->tp_alloc(type, 0);
	if (ppo == NULL)
		return (NULL);
	ppo->sub = sub;
	Py_INCREF(ppo->sub);
	if (name == Py_None) {
		name = PyObject_GetAttrString(sub, "__name__");
		if (name == NULL) {
			PyErr_SetString(PyExc_TypeError,
			    "promiseproperty requires sub.__name__ or for "
			    "a name to be specified explicitly");
			Py_DECREF(sub);
			Py_DECREF(ppo);
			return (NULL);
		}
	}
	ppo->name = name;
	Py_INCREF(ppo->name);
	if (doc == Py_None) {
		doc = PyObject_GetAttrString(sub, "__doc__");
		if (doc == NULL) {
			PyErr_Clear();
			doc = Py_None;
		}
	}
	ppo->doc = doc;
	Py_INCREF(ppo->doc);
	return ((PyObject *)ppo);
}

static void
promiseproperty_dealloc(struct promiseproperty *ppo)
{

	PyObject_GC_UnTrack(ppo);
	Py_CLEAR(ppo->sub);
	Py_CLEAR(ppo->name);
	Py_CLEAR(ppo->doc);
	ppo->ob_type->tp_free(ppo);
}

static int
promiseproperty_traverse(struct promiseproperty *ppo,visitproc visit,void *arg)
{

	Py_VISIT(ppo->sub);
	Py_VISIT(ppo->name);
	Py_VISIT(ppo->doc);
	return (0);
}

static PyObject *
promiseproperty_get(struct promiseproperty *ppo, PyObject *obj, PyObject *type)
{
	PyObject *res;

	if (obj == NULL || obj == Py_None) {
		Py_INCREF(ppo);
		return ((PyObject *)ppo);
	}
	res = PyObject_CallFunctionObjArgs(ppo->sub, obj, NULL);
	if (res == NULL)
		return (NULL);
	if (PyObject_SetAttr(obj, ppo->name, res) == -1) {
		Py_DECREF(res);
		return (NULL);
	}
	return (res);
}

static PyMemberDef promiseproperty_members[] = {
	{"__doc__", T_OBJECT, offsetof(struct promiseproperty, doc), READONLY},
	{NULL}
};

static PyTypeObject promiseproperty_type = {
	PyObject_HEAD_INIT(NULL)
	0,				/* ob_size */
	"promiseproperty",		/* tp_name */
	sizeof(struct promiseproperty),	/* tp_basicsize */
	0,				/* tp_itemsize */
	/* methods */
	(destructor)promiseproperty_dealloc,	/* tp_dealloc */
	0,				/* tp_print */
	0,				/* tp_getattr */
	0,				/* tp_setattr */
	0,				/* tp_compare */
	0,				/* tp_repr */
	0,				/* tp_as_number */
	0,				/* tp_as_sequence */
	0,				/* tp_as_mapping */
	0,				/* tp_hash */
	0,				/* tp_call */
	0,				/* tp_str */
	0,				/* tp_getattro */
	0,				/* tp_setattro */
	0,				/* tp_as_buffer */
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC |
		Py_TPFLAGS_BASETYPE,	/* tp_flags */
	promiseproperty_doc,		/* tp_doc */
	(traverseproc)promiseproperty_traverse,	/* tp_traverse */
	0,				/* tp_clear */
	0,				/* tp_richcompare */
	0,				/* tp_weaklistoffset */
	0,				/* tp_iter */
	0,				/* tp_iternext */
	0,				/* tp_methods */
	promiseproperty_members,	/* tp_members */
	0,				/* tp_getset */
	0,				/* tp_base */
	0,				/* tp_dict */
	(descrgetfunc)promiseproperty_get,	/* tp_descr_get */
	0,				/* tp_descr_set */
	0,				/* tp_dictoffset */
	0,				/* tp_init */
	0,				/* tp_alloc */
	promiseproperty_new,		/* tp_new */
	PyObject_GC_Del,		/* tp_free */
};

int
init_lazytools_promiseproperty(PyObject *m)
{

	if (PyType_Ready(&promiseproperty_type) < 0)
		return (1);
	PyModule_AddObject(m, "promiseproperty",
	    (PyObject *)&promiseproperty_type);
	return (0);
}
