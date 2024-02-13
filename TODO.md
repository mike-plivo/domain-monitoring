# Features list
* ping domain
* https check
* DONE - launch multiple sensors from the same container

# Redis arguments
```
  --redis-host=127.0.0.1
  --redis-port=6379
  --redis-db=0
```

# Arguments below can be passed multiple times
```
  --ping=<domain/subdomain>[attempts=4;timeout=10]
  --https=<URL>[method=GET;connect_timeout=5;read_timeout=30;valid_response_codes=200;content_type=text/plain;request_body=<optional>;valid_response_body=<optional>;verify_ssl=false]
  DONE: --dns=<domain/subdomain>[resolvers=1.1.1.1,8.8.8.8;types=A,CNAME,MX,SOA,NS,TXT,...]
  DONE: --whois=<domain>[server=<optional>;timeout=30]
```

