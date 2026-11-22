-- ==============================================================================
-- Source Binary: /System/Library/PrivateFrameworks/TextInputCore.framework/TextInputCore
-- Source File on Disk: System/Library/PrivateFrameworks/TextInputCore.framework/rejections_database_schema.sql
-- Storage Path on Device: ~/Library/Keyboard/rejections.sqlite
-- Engine: SQLite3 (Compiled with WAL mode, page_size=4096, journal_mode=WAL)
-- Classification: [VERBATIM EMPIRICAL SCHEMA / RUNTIME QUERY RECONSTRUCTION]
-- ==============================================================================

-- Core Autocorrection Rejections Ledger
CREATE TABLE IF NOT EXISTS rejections (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    typed                        TEXT, -- originally typed by the user
    correction                   TEXT, -- autocorrection performed or rejected
    performed_count              INTEGER DEFAULT 0, -- hard acceptances
    soft_rejections              INTEGER DEFAULT 0, -- dismissed via candidate bar tap
    hard_rejections              INTEGER DEFAULT 0, -- backspaced immediately after insertion
    -- timestamps: seconds since unix epoch
    last_soft_rejection          REAL DEFAULT -1e10,
    last_hard_rejection          REAL DEFAULT -1e10,

    journaled
);

CREATE UNIQUE INDEX IF NOT EXISTS intended_rejected_idx ON rejections(typed, correction);

-- Apple Intelligence Inline Predictive Completion Rejections Ledger
CREATE TABLE IF NOT EXISTS inline_completion_rejections (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    typed                        TEXT, -- originally typed by the user
    correction                   TEXT, -- inline completion suggested or rejected
    performed_count              INTEGER DEFAULT 0, -- accepted via space / tab / swipe
    soft_rejections              INTEGER DEFAULT 0, -- ignored by continuing to type alternative chars
    hard_rejections              INTEGER DEFAULT 0, -- accepted then immediately backspaced
    -- timestamps: seconds since unix epoch
    last_soft_rejection          REAL DEFAULT -1e10,
    last_hard_rejection          REAL DEFAULT -1e10,

    journaled
);

CREATE UNIQUE INDEX IF NOT EXISTS inline_completion_intended_rejected_idx ON inline_completion_rejections(typed, correction);

-- ------------------------------------------------------------------------------
-- Reconstructed Runtime Queries Executed by TextInputCore
-- ------------------------------------------------------------------------------

-- Query 1: Evaluate Rejection Penalty for Candidate Promotion
-- Executed inside -[FavoniusCandQualityFilter computeCandidateScoreForSurface:...]
-- Parameters: :typed, :correction
/*
SELECT 
    performed_count,
    soft_rejections,
    hard_rejections,
    last_soft_rejection,
    last_hard_rejection
FROM rejections
WHERE typed = :typed AND correction = :correction;
*/

-- Query 2: Record Soft Rejection (User tapped identity candidate in bar)
/*
INSERT INTO rejections (typed, correction, soft_rejections, last_soft_rejection)
VALUES (:typed, :correction, 1, strftime('%s', 'now'))
ON CONFLICT(typed, correction) DO UPDATE SET
    soft_rejections = soft_rejections + 1,
    last_soft_rejection = strftime('%s', 'now');
*/

-- Query 3: Record Hard Rejection (User pressed backspace immediately after space triggered correction)
/*
INSERT INTO rejections (typed, correction, hard_rejections, last_hard_rejection)
VALUES (:typed, :correction, 1, strftime('%s', 'now'))
ON CONFLICT(typed, correction) DO UPDATE SET
    hard_rejections = hard_rejections + 1,
    last_hard_rejection = strftime('%s', 'now');
*/

-- Query 4: Record Acceptance (User accepted autocorrection without reversal)
/*
INSERT INTO rejections (typed, correction, performed_count)
VALUES (:typed, :correction, 1)
ON CONFLICT(typed, correction) DO UPDATE SET
    performed_count = performed_count + 1;
*/
