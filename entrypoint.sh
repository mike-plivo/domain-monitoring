# trap ctrl-c and call ctrl_c()
trap ctrl_c INT

function ctrl_c() {
        echo "Trapped CTRL-C, exiting ..."
	exit 0
}

echo "Monitoring $DOMAIN started"
redis-server --daemonize yes

if [ "$TEST_MODE" = "1" ]; then
    echo "Test mode"
    [ "$WHOIS_MONITOR_DISABLED" = "1" ] || echo "Starting WHOIS test server" && python3 /app/whois_test_server.py &
    [ "$DNS_MONITOR_DISABLED" = "1" ] || echo "Starting DNS test server" && python3 /app/dns_test_server.py &
fi

if [ "$WHOIS_MONITOR_DISABLED" = "1" ]; then
    echo "WHOIS monitor disabled"
else
    while true; do
        if [ "$TEST_MODE" = "1" ]; then
            python3 /app/whois_monitor.py --domain=dummy.net --whois_timeout=30 --whois_server=127.0.0.1 --slack_webhook_url="$SLACK_WEBHOOK_URL"
            sleep 45
        else
            python3 /app/whois_monitor.py --domain=$DOMAIN --whois_timeout=30 --slack_webhook_url="$SLACK_WEBHOOK_URL"
            sleep 300
        fi
    done &
fi

if [ "$DNS_MONITOR_DISABLED" = "1" ]; then
    echo "DNS monitor disabled"
else
    while true; do
        if [ "$TEST_MODE" = "1" ]; then
            python3 /app/dns_monitor.py --domain=dummy.net --resolvers=127.0.0.1 --slack_webhook_url="$SLACK_WEBHOOK_URL"
            sleep 30
        else
            python3 /app/dns_monitor.py --domain=$DOMAIN --resolver="$DNS_RESOLVERS" --slack_webhook_url="$SLACK_WEBHOOK_URL"
            sleep 120
        fi
    done
fi


echo "Monitoring $DOMAIN finished"

