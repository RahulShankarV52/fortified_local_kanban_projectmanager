#!/bin/bash

# 1. Configuration
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="./backups"
CONTAINER_NAME="kanban_db"
DB_USER="kanban_admin"

mkdir -p $BACKUP_DIR

echo "🔒 Starting Backup for Fortified Kanban..."

# 2. Dump the Database (This contains the encrypted text)
docker exec -t $CONTAINER_NAME pg_dump -U $DB_USER kanban_prod > "$BACKUP_DIR/db_dump_$TIMESTAMP.sql"

# 3. Encrypt the Backup File (Double Encryption!)
# We use OpenSSL to encrypt the SQL file itself with a password.
# You will be prompted to type a password.
echo "🔑 Encrypting the backup file..."
openssl enc -aes-256-cbc -salt -in "$BACKUP_DIR/db_dump_$TIMESTAMP.sql" -out "$BACKUP_DIR/backup_$TIMESTAMP.enc" -pbkdf2

# 4. Cleanup raw SQL
rm "$BACKUP_DIR/db_dump_$TIMESTAMP.sql"

echo "✅ Success! Encrypted backup saved to: $BACKUP_DIR/backup_$TIMESTAMP.enc"
