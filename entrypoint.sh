# trap ctrl-c and call ctrl_c()
trap ctrl_c INT

function ctrl_c() {
        echo "Trapped CTRL-C, exiting ..."
	exit 0
}

echo "Monitor $DOMAIN"
redis-server --daemonize yes

if [ "$TEST_MODE" = "1" ]; then
    echo "Test mode"
    echo "Starting test server"
    python3 /app/whois_test_server.py &
fi

#rqworker --verbose &
while true; do
    if [ "$TEST_MODE" = "1" ]; then
        python3 /app/monitor.py --domain=dummy.net --whois_timeout=30 --whois_server=127.0.0.1 --slack_webhook_url="$SLACK_WEBHOOK_URL"
        sleep 30
    else
        python3 /app/monitor.py --domain=$DOMAIN --whois_timeout=30 --slack_webhook_url="$SLACK_WEBHOOK_URL"
        sleep 300
    fi
done

