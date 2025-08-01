output "ec2_public_ip" {
  value = aws_instance.docqa_ec2.public_ip
}

output "s3_bucket_name" {
  value = aws_s3_bucket.pdf_bucket.id
}

output "private_key_path" {
  value = local_file.private_key_pem.filename
}
