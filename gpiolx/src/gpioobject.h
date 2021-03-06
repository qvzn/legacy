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
 * $Id: gpioobject.h 124 2017-03-12 03:42:47Z dima $
 */

#ifndef	GPIOOBJECT_H
#define	GPIOOBJECT_H

#include <libgpio.h>

typedef struct {
	PyObject_HEAD
	gpio_handle_t handle;
} GPIOObject;

PyTypeObject GPIO_Type;

#define GPIOObject_Check(v)      (Py_TYPE(v) == &GPIO_Type)

#endif
