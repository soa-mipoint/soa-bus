-- MiPoint: initialize databases for each service
-- Runs automatically on first postgres container start

CREATE DATABASE customers_db;
CREATE DATABASE catalog_db;
CREATE DATABASE bookings_db;
CREATE DATABASE notifications_db;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE customers_db TO mipoint;
GRANT ALL PRIVILEGES ON DATABASE catalog_db TO mipoint;
GRANT ALL PRIVILEGES ON DATABASE bookings_db TO mipoint;
GRANT ALL PRIVILEGES ON DATABASE notifications_db TO mipoint;
