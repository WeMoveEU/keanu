-- Loader run history: one row per batch execution (cycle) and one per
-- script attempt within it. Used to surface freshness and cycle duration
-- in dashboards.

CREATE TABLE IF NOT EXISTS loader_cycle (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_name VARCHAR(64) NOT NULL,
    started_at DATETIME NOT NULL,
    finished_at DATETIME NULL,
    status ENUM('running', 'success', 'failure') NOT NULL,
    INDEX loader_cycle_started_at (started_at)
);

CREATE TABLE IF NOT EXISTS loader_run (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    cycle_id BIGINT NOT NULL,
    script_name VARCHAR(255) NOT NULL,
    script_order INT NOT NULL,
    started_at DATETIME NOT NULL,
    finished_at DATETIME NULL,
    status ENUM('running', 'success', 'failure') NOT NULL,
    error_message TEXT NULL,
    INDEX loader_run_cycle_id (cycle_id),
    INDEX loader_run_script_started_at (script_name, started_at),
    CONSTRAINT loader_run_cycle_fk FOREIGN KEY (cycle_id) REFERENCES loader_cycle(id)
);
