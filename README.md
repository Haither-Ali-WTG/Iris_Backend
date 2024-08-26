# Introduction

Iris is the new (as of 2022) haproxy deployment automation

For more information, see the `HAProxy` directory in the `documentation` repo.



#### AU2 SAND Internal

| Instance | Description | DNS Name | Firewall Object | NAT | Proto | Transport
| :-: |:-: |:-: |:-: | :-: | :-: | :-: | 
| SAND Internal | SAND Internal Services | au2-sand-internal.oc.wisegrid.net | au2-sand-internal.oc.wisegrid.net | 10.2.3.11 -> 10.2.136.137:2007 | HTTP | TCP |
| SAND Internal | SAND Internal Services | au2-sand-internal.oc.wisegrid.net | au2-sand-internal.oc.wisegrid.net | 10.2.3.11 -> 10.2.136.137:2008 | HTTPS | TCP |
| au2prodfrontend1prodservices | AU2 PROD Services | au2-9.oc.wisegrid.net | au2-9.oc.wisegrid.net-180.235.158.129 | 10.2.64.137:2009 -> 180.235.158.129:80 | HTTP | TCP |
| au2prodfrontend1prodservices | AU2 PROD Services | au2-9.oc.wisegrid.net | au2-9.oc.wisegrid.net-180.235.158.129 | 10.2.64.137:2010 -> 180.235.158.129:443 | HTTPS | TCP |