-- MiPoint: initialize databases for each service
-- Runs automatically on first postgres container start

CREATE DATABASE customers_db;
CREATE DATABASE catalog_db;
CREATE DATABASE bookings_db;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE customers_db TO mipoint;
GRANT ALL PRIVILEGES ON DATABASE catalog_db TO mipoint;
GRANT ALL PRIVILEGES ON DATABASE bookings_db TO mipoint;
