CREATE TABLE IF NOT EXISTS sponsors (
    id         SERIAL PRIMARY KEY,
    email      TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scans (
    id            SERIAL PRIMARY KEY,
    attendee_id   TEXT NOT NULL,
    sponsor_email TEXT NOT NULL REFERENCES sponsors(email),
    scanned_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes         TEXT
);

CREATE INDEX IF NOT EXISTS scans_attendee_id_idx ON scans(attendee_id);
CREATE INDEX IF NOT EXISTS scans_sponsor_email_idx ON scans(sponsor_email);
