#!/bin/bash

#############################################
# Frappe Backup to S3 Script
# Backs up Frappe database and files to AWS S3
# Keeps only the 2 most recent backups in S3
# Container cleanup is handled by Frappe automatically
#############################################

# Configuration Variables
SITE_NAME="teamtest.btcfi.wtf"
S3_BUCKET="s3://frappe-backup-demo"  # UPDATE THIS
CONTAINER_NAME="frappe-backend-1"
KEEP_BACKUPS_S3=2  # Number of backups to keep in S3
LOG_FILE="$HOME/backup-to-s3.log"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to check if command succeeded
check_status() {
    if [ $? -eq 0 ]; then
        log_message "✓ $1 - SUCCESS"
    else
        log_message "✗ $1 - FAILED"
        exit 1
    fi
}

# Start backup process
log_message "========================================="
log_message "Starting backup process"
log_message "========================================="

# Check if container is running
if ! docker ps | grep -q $CONTAINER_NAME; then
    log_message "ERROR: Container $CONTAINER_NAME is not running"
    exit 1
fi
log_message "✓ Container $CONTAINER_NAME is running"

# Create Frappe backup
log_message "Creating Frappe backup..."
docker exec $CONTAINER_NAME bench --site $SITE_NAME backup --with-files 2>&1 | tee -a "$LOG_FILE"
check_status "Frappe backup creation"

# Wait a moment for backup to complete
sleep 3

# Define backup path in container
BACKUP_PATH="/home/frappe/frappe-bench/sites/$SITE_NAME/private/backups"

# Get the latest backup files
log_message "Identifying latest backup files..."
LATEST_DB=$(docker exec $CONTAINER_NAME bash -c "ls -t $BACKUP_PATH/*database.sql.gz 2>/dev/null | head -1")
LATEST_CONFIG=$(docker exec $CONTAINER_NAME bash -c "ls -t $BACKUP_PATH/*site_config_backup.json 2>/dev/null | head -1")

if [ -z "$LATEST_DB" ]; then
    log_message "ERROR: No database backup found"
    exit 1
fi

log_message "Latest DB backup: $LATEST_DB"
log_message "Latest Config backup: $LATEST_CONFIG"

# Extract filenames
DB_FILE=$(basename "$LATEST_DB")
CONFIG_FILE=$(basename "$LATEST_CONFIG")

# Create temp directory
TEMP_DIR="/tmp/frappe-backup-$$"
mkdir -p "$TEMP_DIR"
trap "rm -rf '$TEMP_DIR'" EXIT
log_message "Created temporary directory: $TEMP_DIR"

# Copy files from container to host
log_message "Copying backups from container to host..."
docker cp "$CONTAINER_NAME:$LATEST_DB" "$TEMP_DIR/"
check_status "Database backup copy"

docker cp "$CONTAINER_NAME:$LATEST_CONFIG" "$TEMP_DIR/"
check_status "Config backup copy"

# Check if files exist and have content
if [ ! -s "$TEMP_DIR/$DB_FILE" ]; then
    log_message "ERROR: Database backup file is empty or doesn't exist"
    rm -rf "$TEMP_DIR"
    exit 1
fi

DB_SIZE=$(du -h "$TEMP_DIR/$DB_FILE" | cut -f1)
log_message "Database backup size: $DB_SIZE"

# Upload to S3
log_message "Uploading backups to S3..."
aws s3 cp "$TEMP_DIR/$DB_FILE" "$S3_BUCKET/$SITE_NAME/" --storage-class STANDARD_IA
check_status "Database upload to S3"

aws s3 cp "$TEMP_DIR/$CONFIG_FILE" "$S3_BUCKET/$SITE_NAME/" --storage-class STANDARD_IA
check_status "Config upload to S3"

# Verify upload
log_message "Verifying S3 upload..."
if aws s3 ls "$S3_BUCKET/$SITE_NAME/$DB_FILE" > /dev/null 2>&1; then
    log_message "✓ Verified: Database backup exists in S3"
else
    log_message "ERROR: Database backup verification failed"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Cleanup local temp files
log_message "Cleaning up temporary files..."
rm -rf "$TEMP_DIR"
check_status "Temporary files cleanup"

# Cleanup old backups in S3 ONLY (keep last KEEP_BACKUPS_S3)
log_message "========================================="
log_message "Cleaning up old backups in S3 (keeping last $KEEP_BACKUPS_S3)..."
log_message "Note: Container backups are managed by Frappe automatically"

# Count current backups in S3
S3_DB_COUNT=$(aws s3 ls "$S3_BUCKET/$SITE_NAME/" | grep "database.sql.gz" | wc -l)
log_message "Current database backups in S3: $S3_DB_COUNT"

if [ "$S3_DB_COUNT" -gt "$KEEP_BACKUPS_S3" ]; then
    REMOVE_COUNT=$((S3_DB_COUNT - KEEP_BACKUPS_S3))
    log_message "Removing $REMOVE_COUNT old database backup(s) from S3..."

    aws s3 ls "$S3_BUCKET/$SITE_NAME/" | grep "database.sql.gz" | sort -k1,2 | head -n $REMOVE_COUNT | awk '{print $4}' | while read file; do
        aws s3 rm "$S3_BUCKET/$SITE_NAME/$file"
        log_message "  - Removed: $file"
    done
    log_message "✓ Cleaned up old database backups from S3"
else
    log_message "✓ No old database backups to remove from S3 (current count: $S3_DB_COUNT)"
fi

# Cleanup old config files in S3
S3_CONFIG_COUNT=$(aws s3 ls "$S3_BUCKET/$SITE_NAME/" | grep "site_config_backup.json" | wc -l)
log_message "Current config backups in S3: $S3_CONFIG_COUNT"

if [ "$S3_CONFIG_COUNT" -gt "$KEEP_BACKUPS_S3" ]; then
    REMOVE_COUNT=$((S3_CONFIG_COUNT - KEEP_BACKUPS_S3))
    log_message "Removing $REMOVE_COUNT old config backup(s) from S3..."

    aws s3 ls "$S3_BUCKET/$SITE_NAME/" | grep "site_config_backup.json" | sort -k1,2 | head -n $REMOVE_COUNT | awk '{print $4}' | while read file; do
        aws s3 rm "$S3_BUCKET/$SITE_NAME/$file"
        log_message "  - Removed: $file"
    done
    log_message "✓ Cleaned up old config backups from S3"
else
    log_message "✓ No old config backups to remove from S3 (current count: $S3_CONFIG_COUNT)"
fi

# Get current backup counts
CONTAINER_BACKUP_COUNT=$(docker exec $CONTAINER_NAME bash -c "ls -1 $BACKUP_PATH/*database.sql.gz 2>/dev/null | wc -l")
S3_FINAL_DB_COUNT=$(aws s3 ls "$S3_BUCKET/$SITE_NAME/" | grep "database.sql.gz" | wc -l)
S3_FINAL_CONFIG_COUNT=$(aws s3 ls "$S3_BUCKET/$SITE_NAME/" | grep "site_config_backup.json" | wc -l)

# Summary
log_message "========================================="
log_message "Backup Summary:"
log_message "- Site: $SITE_NAME"
log_message "- Database backup: $DB_FILE ($DB_SIZE)"
log_message "- Config backup: $CONFIG_FILE"
log_message "- S3 Location: $S3_BUCKET/$SITE_NAME/"
log_message ""
log_message "Current Backup Counts:"
log_message "- Container: $CONTAINER_BACKUP_COUNT backups (managed by Frappe)"
log_message "- S3 Database: $S3_FINAL_DB_COUNT backups"
log_message "- S3 Config: $S3_FINAL_CONFIG_COUNT backups"
log_message "- S3 Retention Policy: Keep last $KEEP_BACKUPS_S3 backups"
log_message "========================================="
log_message "Backup completed successfully!"
log_message "========================================="

exit 0
