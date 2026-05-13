terraform {
  required_version = ">= 1.0"
}

resource "null_resource" "docker_deploy" {
  provisioner "local-exec" {
    command = <<-EOT
      docker rm -f library-management-app 2>$null
      docker run -d -p 5001:5001 --name library-management-app final-project:latest
      echo "Container created successfully!"
    EOT
  }
  
  provisioner "local-exec" {
    when    = destroy
    command = "docker rm -f library-management-app"
  }
}

output "app_url" {
  value       = "http://localhost:5001"
  description = "Application URL"
}

output "view_logs_command" {
  value       = "docker logs library-management-app"
  description = "Command to view logs"
}