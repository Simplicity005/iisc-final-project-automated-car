#!/bin/bash

# Navigate to your workspace
cd ~/ros2_ws/ || { echo "Directory not found!"; exit 1; }

# Build the specific package
colcon build --packages-select my_robot

# Check which shell is running and source the matching setup file
if [ -n "$ZSH_VERSION" ]; then
    echo "Sourcing setup.zsh..."
    source install/setup.zsh
elif [ -n "$BASH_VERSION" ]; then
    echo "Sourcing setup.bash..."
    source install/setup.bash
else
    echo "Sourcing generic setup.sh..."
    source install/setup.sh
fi
