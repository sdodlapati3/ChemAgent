#!/bin/bash
# Wrapper script to run tests with the correct Python environment

echo "Loading Python environment..."
module load python3

echo "Running ChemAgent verification tests..."
crun -p ~/envs/chemagent python test_improvements.py

echo ""
echo "Test complete!"
