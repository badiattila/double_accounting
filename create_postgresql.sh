#!/usr/bin/env bash

# Safe PostgreSQL setup script for the Django ledger project.
# Idempotent: re-running won't error if role/db already exist.
# Creates a database and superuser (optional) and ensures timezone is UTC.

set -euo pipefail
IFS=$'\n\t'

######################################################################
# Configuration (override via environment variables before execution)
######################################################################
DB_NAME="${DB_NAME:-ledger}"
DB_USER="${DB_USER:-$USER}"
DB_SUPERUSER="${DB_SUPERUSER:-false}"          # true => make role superuser
DB_ENCODING="${DB_ENCODING:-UTF8}"
DB_LOCALE="${DB_LOCALE:-en_US.UTF-8}"
DB_TIMEZONE="${DB_TIMEZONE:-UTC}"
WRITE_ENV_FILE="${WRITE_ENV_FILE:-true}"       # write .env.local with URLs
QUIET="${QUIET:-false}"                        # true => less output
VERBOSE="${VERBOSE:-false}"                    # true => psql verbose

ASYNC_DRIVER="${ASYNC_DRIVER:-asyncpg}"        # for async DATABASE_URL
DB_PORT="${DB_PORT:-5432}"
DB_HOST="${DB_HOST:-localhost}"

######################################################################
# Logging helpers
######################################################################
log() { [ "$QUIET" = true ] || printf "[INFO] %s\n" "$*"; }
warn() { printf "[WARN] %s\n" "$*" >&2; }
die() { printf "[ERROR] %s\n" "$*" >&2; exit 1; }

psql_cmd() {
	local db="$1"; shift || true
	local extra=""
	[ "$VERBOSE" = true ] && extra="-e"
	sudo -u postgres psql $extra -v ON_ERROR_STOP=1 -d "$db" -c "$*"
}

need_cmd() { command -v "$1" >/dev/null 2>&1 || die "Required command '$1' not found"; }

######################################################################
# Pre-flight checks
######################################################################
need_cmd sudo
need_cmd grep
need_cmd cut

if ! command -v psql >/dev/null 2>&1; then
	log "PostgreSQL client not found; attempting installation (Debian/Ubuntu)."
	if [ -f /etc/debian_version ]; then
		if [ "${EUID}" -ne 0 ]; then
			sudo apt-get update -y
			sudo apt-get install -y postgresql postgresql-contrib
		else
			apt-get update -y
			apt-get install -y postgresql postgresql-contrib
		fi
	else
		die "Automatic install only supported for Debian-based systems. Install PostgreSQL manually and re-run."
	fi
fi

if ! systemctl list-unit-files | grep -q '^postgresql'; then
	warn "systemd unit 'postgresql' not found. Assuming service already managed elsewhere."
else
	log "Enabling and starting PostgreSQL service."
	sudo systemctl enable --now postgresql || die "Failed to enable/start postgresql service"
fi

######################################################################
# Role creation
######################################################################
ROLE_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" || true)
if [ "$ROLE_EXISTS" = "1" ]; then
	log "Role '${DB_USER}' already exists. Skipping creation."
else
	log "Creating role '${DB_USER}' (superuser=${DB_SUPERUSER})."
	if [ "$DB_SUPERUSER" = true ]; then
		sudo -u postgres createuser -s "$DB_USER" || die "Failed to create superuser role"
	else
		sudo -u postgres createuser -d -r "$DB_USER" || die "Failed to create role"
	fi
fi

######################################################################
# Database creation
######################################################################
DB_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" || true)
if [ "$DB_EXISTS" = "1" ]; then
	log "Database '${DB_NAME}' already exists."
else
	log "Creating database '${DB_NAME}' with owner '${DB_USER}'."
	sudo -u postgres createdb -E "$DB_ENCODING" -O "$DB_USER" "$DB_NAME" || die "Failed to create database"
fi

######################################################################
# Timezone enforcement
######################################################################
CURRENT_TZ=$(sudo -u postgres psql -d "$DB_NAME" -tAc "SHOW timezone;" | tr -d '[:space:]')
if [ "$CURRENT_TZ" != "$DB_TIMEZONE" ]; then
	log "Setting timezone for '${DB_NAME}' to ${DB_TIMEZONE} (was ${CURRENT_TZ})."
	psql_cmd "$DB_NAME" "ALTER DATABASE ${DB_NAME} SET timezone TO '${DB_TIMEZONE}';"
else
	log "Database timezone already ${DB_TIMEZONE}."
fi

######################################################################
# Connection URLs (export + optional .env.local file)
######################################################################
DATABASE_URL="postgresql+${ASYNC_DRIVER}://${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
DATABASE_URL_SYNC="postgresql://${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
export DATABASE_URL DATABASE_URL_SYNC

log "DATABASE_URL=${DATABASE_URL}"
log "DATABASE_URL_SYNC=${DATABASE_URL_SYNC}"

if [ "$WRITE_ENV_FILE" = true ]; then
	ENV_FILE=".env.local"
	if [ -f "$ENV_FILE" ]; then
		if grep -q '^DATABASE_URL=' "$ENV_FILE"; then
			log "Updating DATABASE_URL entries in ${ENV_FILE}."
			# Use sed in-place update
			sed -i "s|^DATABASE_URL=.*|DATABASE_URL=${DATABASE_URL}|" "$ENV_FILE" || true
			sed -i "s|^DATABASE_URL_SYNC=.*|DATABASE_URL_SYNC=${DATABASE_URL_SYNC}|" "$ENV_FILE" || true
		else
			log "Appending DATABASE_URL entries to ${ENV_FILE}."
			{
				echo "DATABASE_URL=${DATABASE_URL}"
				echo "DATABASE_URL_SYNC=${DATABASE_URL_SYNC}"
			} >> "$ENV_FILE"
		fi
	else
		log "Writing ${ENV_FILE} with database URLs."
		cat > "$ENV_FILE" <<EOF
# Generated by create_postgresql.sh
DATABASE_URL=${DATABASE_URL}
DATABASE_URL_SYNC=${DATABASE_URL_SYNC}
EOF
	fi
fi

######################################################################
# Summary
######################################################################
log "PostgreSQL setup complete."
log "You can test connection: psql ${DB_NAME} (role: ${DB_USER})"

exit 0
