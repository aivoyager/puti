#!/usr/bin/env bash
nohup python -u main.py > ./logs/server.log 2>&1 &

while true; do
  sleep 10
done
