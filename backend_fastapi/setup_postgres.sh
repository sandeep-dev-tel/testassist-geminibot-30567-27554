#!/bin/bash
# This script initializes PostgreSQL exactly as requested: starts the service, opens an interactive psql session,
# creates database/user, grants privileges, changes schema ownership, and loads the schema from init.sql.

set -e

# Step 1: Start PostgreSQL service
sudo service postgresql start

# Step 2: Open psql as postgres superuser
sudo -u postgres psql <<EOSQL

-- Step 3: Create the database
CREATE DATABASE chatdb2;

-- Step 4: Create the user with password
CREATE USER kavia WITH PASSWORD 'yourpassword';

-- Step 5: Grant all privileges on the new database to the new user
GRANT ALL PRIVILEGES ON DATABASE chatdb2 TO kavia;

EOSQL

# Step 6: Connect to the new database as postgres and grant schema privileges
sudo -u postgres psql -d chatdb2 <<EOSQL2

-- Step 7: Grant all on public schema to the new user
GRANT ALL ON SCHEMA public TO kavia;
ALTER SCHEMA public OWNER TO kavia;

EOSQL2

# Step 8: Run the init.sql script as the new user to initialize the schema
psql -U kavia -d chatdb2 -f ../database_container/init.sql

echo "PostgreSQL setup completed with exact user-specified commands."
