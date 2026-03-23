#!/bin/bash
# Generate a strong JWT_SECRET for SYSTVETAM dispatch
# Run this once — save the output as your Railway JWT_SECRET env var
# This value is also your login password for username: levi

echo "Your JWT_SECRET (copy this EXACTLY into Railway and save it as your login password):"
openssl rand -hex 32
