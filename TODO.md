# Features list
* ping domain
* DONE - https check
* DONE - launch multiple sensors from the same container

# Redis arguments
```
  --redis-host=127.0.0.1
  --redis-port=6379
  --redis-db=0
```

# Arguments below can be passed multiple times
```
  --ping domain=<domain>;attempts=4;timeout=10
  DONE: --whois domain=<domain>;server=<optional>;timeout=30
  DONE: --dns domain=<domain>;resolvers=<resolvers>;record_types=<record_types>
  DONE: --http url=<url>;method=<method>;timeout=<timeout>;connect_timeout=<connect_timeout>;payload=<payload>;headers=<headers>;verify_ssl=<verify_ssl>
```

