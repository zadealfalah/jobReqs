## Just use the default vpc/subnets for my db for now.
# resource "aws_vpc" "scraper-vpc" {
#     cidr_block = "10.123.0.0/16"

#     tags = {
#         Name   = "dev"
#     }
# }

# resource "aws_subnet" "scraper-public-subnet" {
#     vpc_id     = aws_vpc.scraper-vpc.id
#     cidr_block = "10.123.1.0/24"
#     map_public_ip_on_launch = true
#     availability_zone = "us-east-1a"

#     tags = {
#         Name = "dev-public"
#     }
# }



# Store mysql database in main for now as we won't have many resources for a bit
# Can split into other tf files and reference from main once I get more

resource "aws_db_instance" "scrape-db" {
    allocated_storage    = 10
    db_name              = "scrapeindeed"
    engine               = "mysql"
    engine_version       = "8.0.35"
    instance_class       = "db.t3.micro"
    username             = var.db_username
    password             = var.db_password
    parameter_group_name = "default.mysql8.0"
    skip_final_snapshot  = true
}