FROM mysql:8.0

# Copy the initialization SQL script into the database entrypoint folder
COPY database.sql /docker-entrypoint-initdb.d/database.sql
