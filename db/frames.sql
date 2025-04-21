CREATE EXTENSION q3c;

-- Sequence metadata
-- TODO: unique constraints on something to avoid duplication?..
DROP TABLE IF EXISTS sequences CASCADE;
CREATE TABLE sequences (
       id SERIAL PRIMARY KEY,
       site TEXT,
       observer TEXT,
       filter TEXT,
       object TEXT,
       keywords JSONB
);

CREATE INDEX ON sequences(site);
CREATE INDEX ON sequences(observer);
CREATE INDEX ON sequences(filter);
CREATE INDEX ON sequences(object);

-- Frame metadata
-- TODO: unique constraints on something to avoid duplication?..
DROP TABLE IF EXISTS frames CASCADE;
CREATE TABLE frames (
       id SERIAL PRIMARY KEY,
       sequence INT,
       time TIMESTAMP,
       filter TEXT,
       exposure FLOAT,
       ra FLOAT,
       dec FLOAT,
       radius FLOAT,
       pixscale FLOAT,
       width INT,
       height INT,
       footprint POLYGON,
       keywords JSONB
);

CREATE INDEX ON frames(time);
CREATE INDEX ON frames(filter);

CREATE INDEX ON frames (q3c_ang2ipix(ra, dec));

-- Photometry measurements
DROP TABLE IF EXISTS photometry CASCADE;
CREATE TABLE photometry (
       id SERIAL PRIMARY KEY,
       sequence INT,
       frame INT,
       time TIMESTAMP,
       filter TEXT,
       ra FLOAT,
       dec FLOAT,
       -- x, y, exposure, ... ?
       mag FLOAT,
       magerr FLOAT,
       color_term FLOAT DEFAULT 0,
       color_term2 FLOAT DEFAULT 0,
       flags INT,
       fwhm FLOAT
);

CREATE INDEX ON photometry (q3c_ang2ipix(ra, dec));
