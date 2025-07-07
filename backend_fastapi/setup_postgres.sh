#!/bin/bash
# Automate PostgreSQL setup: start service, create db/user, grant privileges, set schema owner, initialize from SQL file.

set -euo pipefail

DB_NAME="chatdb2"
DB_USER="kavia"
DB_PASSWORD="yourpassword"  # TODO: CHANGE THIS! Set a secure password before running.
INIT_SQL_REL_PATH="../database_container/init.sql"

# Optional: check for required utilities
for util in psql pg_isready; do
  if ! command -v $util &>/dev/null; then
    echo "ERROR: $util is required but not installed/available in PATH."
    exit 1
  fi
done

echo "Starting (or ensuring) PostgreSQL service is running..."
if command -v systemctl &>/dev/null; then
  sudo systemctl start postgresql || echo "systemctl start failed, may already be running or is managed elsewhere."
elif command -v service &>/dev/null; then
  sudo service postgresql start || echo "service start failed, may already be running or is managed elsewhere."
else
  echo "Not running on a system with systemctl/service; ensure PostgreSQL is running manually."
fi

echo "Waiting for PostgreSQL to become available..."
for i in {1..10}; do
  if pg_isready -U postgres &>/dev/null; then
    break
  fi
  echo "  Still waiting for PostgreSQL to be ready... ($i/10)"
  sleep 1
done
if ! pg_isready -U postgres &>/dev/null; then
  echo "ERROR: PostgreSQL server did not become ready in time."
  exit 1
fi

# Create database if not exists
echo "Creating database '$DB_NAME' if it does not exist..."
psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}';" | grep -q 1 \
  || psql -U postgres -c "CREATE DATABASE ${DB_NAME};"

# Create user if not exists and set password (idempotent)
echo "Creating user '$DB_USER' if it does not exist..."
psql -U postgres -tc "SELECT 1 FROM pg_roles WHERE rolname = '${DB_USER}';" | grep -q 1 \
  || psql -U postgres -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';  -- CHANGE password!"

# Ensure user password (safe for rerun)
psql -U postgres -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';  -- CHANGE password!"

# Grant privileges on database
echo "Granting ALL privileges on database '$DB_NAME' to '$DB_USER'..."
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

# Change schema privileges and ownership
echo "Granting ALL on schema public to '$DB_USER' and making '$DB_USER' the schema owner..."
psql -U postgres -d "${DB_NAME}" -c "GRANT ALL ON SCHEMA public TO ${DB_USER};"
psql -U postgres -d "${DB_NAME}" -c "ALTER SCHEMA public OWNER TO ${DB_USER};"

# Find/calculate init.sql absolute path
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INIT_SQL="${SCRIPT_DIR}/${INIT_SQL_REL_PATH}"

if [ ! -f "$INIT_SQL" ]; then
  echo "ERROR: Could not find init.sql at $INIT_SQL"
  exit 1
fi

echo "Initializing database schema from $INIT_SQL..."
# Use PGPASSWORD for automation; remove/comment for production!
export PGPASSWORD="${DB_PASSWORD}"
psql -U "${DB_USER}" -d "${DB_NAME}" -f "$INIT_SQL"
unset PGPASSWORD

echo "PostgreSQL setup complete!"
echo "If running in production, set a strong password for '${DB_USER}' and remove it from this script."
