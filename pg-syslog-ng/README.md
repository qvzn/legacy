# Real-time & filtered logs using PostgreSQL & syslog-ng

## loghost setup

Create schema using postgres.sql

Set loghost and user passwords appropriately

Set up syslog-ng based on syslog-ng.conf

Use daemontools to run psql.service.run under the "sql" user.
Credentials are best specified in ~sql/.pgpass

## viewing logs

pgsyslog.py supports filtering and real-time view

Specify database using -d/--dbconnfile or SYSLOG_PGDB

