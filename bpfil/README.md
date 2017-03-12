# FreeBSD packet filter (kernel module) using bpf/pcal/tcpdump rules

This is a prototype kernel module that implements a packet filter
(firewall) that uses Berkeley Packet Filter (bpf) [aka pfil/pcap]
instructions to discriminate packets.

Last known state: It works and demonstrates the concept.

- load bpf program via sysctl
- only one bpf program supported
- possible action is pass or drop; no finer control

This was never used in production. Caveat emptor.
