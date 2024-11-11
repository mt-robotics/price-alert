#!/bin/bash
#
## Function to handle termination
terminate() {
	echo "Termination signal received. Stopping service..."
	exit 0
}

# Trap termination signals (SIGINT, SIGTERM)
trap terminate SIGINT SIGTERM

while true; do
	nohup python3 main.py > nohup.out 2>&1 &
	PID=$!
	
	# Print out the PID
	echo "Started service with PID: $PID"

	# Wait for the process ID to exit and log the result
	wait $PID

	# Capture exit code
	EXIT_CODE=$?

	# Log if the process crashes
	if [ $EXIT_CODE -ne 0 ]; then
		echo "Service stopped with exit code $EXIT_CODE. Restarting..." | tee -a error.log
	else
		echo "Service stopped normally." | tee -a error.log
		break
	fi

	# Wait a few seconds before restarting
	sleep 5
done &

disown
