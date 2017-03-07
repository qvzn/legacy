CREATE TABLE logs (
   seq serial not null,
   stamp timestamp not null default current_timestamp,
   sqluser varchar default current_user not null,
   host varchar default NULL,
   facility varchar default NULL,
   priority varchar default NULL,
   level varchar default NULL,
   tag varchar default NULL,
   date date default NULL,
   time time default NULL,
   program varchar default NULL,
   msg text,
   PRIMARY KEY (seq)
);

CREATE INDEX logs_stamp_ix ON logs USING btree (stamp);

CREATE ROLE syslogserver LOGIN;
ALTER ROLE syslogserver SET synchronous_commit TO off;
GRANT INSERT ON logs TO syslogserver;
GRANT USAGE, UPDATE ON SEQUENCE logs_seq_seq TO syslogserver;

CREATE ROLE syslogreader LOGIN;
GRANT SELECT ON logs TO syslogreader;


CREATE INDEX logs_stamp_msg_ix ON logs USING btree (stamp,host,msg);


CREATE ROLE pfylogserver LOGIN PASSWORD 'DONOTUSETHIS';
GRANT syslogserver TO pfylogserver;
ALTER ROLE pfylogserver SET synchronous_commit TO OFF;
