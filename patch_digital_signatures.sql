CREATE TABLE digital_signature (
    id VARCHAR(36) NOT NULL,
    work_order_id INTEGER NOT NULL,
    signer_name VARCHAR(100) NOT NULL,
    signer_title VARCHAR(100),
    signed_at DATETIME,
    document_hash VARCHAR(64) NOT NULL,
    status VARCHAR(20),
    pdf_path VARCHAR(255),
    PRIMARY KEY (id),
    FOREIGN KEY(work_order_id) REFERENCES work_order (id)
);
