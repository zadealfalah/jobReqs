-- http://howto.philippkeller.com/2005/04/24/Tags-Database-schemas/
-- Above to justify creation of 3 tables below just to contain tags
-- Note that the 'Toxi' solution for tags (3 tables) is used by wordpress
-- above also gives examples of how to query it

-- https://stackoverflow.com/questions/10506181/tagging-system-toxi-solution-questions
-- above to see some examples of how to add to such a db

USE -- whatever db I end up making on AWS with terraform

CREATE TABLE IF NOT EXISTS jobs (
    id INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
    title VARCHAR (150) NOT NULL,
    company VARCHAR(150) NOT NULL,
    location VARCHAR(150),
    salary INT
)


CREATE TABLE IF NOT EXISTS tags (
    tag_id INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL
)

CREATE TABLE IF NOT EXISTS tagmap (
    id INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
    job_id INT NOT NULL,
    tag_id INT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES jobs.id ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags.tag_id ON DELETE CASCADE -- shouldn't be necesarry to delete tags, but just in case
)