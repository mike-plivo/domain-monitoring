#!/bin/sh
docker run -e TEST_MODE=1 --env-file .env -ti local/domain_monitor
