# trap ctrl-c and call ctrl_c()
trap ctrl_c INT

function ctrl_c() {
    echo "Trapped CTRL-C, exiting ..."
    python3 /app/alert.py --message="process interrupted, exiting" --slack_webhook_url="$SLACK_WEBHOOK_URL"
	exit 0
}

export SENSOR_ID=$(python3 /app/generate_sensor_id.py)
if [ -z $SENSOR_ID ]; then
    echo "Failed to generate sensor id"
    exit 1
fi
echo "Monitoring started with sensor id $SENSOR_ID"

python3 /app/alert.py --message="process started" --slack_webhook_url="$SLACK_WEBHOOK_URL"
redis-server --daemonize yes

if [ "$TEST_MODE" = "1" ]; then
    echo "Test mode"
    echo "Starting WHOIS test server" && python3 /app/whois_test_server.py &
    echo "Starting DNS test server" && python3 /app/dns_test_server.py &
    python3 /app/run.py --whois 'domain=dummy.net;server=127.0.0.1;timeout=30;pause=30' --dns 'domain=dummy.net;resolvers=127.0.0.1;pause=20' --dns 'domain=ping.dummy.net;resolvers=127.0.0.1;pause=20' --slack_webhook_url="$SLACK_WEBHOOK_URL"
else
    python3 /app/run.py $COMMANDS --slack_webhook_url="$SLACK_WEBHOOK_URL"
fi

python3 /app/alert.py --message="process stopped" --slack_webhook_url="$SLACK_WEBHOOK_URL"
echo "Monitoring shutdown with sensor id $SENSOR_ID"
exit 0

