#!/bin/bash
# Script to create PostgreSQL user and database
sudo -u postgres psql -c "CREATE ROLE accounting WITH LOGIN CREATEDB PASSWORD 'double';"
sudo -u postgres psql -c "CREATE DATABASE accounting_db OWNER accounting;"
