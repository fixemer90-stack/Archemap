#!/bin/bash
# Yandex Cloud setup script for Astrotype
# Prerequisites: yc CLI installed and authenticated

set -euo pipefail

# Configuration
CLUSTER_NAME="astrotype"
NETWORK_NAME="astrotype-network"
SUBNET_NAME="astrotype-subnet"
REGISTRY_NAME="astrotype"
ZONE="ru-central1-a"
NODE_COUNT=2
NODE_CPU=4
NODE_MEMORY=8
NODE_DISK=64

echo "=== Yandex Cloud Setup for Astrotype ==="

# 1. Create network
echo "Creating network..."
yc vpc network create \
  --name "$CLUSTER_NAME" \
  --description "Astrotype K8s network" 2>/dev/null || echo "Network already exists"

# 2. Create subnet
echo "Creating subnet..."
yc vpc subnet create \
  --name "$SUBNET_NAME" \
  --network-name "$CLUSTER_NAME" \
  --zone "$ZONE" \
  --range "10.0.0.0/24" \
  --description "Astrotype K8s subnet" 2>/dev/null || echo "Subnet already exists"

# 3. Create container registry
echo "Creating container registry..."
yc container registry create \
  --name "$REGISTRY_NAME" \
  --description "Astrotype container registry" 2>/dev/null || echo "Registry already exists"

REGISTRY_ID=$(yc container registry get "$REGISTRY_NAME" --format json | jq -r '.id')
echo "Registry ID: $REGISTRY_ID"

# 4. Create service account for CI
echo "Creating service account..."
yc iam service-account create \
  --name "astrotype-ci" \
  --description "CI/CD service account" 2>/dev/null || echo "Service account already exists"

SA_ID=$(yc iam service-account get "astrotype-ci" --format json | jq -r '.id')
echo "Service Account ID: $SA_ID"

# 5. Grant roles to service account
echo "Granting roles..."
yc resource-manager folder add-access-binding \
  --role "container-registry.images.pusher" \
  --service-account-id "$SA_ID" 2>/dev/null || true

yc resource-manager folder add-access-binding \
  --role "container-registry.images.puller" \
  --service-account-id "$SA_ID" 2>/dev/null || true

yc resource-manager folder add-access-binding \
  --role "k8s.cluster-api.cluster-admin" \
  --service-account-id "$SA_ID" 2>/dev/null || true

# 6. Create static key for CI
echo "Creating static key..."
yc iam access-key create \
  --service-account-id "$SA_ID" \
  --description "CI/CD static key" 2>/dev/null || echo "Key already exists"

# 7. Create Kubernetes cluster
echo "Creating Kubernetes cluster..."
yc managed-kubernetes cluster create \
  --name "$CLUSTER_NAME" \
  --network-name "$CLUSTER_NAME" \
  --subnet-name "$SUBNET_NAME" \
  --zone "$ZONE" \
  --service-account-id "$SA_ID" \
  --node-service-account-id "$SA_ID" \
  --description "Astrotype K8s cluster" 2>/dev/null || echo "Cluster already exists"

# 8. Create node group
echo "Creating node group..."
yc managed-kubernetes node-group create \
  --cluster-name "$CLUSTER_NAME" \
  --name "default" \
  --fixed-size "$NODE_COUNT" \
  --platform "standard-v3" \
  --cores "$NODE_CPU" \
  --memory "$NODE_MEMORY" \
  --disk "$NODE_DISK" \
  --network-interface subnet-name="$SUBNET_NAME",ipv4-address=nat 2>/dev/null || echo "Node group already exists"

# 9. Get kubeconfig
echo "Getting kubeconfig..."
yc managed-kubernetes cluster get-credentials \
  --name "$CLUSTER_NAME" \
  --external 2>/dev/null || echo "Kubeconfig already exists"

# 10. Create namespaces
echo "Creating namespaces..."
kubectl create namespace astrotype-staging 2>/dev/null || echo "Namespace staging already exists"
kubectl create namespace astrotype-prod 2>/dev/null || echo "Namespace prod already exists"

# 11. Install NGINX Ingress Controller
echo "Installing NGINX Ingress..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.0/deploy/static/provider/cloud/deploy.yaml 2>/dev/null || echo "Ingress already installed"

# 12. Install cert-manager
echo "Installing cert-manager..."
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.yaml 2>/dev/null || echo "cert-manager already installed"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Update secrets in infra/k8s/base/secrets.yaml"
echo "2. Build and push images to cr.yandex/$REGISTRY_ID/"
echo "3. Deploy: kubectl apply -k infra/k8s/overlays/staging/"
echo ""
echo "Registry ID: $REGISTRY_ID"
echo "Service Account ID: $SA_ID"
