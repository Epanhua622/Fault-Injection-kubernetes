#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
METRICS_SERVER_URL="https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml"
HPA_MODE="${1:-webui}"

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$1"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

wait_for_rollout() {
  local namespace="$1"
  local resource="$2"
  local timeout="${3:-180s}"

  kubectl rollout status "$resource" -n "$namespace" --timeout="$timeout"
}

wait_for_metrics_api() {
  local attempts=30
  local sleep_seconds=5
  local i

  for ((i = 1; i <= attempts; i++)); do
    if kubectl top nodes >/dev/null 2>&1; then
      return 0
    fi
    log "Waiting for Metrics API to become available ($i/$attempts)..."
    sleep "$sleep_seconds"
  done

  echo "Metrics API did not become available. Check metrics-server and kube-system pods." >&2
  kubectl get apiservice v1beta1.metrics.k8s.io || true
  kubectl get pods -n kube-system || true
  exit 1
}

wait_for_teastore_pods() {
  local attempts=60
  local sleep_seconds=5
  local i

  for ((i = 1; i <= attempts; i++)); do
    if kubectl get pods -n teastore --no-headers 2>/dev/null | awk '{print $2" "$3}' | grep -qvE '^1/1 Running$|^2/2 Running$'; then
      log "Waiting for TeaStore pods to become ready ($i/$attempts)..."
      sleep "$sleep_seconds"
      continue
    fi

    if kubectl get pods -n teastore --no-headers 2>/dev/null | grep -q .; then
      return 0
    fi
  done

  echo "TeaStore pods did not become ready in time." >&2
  kubectl get pods -n teastore || true
  exit 1
}

apply_default_hpa() {
  case "$HPA_MODE" in
    webui)
      kubectl apply -f "$ROOT_DIR/k8s/webui-hpa.yaml"
      ;;
    recommender)
      kubectl apply -f "$ROOT_DIR/k8s/recommender-hpa.yaml"
      ;;
    none)
      log "Skipping HPA installation because mode is 'none'."
      return 0
      ;;
    *)
      echo "Unknown HPA mode: $HPA_MODE" >&2
      echo "Usage: $0 [webui|recommender|none]" >&2
      exit 1
      ;;
  esac
}

require_cmd kubectl

log "Checking cluster connectivity..."
kubectl get nodes

log "Installing metrics-server from upstream manifest..."
kubectl apply -f "$METRICS_SERVER_URL"

log "Patching metrics-server for Docker Desktop..."
kubectl patch deployment metrics-server -n kube-system --patch-file "$ROOT_DIR/k8s/metrics-server-patch.yaml"

log "Restarting metrics-server..."
kubectl rollout restart deployment metrics-server -n kube-system

log "Waiting for metrics-server rollout..."
wait_for_rollout kube-system deployment/metrics-server 180s

log "Waiting for Metrics API..."
wait_for_metrics_api

log "Deploying TeaStore stack..."
kubectl apply -f "$ROOT_DIR/k8s/teastore.yaml"

log "Applying default HPA mode: $HPA_MODE"
apply_default_hpa

log "Waiting for TeaStore pods..."
wait_for_teastore_pods

log "Current TeaStore state:"
kubectl get pods -n teastore
kubectl get service -n teastore
kubectl get hpa -n teastore || true

log "Bootstrap complete."
