#!/bin/bash
# AutoAssemble Database Backup Automation Script
# Cron schedule recommendation: 0 2 * * * (Run daily at 2:00 AM)

# Exit immediately if a command exits with a non-zero status
set -e

# Configuration
DB_HOST=${DB_HOST:-"database-1.cv44ak4uaxvi.ap-south-1.rds.amazonaws.com"}
DB_USER=${DB_USER:-"admin"}
DB_NAME=${DB_NAME:-"auto_assemble_db"}
BACKUP_DIR="/var/backups/autoassemble"
RETENTION_DAYS=7
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/db_backup_${DB_NAME}_${TIMESTAMP}.sql"
GZIP_FILE="${BACKUP_FILE}.gz"

# Create backup directory if it does not exist
mkdir -p "$BACKUP_DIR"

# Print log start
echo "[$(date)] Starting MySQL backup for database: $DB_NAME..."

# Execute mysqldump
# Note: The database password should be stored in ~/.my.cnf or passed via environment variable MYSQL_PWD
if mysqldump -h "$DB_HOST" -u "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"; then
    echo "[$(date)] Backup file created: $BACKUP_FILE"
    
    # Compress the backup
    gzip "$BACKUP_FILE"
    echo "[$(date)] Compression complete: $GZIP_FILE"
    
    # Optional: Upload to AWS S3 (Uncomment if S3 access is configured)
    # S3_BUCKET="autoassemble-backups-bucket"
    # aws s3 cp "$GZIP_FILE" "s3://$S3_BUCKET/db_backups/" --region ap-south-1
    # echo "[$(date)] Uploaded backup to S3 bucket: s3://$S3_BUCKET"
    
    # Clean up backups older than retention policy (7 days)
    echo "[$(date)] Cleaning up backups older than $RETENTION_DAYS days in $BACKUP_DIR..."
    find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
    echo "[$(date)] Backup rotation complete."
    
else
    echo "[$(date)] ERROR: Database backup failed." >&2
    exit 1
fi

echo "[$(date)] Backup operation completed successfully."
exit 0
