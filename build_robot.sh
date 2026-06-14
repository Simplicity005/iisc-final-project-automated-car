#!/bin/bash

# Navigate to your workspace
cd ~/ros2_ws/ || { echo "Directory not found!"; exit 1; }

# Build: no args or "all" → full build; anything else → build that package only
if [ $# -eq 0 ] || [ "$1" = "all" ]; then
    colcon build
else
    colcon build --packages-select "$1"
fi

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
