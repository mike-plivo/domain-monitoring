WHOIS and DNS Records changes monitoring

# Docker command to build the image locally
```
docker build -t local/domain_monitor .
```

# Setup your .env file
Note: you can also use environment variables instead of the .env file.

```
# your domain
DOMAIN=yourdomain
# your slack webhook URL, this is optional
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXXXXXXXX/XXXXXXXXX/XXXXXXXXXXXXXXXXXXXXXXXX
# dns nameservers to resolve the domain records
DNS_NAMESERVERS=x.x.x.x,y.y.y.y
```

# Execute in local test mode
In this mode, no domain is tested. It's starting a test dns server and a test whois server responding with random data.
```
docker run -e TEST_MODE=1 --env-file .env -ti local/domain_monitor
```

You can also use the following script:
```
bash ./run_test.sh
```

# Execute with your domain
```
docker run --env-file .env -ti local/domain_monitor
```

You can also use the following script:
```
bash ./run.sh
```

