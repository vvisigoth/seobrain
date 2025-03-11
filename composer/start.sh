#!/bin/bash

SESSION_NAME=$(basename "$PWD")
#SESSION_NAME=tester

SCRIPT1=reich.py

# Start a new tmux session named $SESSION_NAME
tmux new-session -d -s $SESSION_NAME

# Rename the first window and split it vertically
tmux rename-window -t $SESSION_NAME:0 'Main'
#tmux send-keys -t $SESSION_NAME:0 "export OPENAI_API_KEY=$(cat key)" C-m
tmux send-keys -t $SESSION_NAME:0 "clear" C-m
tmux send-keys -t $SESSION_NAME:0 "source bin/activate" C-m
tmux send-keys -t $SESSION_NAME:0 "python $SCRIPT1" C-m
tmux split-window -h -t $SESSION_NAME:0

# Split the new pane horizontally
tmux split-window -v -t $SESSION_NAME:0.1 -p 10

# Set up logging for pane 0.1 with a max of 1000 lines
#tmux pipe-pane -t ${SESSION_NAME}:0.1 -o "tee -a ${SESSION_NAME}_terminal_log.txt | tail -n 1000 > ${SESSION_NAME}_terminal_log.tmp && mv ${SESSION_NAME}_terminal_log.tmp ${SESSION_NAME}_terminal_log.txt"
tmux send-keys -t $SESSION_NAME:0.1 "script -q -c 'bash' ${SESSION_NAME}_log.txt & (tail -n 1000 -F ${SESSION_NAME}_log.txt > ${SESSION_NAME}_log.tmp && mv ${SESSION_NAME}_log.tmp ${SESSION_NAME}_log.txt)" C-m

# Create a second window and run the second script
tmux new-window -t $SESSION_NAME:1 -n 'Vim'
tmux send-keys -t $SESSION_NAME:1 "vim ." C-m

# Attach to the session
tmux attach-session -t $SESSION_NAME
