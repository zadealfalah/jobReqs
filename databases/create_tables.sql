-- Create jobs table
CREATE TABLE jobs (
    job_key VARCHAR(255) PRIMARY KEY,
    job_location VARCHAR(255),
    salary_min DECIMAL(10, 2),
    salary_max DECIMAL(10, 2),
    salary_type VARCHAR(50),
    salary_estimated_flag INT,
    company VARCHAR(255),
    job_title VARCHAR(255),
    job_date
    url VARCHAR(1000),
);

-- Create keywords table
CREATE TABLE keywords (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_key VARCHAR(255),
    keyword VARCHAR(255),
    FOREIGN KEY (job_key) REFERENCES jobs(job_key)
);

-- Create tech table
CREATE TABLE tech (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_key VARCHAR(255),
    technology VARCHAR(255),
    FOREIGN KEY (job_key) REFERENCES jobs(job_key)
);