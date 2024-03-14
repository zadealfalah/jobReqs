# Just use the default vpc/subnets for my db for now.
resource "aws_vpc" "scraper-vpc" {
    cidr_block = "10.123.0.0/16"

    tags = {
        Name   = "dev"
    }
}

resource "aws_subnet" "scraper-public-subnet" {
    vpc_id     = aws_vpc.scraper-vpc.id
    cidr_block = "10.123.1.0/24"
    map_public_ip_on_launch = true
    availability_zone = "us-east-1a"

    tags = {
        Name = "dev-public"
    }
}