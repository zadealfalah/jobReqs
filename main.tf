# https://dev.to/aws-builders/create-a-mysql-rds-database-instance-with-terraform-3oab
# https://aws.amazon.com/getting-started/hands-on/create-mysql-db/

# Set provider as aws
provider "aws" {
    region = "${var.region}"
    access_key = "${var.access_key}"
    secret_key = "${var.secret_key}"
}

# Create security group for RDS db instance
resource "aws_security_group" "rds_sg" {
    name = "rds_sg"
    ingress {
        from_port = 3306
        to_port = 3306
        protocol = "tcp"
        dicr_blocks = ["0.0.0.0/0"]
    }
    egress {
        from_port = 0
        to_port = 0
        protocol = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }
}

# Create the RDS DB instance itself
resource "aws_db_instance" "myinstance" {
    engine = "mysql"
    identifier = "myrdsinstance'
    allocated_storage = 20
    engine_version = "8.0"
    instance_class = "db.t2.micro"
    username = "myrdsuser"
    password = "myrdspassword"
    parameter_group_name = "default.mysql8.0"
    vpc_security_group_ids = ["${aws_security_group.rds_sg.id}"]
    skip_final_snapshot = true
    publicly_Accessible = true
}