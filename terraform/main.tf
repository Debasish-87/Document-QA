provider "aws" {
  region = "us-east-1"  # or your preferred region
}

resource "aws_s3_bucket" "pdf_bucket" {
  bucket = "documentqa-app-bucket"
  force_destroy = true
}

resource "aws_security_group" "docqa_sg" {
  name        = "docqa-sg"
  description = "Allow Flask port"
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
}

resource "aws_instance" "docqa_ec2" {
  ami                         = "ami-0c02fb55956c7d316"  # Ubuntu 22.04 in us-east-1
  instance_type               = "t2.medium"
  key_name                    = var.key_name
  vpc_security_group_ids      = [aws_security_group.docqa_sg.id]
  associate_public_ip_address = true

  user_data = file("ec2_user_data.sh")

  tags = {
    Name = "DocumentQA-EC2"
  }
}
