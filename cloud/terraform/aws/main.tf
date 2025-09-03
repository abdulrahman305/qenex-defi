terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.0"
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region for deployment"
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  default     = "t3.large"
}

# VPC Configuration
resource "aws_vpc" "qenex_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "qenex-os-vpc"
    Project = "QENEX-OS"
  }
}

resource "aws_subnet" "qenex_public" {
  vpc_id                  = aws_vpc.qenex_vpc.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "${var.aws_region}a"

  tags = {
    Name = "qenex-os-public-subnet"
  }
}

resource "aws_internet_gateway" "qenex_igw" {
  vpc_id = aws_vpc.qenex_vpc.id

  tags = {
    Name = "qenex-os-igw"
  }
}

resource "aws_route_table" "qenex_public" {
  vpc_id = aws_vpc.qenex_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.qenex_igw.id
  }

  tags = {
    Name = "qenex-os-public-route"
  }
}

resource "aws_route_table_association" "qenex_public" {
  subnet_id      = aws_subnet.qenex_public.id
  route_table_id = aws_route_table.qenex_public.id
}

# Security Group
resource "aws_security_group" "qenex_sg" {
  name        = "qenex-os-sg"
  description = "Security group for QENEX OS"
  vpc_id      = aws_vpc.qenex_vpc.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "qenex-os-sg"
  }
}

# EC2 Instance
resource "aws_instance" "qenex_server" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  subnet_id     = aws_subnet.qenex_public.id
  security_groups = [aws_security_group.qenex_sg.id]

  user_data = <<-EOF
    #!/bin/bash
    curl -fsSL https://qenex.ai/install.sh | sudo bash
    systemctl start qenex-os
  EOF

  tags = {
    Name = "qenex-os-server"
    Project = "QENEX-OS"
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

# Load Balancer
resource "aws_lb" "qenex_lb" {
  name               = "qenex-os-lb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.qenex_sg.id]
  subnets           = [aws_subnet.qenex_public.id]

  tags = {
    Name = "qenex-os-lb"
  }
}

# Outputs
output "instance_public_ip" {
  value = aws_instance.qenex_server.public_ip
}

output "load_balancer_dns" {
  value = aws_lb.qenex_lb.dns_name
}