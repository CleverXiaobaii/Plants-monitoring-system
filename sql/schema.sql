CREATE TABLE IF NOT EXISTS rawdata_from_sensors (
    id SERIAL PRIMARY KEY,
    sensor_id INTEGER NOT NULL,
    time_stamp TIMESTAMP NOT NULL,
    temperature FLOAT NOT NULL,
    humidity FLOAT NOT NULL,
    soil_moisture FLOAT NOT NULL,
    is_anomaly BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS plants(
    id SERIAL PRIMARY KEY,
    plant_name VARCHAR(50) UNIQUE NOT NULL
);