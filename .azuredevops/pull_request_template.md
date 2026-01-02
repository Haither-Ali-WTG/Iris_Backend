The CI/CD automation that is driven by this repository can deploy both minor
**pre-approved** and **major** changes to the HAProxy service.  Please review the
criteria below which is a guide for requestors and reviewers to identify clear
cases of the two changes types, and mark any checkbox that applies.

Changes that are not covered by these scenarios need to be assessed by reviewers
with a view to what could potentially go wrong when deployed.

**Pre-Approved Changes**

- [ ] changes for up to 3 backends
- [ ] changes to test backends
- [ ] acl additions/modifications for subnets up to /29 (8 network addresses)

**Potentially Major Changes** requiring deployment considerations

- [ ] any change in the GLOBAL, DEFAULT, STATS or FRONTEND sections
- [ ] wildcarded subdomain changes (not test services)
- [ ] changes to \*/instances/*
- [ ] changes to \*/machine_clusters/*
- [ ] safety check security exceptions
- [ ] http-\* header mangling
- [ ] new instances or new ports

(*) backend = service = application (can be multiple backends per customer, eg. UPS)
