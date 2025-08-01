provider "aws" {
  region = "ap-south-1"
}

# Generate an SSH key pair for EC2
resource "tls_private_key" "ec2_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Create AWS Key Pair from the public key
resource "aws_key_pair" "generated_key" {
  key_name   = "docqa-key"
  public_key = tls_private_key.ec2_key.public_key_openssh
}


# Save private key locally
resource "local_file" "private_key_pem" {
  content              = tls_private_key.ec2_key.private_key_pem
  filename             = "${path.module}/docqa-key.pem"
  file_permission      = "0400"
  directory_permission = "0700"
}

# S3 bucket to store PDFs
resource "aws_s3_bucket" "pdf_bucket" {
  bucket        = "documentqa-app-bucket-debasish-unique"  # MUST be globally unique
  force_destroy = true
}

# Security group to allow traffic to Flask app on port 8000
resource "aws_security_group" "docqa_sg" {
  name        = "docqa-sg"
  description = "Allow inbound traffic for SSH and Flask app"

  ingress {
    description = "Flask App"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH Access"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # ⚠️ You can restrict this to your IP for better security
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}


# Launch EC2 instance
resource "aws_instance" "docqa_ec2" {
  ami                         = "ami-03bb6d83c60fc5f7c"  # ✅ Ubuntu 22.04 in ap-south-1 (Mumbai)
  instance_type               = "t2.medium"
  key_name                    = aws_key_pair.generated_key.key_name
  vpc_security_group_ids      = [aws_security_group.docqa_sg.id]
  associate_public_ip_address = true
  user_data                   = file("ec2_user_data.sh")

  tags = {
    Name = "DocumentQA-EC2"
  }

  depends_on = [aws_key_pair.generated_key]
}
