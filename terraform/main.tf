terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0.1"
    }
  }
}

provider "docker" {}

resource "docker_container" "library_app" {
  name  = "library-management-app"
  image = "final-project:latest"
  
  ports {
    internal = 5001
    external = 5001
  }
  
  start    = true
  must_run = true
}

output "app_url" {
  value       = "http://localhost:5001"
  description = "Library Management System URL"
}

output "container_name" {
  value = docker_container.library_app.name
}

output "view_logs_command" {
  value = "docker logs library-management-app"
}