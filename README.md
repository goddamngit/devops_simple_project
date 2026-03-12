# Automated Web Infrastructure with Monitoring (DevOps Project)

This repository contains a full-cycle DevOps project: a Flask-based web application with PostgreSQL and Redis, fully automated using Ansible and GitHub Actions, and monitored with Prometheus/Grafana.

## 🚀 Project Overview

The project demonstrates a production-ready infrastructure distributed across three virtual machines (or nodes):

1.  **Gateway Node (.52)**: Runs Nginx Reverse Proxy, PostgreSQL, and Redis.
    
2.  **Application Node (.51)**: Hosts the Python Flask application.
    
3.  **Monitoring Node (.50)**: Centralized monitoring with Prometheus and Grafana.
    

## 🛠 Tech Stack

-   **App**: Python 3.11, Flask, Redis, PostgreSQL.
    
-   **Infrastructure**: Docker & Docker Compose.
    
-   **CI/CD**: GitHub Actions.
    
-   **Automation**: Ansible (Roles, Vault, Inventory).
    
-   **Monitoring**: Prometheus, Grafana, Node Exporter.
    

## 🏗 System Architecture

The infrastructure is designed for isolation and scalability:

-   **Reverse Proxy**: Nginx handles incoming traffic for `site.local` and `monitoring.local`.
    
-   **Data Layer**: PostgreSQL stores user credentials and access logs; Redis tracks site visit counters.
    
-   **Monitoring**: Every node runs a `node-exporter` container. Prometheus scrapes metrics from all nodes, and Grafana visualizes them via pre-provisioned dashboards.
    

## ⚙️ Setup & Deployment

### Prerequisites

-   Ansible installed on your local machine.
    
-   Three Linux VMs (Ubuntu recommended) with SSH access.
    
-   Docker Hub account.
    

### 1. Secrets Configuration

Encrypt your sensitive data using Ansible Vault:

```
ansible-vault create ansible/group_vars/all/vault.yml

```

Required variables:

-   `vault_db_pass`: PostgreSQL password.
    
-   `vault_secret_key`: Flask session key.
    
-   `vault_docker_password`: Docker Hub token.
    

### 2. Inventory

Update `ansible/inventory.ini` with your server IP addresses.

### 3. Deployment

Run the main playbook:

```
ansible-playbook ansible/site.yml

```

## 📊 Monitoring

-   **Prometheus**: Access at `http://<monitoring_ip>:9090`
    
-   **Grafana**: Access at `http://monitoring.local` (default credentials managed via Vault).
    

## 📝 Features

-   **User Authentication**: Register and Login functionality.
    
-   **Access Logs**: Stores login history with IP address tracking.
    
-   **High Availability**: Containers are set to `restart: always`.
    
-   **Automated Metrics**: Application metrics exported via `prometheus-flask-exporter`.