/*-
 * Copyright (c) 2013 Dima Dorfman. All rights reserved.
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
 */

/*-
 * Originally based on siftr.c and ng_bpf
 */

#define	BPFILMODVERSION		27

#include <sys/param.h>
#include <sys/errno.h>
#include <sys/kernel.h>
#include <sys/mbuf.h>
#include <sys/module.h>
#include <sys/proc.h>
#include <sys/socket.h>
#include <sys/sysctl.h>
#include <sys/unistd.h>

#include <net/if.h>
#include <net/pfil.h>
#include <net/bpf.h>

#include <netinet/in.h>
#include <netinet/in_systm.h>
#include <netinet/in_var.h>


#define	BPFIL_MAXPROGLEN	8192

#define	BPFIL_ERRNO		EACCES

#define CAST_PTR_INT(X) (*((int*)(X)))

static MALLOC_DEFINE(M_BPFIL, "bpfil", "dynamic memory used by BPFIL");

/* sysctl variables */
static unsigned int bpfil_mode = 0;
static int bpfil_passerr = 1;
static int bpfil_passhit = 0;
static char bpfil_progstring[BPFIL_MAXPROGLEN] = "";
static char bpfil_interface[IFNAMSIZ] = "";

/* sysctl-accessible stats */
static u_quad_t bpfilstat_counter = 0,
	bpfilstat_error = 0,
	bpfilstat_bpfmatch = 0,
	bpfilstat_drop = 0;

/* internal state */
static struct bpf_program *bpfil_prog = NULL;

static int bpfil_proc_mode(SYSCTL_HANDLER_ARGS);
static int bpfil_proc_program(SYSCTL_HANDLER_ARGS);
static int bpfil_proc_interface(SYSCTL_HANDLER_ARGS);

SYSCTL_DECL(_net_inet_bpfil);

SYSCTL_NODE(_net_inet, OID_AUTO, bpfil, CTLFLAG_RW, NULL,
    "bpfil related settings");

SYSCTL_PROC(_net_inet_bpfil, OID_AUTO, mode, CTLTYPE_UINT | CTLFLAG_RW,
    &bpfil_mode, 0, &bpfil_proc_mode, "IU",
    "operation mode (0=none, 1=in, 2=out, 3=both)");

SYSCTL_INT(_net_inet_bpfil, OID_AUTO, passerr, CTLTYPE_UINT | CTLFLAG_RW,
    &bpfil_passerr, 0, "bpfil action on error");

SYSCTL_INT(_net_inet_bpfil, OID_AUTO, passhit, CTLTYPE_UINT | CTLFLAG_RW,
    &bpfil_passhit, 0, "bpfil action on match");

SYSCTL_DECL(_net_inet_bpfil_stats);
SYSCTL_NODE(_net_inet_bpfil, OID_AUTO, stats, CTLFLAG_RD, NULL,
    "bpfil statistics");
SYSCTL_UQUAD(_net_inet_bpfil_stats, OID_AUTO, counter, CTLTYPE_U64,
    &bpfilstat_counter, 0, "total number of packets processed");
SYSCTL_UQUAD(_net_inet_bpfil_stats, OID_AUTO, error, CTLTYPE_U64,
    &bpfilstat_error, 0, "packets dropped due to errors");
SYSCTL_UQUAD(_net_inet_bpfil_stats, OID_AUTO, bpfmatch, CTLTYPE_U64,
    &bpfilstat_bpfmatch, 0, "packets matched by bpf program");
SYSCTL_UQUAD(_net_inet_bpfil_stats, OID_AUTO, drop, CTLTYPE_U64,
    &bpfilstat_drop, 0, "packets dropped by filter");

SYSCTL_PROC(_net_inet_bpfil, OID_AUTO, program, CTLTYPE_STRING | CTLFLAG_RW,
    &bpfil_progstring, sizeof(bpfil_progstring), &bpfil_proc_program, "A",
    "bpf program instructions in decimal with count first");

SYSCTL_PROC(_net_inet_bpfil, OID_AUTO, interface, CTLTYPE_STRING | CTLFLAG_RW,
    &bpfil_interface, sizeof(bpfil_interface), &bpfil_proc_interface, "A",
    "interface restriction");


/*
 * pfil hook that is called for each IPv4 packet making its way through the
 * stack in either direction.
 * The pfil subsystem holds a non-sleepable mutex somewhere when
 * calling our hook function, so we can't sleep at all.
 * It's very important to use the M_NOWAIT flag with all function calls
 * that support it so that they won't sleep, otherwise you get a panic.
 */
static int
bpfil_filter(void *arg, struct mbuf **m, struct ifnet *ifp, int dir,
    struct inpcb *inp)
{
	u_char *data;
	u_int len, totlen;
	int error = 0;

	// XXX this should never hit
	if ((bpfil_mode & dir) == 0)
		return (0);

	if (bpfil_interface[0] != '\0' && strcmp(bpfil_interface, ifp->if_xname) != 0)
		return (0);

	totlen = (*m)->m_pkthdr.len;
	// XXX: replicated from ng_bpf, why is this necessary?
	if (totlen == 0)
		return (0);

	++bpfilstat_counter;

	data = malloc(totlen, M_BPFIL, M_NOWAIT);
	if (data == NULL) {
		++bpfilstat_error;
		if (!bpfil_passerr) {
			error = ENOBUFS;
			goto out;
		} else
			return (0);
	}
	m_copydata(*m, 0, totlen, data);
	len = bpf_filter(bpfil_prog->bf_insns, data, totlen, totlen);
	free(data, M_BPFIL);

	if (len > 0) {
		++bpfilstat_bpfmatch;
		error = bpfil_passhit ? 0 : BPFIL_ERRNO;
	} else {
		error = bpfil_passhit ? BPFIL_ERRNO : 0;
	}

	if (error != 0)
		++bpfilstat_drop;		// Count only policy drops
out:
	if (error != 0)
		m_freem(*m);
	return (error);
}

static void
bpfil_setup(int mode)
{
	struct pfil_head *pfh_inet;
	VNET_ITERATOR_DECL(vnet_iter);

	KASSERT(mode >= 0 && mode < 3, ("bpfil_setup bad mode"));
	VNET_LIST_RLOCK();
	VNET_FOREACH(vnet_iter) {
		CURVNET_SET(vnet_iter);
		pfh_inet = pfil_head_get(PFIL_TYPE_AF, AF_INET);

		if (mode > 0)
			pfil_add_hook(bpfil_filter, NULL,
			    mode | PFIL_WAITOK, pfh_inet);
		else
			pfil_remove_hook(bpfil_filter, NULL,
			    PFIL_ALL | PFIL_WAITOK, pfh_inet);
		CURVNET_RESTORE();
	}
	VNET_LIST_RUNLOCK();
}

static int
bpfil_proc_mode(SYSCTL_HANDLER_ARGS)
{
	u_int u;

	if (req->newptr != NULL) {
		u = *(u_int *)req->newptr;
		if (u > 3)
			return (EDOM);
		if (u != bpfil_mode)
			bpfil_setup(u);
	}
	return (sysctl_handle_int(oidp, arg1, arg2, req));
}

static int
takeqint(const char **xp, u_quad_t *p)
{
	char *xend;

	if (**xp == '\0')
		return (ESRCH);
	*p = strtouq(*xp, &xend, 0);
	if (*xp == xend)
		return (EINVAL);
	*xp = xend;
	return (0);
}

#define	TAKEUINT(x, member) do {				\
	u_quad_t uqint;						\
	error = takeqint(&(x), &uqint);				\
	if (error) goto err;					\
	(member) = uqint;					\
	if ((member) != uqint) { error = E2BIG; goto err; }	\
} while (0)

static int
program_parse(const char *progstr, struct bpf_program *bp)
{
	const char *x = progstr;
	int error = 0;

	bp->bf_insns = NULL;
	TAKEUINT(x, bp->bf_len);
	bp->bf_insns = malloc(sizeof(*bp->bf_insns) * bp->bf_len,
	    M_BPFIL, M_ZERO);
	for (int i = 0; i < bp->bf_len; ++i) {
		struct bpf_insn *xsn = bp->bf_insns + i;
		TAKEUINT(x, xsn->code);
		TAKEUINT(x, xsn->jt);
		TAKEUINT(x, xsn->jf);
		TAKEUINT(x, xsn->k);
	}
	return (error);

err:
	if (bp->bf_insns != NULL)
		free(bp->bf_insns, M_BPFIL);
	return (error);
}

static int
bpfil_proc_program(SYSCTL_HANDLER_ARGS)
{
	struct bpf_program *bp;
	int error = 0;

	if (req->newptr != NULL) {
		bp = malloc(sizeof(*bp), M_BPFIL, M_ZERO);
		error = program_parse(req->newptr, bp);
		if (error) {
 err:
			free(bp, M_BPFIL);
			return (error);
		}
		if (bpf_validate(bp->bf_insns, bp->bf_len)) {
			if (bpfil_prog != NULL) {
				free(bpfil_prog->bf_insns, M_BPFIL);
				free(bpfil_prog, M_BPFIL);
			}
			bpfil_prog = bp;
		} else {
			error = EPROCUNAVAIL;
			goto err;
		}
	}
	return (sysctl_handle_string(oidp, arg1, arg2, req));
}

static int
bpfil_proc_interface(SYSCTL_HANDLER_ARGS)
{

	return (sysctl_handle_string(oidp, arg1, arg2, req));
}

static int
bpfil_modevent(module_t mod, int what, void *arg)
{

	switch (what) {
	case MOD_LOAD:
		return (0);

	case MOD_QUIESCE:
	case MOD_SHUTDOWN:
	case MOD_UNLOAD:
		bpfil_setup(0);
		if (bpfil_prog != NULL) {
			free(bpfil_prog->bf_insns, M_BPFIL);
			free(bpfil_prog, M_BPFIL);
			bpfil_prog = NULL;
			bpfil_progstring[0] = '\0';
		}
		return (0);

	default:
		return (EINVAL);
	}
}


static moduledata_t bpfil_mod = {
	.name = "bpfil",
	.evhand = bpfil_modevent,
};

DECLARE_MODULE(bpfil, bpfil_mod, SI_SUB_PSEUDO, SI_ORDER_FIRST);
MODULE_VERSION(bpfil, BPFILMODVERSION);
