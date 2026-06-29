#!/bin/bash

echo "Deleting all __pycache__ folders..."

# Recursively find and delete all __pycache__ directories
find . -type d -name "__pycache__" -prune -exec rm -rf {} \;

echo "Done."