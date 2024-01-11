WHOIS and DNS Records changes monitoring

# Docker command to build the image locally
```
docker build -t local/domain_monitor .
```

# Setup your .env file
```
cp .env.example .env
```

Then edit .env with your configuration.

# Test mode
1. In this mode, actual domain is not tested. Instead, a test DNS server and a test WHOIS server are initiated, both providing random data in response.
1. In test mode, WHOIS monitoring takes place every 30 seconds, while DNS records are monitored every 20 seconds.
```
bash ./run_test.sh
```

# Production mode
1. In this mode, actual domain is tested.
1. WHOIS monitoring occurs at five-minute intervals and DNS records are checked every two minutes.
```
bash ./run.sh
```



