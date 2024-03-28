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
1. In test mode, WHOIS monitoring takes place every thirty seconds, while DNS records are monitored every twenty seconds, and HTTP monitoring is performed every fifteen seconds.
```
bash ./run_test.sh
```

# Production mode
1. In this mode, actual domain is tested.
1. WHOIS monitoring occurs at five-minute intervals, DNS records are checked every two minutes, and HTTP monitoring is performed every minute.

```
bash ./run.sh
```

# Deployment Fly.io
```
# deploy the <app_name> in the iad region
flyctl deploy -a <app_name> -r iad --vm-cpu-kind shared --vm-cpus 1 --vm-memory 512

# by defautl, deploy will create two machines, scale it to one
flyctl scale count 1 -a <app_name> --max-per-region 1 -r iad,fra,bom,lax --vm-cpu-kind shared --vm-cpus 1 --vm-memory 512

# retrieve the id of the machine deployed
flyctl machines list -a <app_name>

# clone the machine to the other regions
flyctl machines clone <id_machine> -a <app_name> -r fra
flyctl machines clone <id_machine> -a <app_name> -r bom
flyctl machines clone <id_machine> -a <app_name> -r lax
```



