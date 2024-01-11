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

# Execute in local test mode
In this mode, no domain is tested. It's starting a test dns server and a test whois server responding with random data.
```
bash ./run_test.sh
```

# Execute with your domain
```
bash ./run.sh
```

