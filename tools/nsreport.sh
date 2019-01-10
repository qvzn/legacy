#! /bin/sh
#
# Copyright (c) 2018 Trit Networks.
# All rights reserved.
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
# $Id: nsreport.sh 158 2019-01-07 10:17:11Z dima $
#

set -e

progname=$(basename $0)

VERBOSE=0
opt_t=2

error() {
	echo "$progname: $*" >&2
	exit 1
}

usage() {
	echo "usage: $progname [-Cv] [-t timeout(=${opt_t})] domain" >&2
	exit 2
}

parse_args() {
	while getopts "Ct:v" option ; do
		case $option in
		C)
			opt_C=1
			;;
		t)
			opt_t="$OPTARG"
			;;
		v)
		        VERBOSE=$(($VERBOSE + 1))
			;;
		*)
			usage
			;;
		esac
	done
}

parse_args "$@"

shift $(($OPTIND - 1))
#echo "args now: $*"
#echo "#=$#"
#echo "1=$1"

if [ -z "$1" ]; then
    usage
fi

DOMAIN="$1"
shift

DIG="dig +timeout=${opt_t}"
DIGSH="$DIG +short"

for ns in $($DIGSH ns "$DOMAIN"); do
    NS=$(echo "$ns" | sed 's/\.$//')
    s="$NS"
    s="$s ($($DIGSH any "$ns" | xargs))"
    if [ $opt_C ]; then
	s="$s $($DIGSH hostname.bind chaos txt "@$ns" || true)"
    fi
    echo "$s"
done
