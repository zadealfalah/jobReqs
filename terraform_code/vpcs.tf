resource "aws_vpc" "glue_vpc" {
    cidr_block = "172.30.0.0/16"
}

resource "aws_vpc" "mysql_vpc" {
    cidr_block = "172.32.0.0/16"
}



# resource "aws_vpc_peering_connection" "glue_to_mysql_peering" {
#     vpc_id = aws_vpc.glue_vpc.id
#     peer_vpc_id = aws_vpc.mysql_vpc.id

#     accepter {
#       allow_remote_vpc_dns_resolution = true
#     }
#     requester {
#       allow_remote_vpc_dns_resolution = true
#     }
# }



# resource "aws_vpc_endpoint" "s3" {
#   vpc_id = aws_vpc.glue_vpc.id
#   service_name = "com.amazonaws.us-east-1.s3"
# }


# ## Double check that s3 endpoint properly present in route table for AWS glue VPC
# resource "aws_route_table" "glue_route_table" {
#   vpc_id = aws_vpc.glue_vpc.id
#   route {
#     cidr_block = aws_vpc.mysql_vpc.cidr_block
#     vpc_peering_connection_id = aws_vpc_peering_connection.glue_to_mysql_peering.id
#   }
# }

# resource "aws_route_table" "mysql_route_table" {
#     vpc_id = aws_vpc.mysql_vpc.id
#     route {
#         cidr_block = aws_vpc.glue_vpc.cidr_block
#         vpc_peering_connection_id = aws_vpc_peering_connection.glue_to_mysql_peering.id
#     }
  
# }