#!/bin/bash
#
## Function to handle termination
terminate() {
	echo "Termination signal received. Stopping service..."

	# Create a flag file to indicate that we want to stop the service manually
	touch stop_service.flag
	exit 0
}

# Trap termination signals (SIGINT, SIGTERM)
trap terminate SIGINT SIGTERM

while true; do
	# Check if the stop_service.flag file exits, if yes, break the loop
	if [ -f stop_service.flag ]; then
		echo "Manual stop requested. Stopping service..."
		break
	fi

	# Start the Python script in the background
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
done 

# Cleanup: Remove the flag file if it exits
if [ -f stop_service.flag ]; then
	rm stop_service.flag
	echo "Service fully stopped."
fi &
disown

# # Option 2
# #!bin/bash

# terminate() {
#     echo "Termination Signal Received"

#     touch stop_service.flag
#     exit 0
# }

# trap terminate SIGINT SIGTERM

# while true; do

#     if [ -f stop_service.flag ]; then
#         echo "Manual Stopping..."
#         break
#     fi

#     python3 main.py > nohup.out 2>&1 
#     PID=$!

#     echo "Start service with PID: $PID"

#     wait $PID

#     EXIT_CODE=$?

#     if [ $EXIT_CODE -ne 0 ]; then
#         echo "Stop with exit code: $EXIT_CODE. Restarting..." | tee -a error.log

#     else
#         echo "Stop normally. Restarting..."  | tee -a error.log
#         break
#     fi

# done &

# LOOP_PID=$!
# disown

# wait $LOOP_PID

# if [ -f stop_service.flag ]; then
#     rm stop_service.flag
#     echo "Service fully stopped."
# fi


# # Option 3
# #!bin/bash

# terminate() {
#     echo "Termination Signal Received"

#     touch stop_service.flag
#     exit 0
# }

# trap terminate SIGINT SIGTERM

# while true; do

#     if [ -f stop_service.flag ]; then
#         echo "Manual Stopping..."
# 		rm stop_service.flag
#         break
#     fi

#     python3 main.py > nohup.out 2>&1 
#     PID=$!

#     echo "Start service with PID: $PID"

#     wait $PID

#     EXIT_CODE=$?

#     if [ $EXIT_CODE -ne 0 ]; then
#         echo "Stop with exit code: $EXIT_CODE. Restarting..." | tee -a error.log

#     else
#         echo "Stop normally. Restarting..."  | tee -a error.log
# 		rm stop_service.flag
#         break
#     fi

# done &
# disown
