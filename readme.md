# Kubernetes Autoscaling Fault Injection Testbed

This project evaluates the **resilience of Kubernetes Horizontal Pod
Autoscaling (HPA)** when the telemetry used for scaling decisions
becomes **faulty or corrupted**.

The system deploys a microservice, collects CPU metrics, injects faults
into those metrics, and observes how Kubernetes autoscaling reacts.

The project runs **locally on a laptop using Docker Desktop's Kubernetes
cluster**.

------------------------------------------------------------------------

# Architecture Diagram

``` mermaid
flowchart TD
    A[Locust Load Generator] --> B[TeaStore Recommender Pod]
    B --> C[Metrics Server]
    C --> D[Fault Injector]
    D --> E[Horizontal Pod Autoscaler]
    E --> F[Replica Scaling Decision]
```

Explanation:

-   **Locust** generates load
-   **TeaStore** processes requests
-   **metrics-server** collects CPU usage
-   **Fault injector** modifies metrics
-   **HPA** makes scaling decisions
-   The system may scale **incorrectly if metrics are faulty**

------------------------------------------------------------------------

# Fault Injection Pipeline

``` mermaid
flowchart LR
    A[Real CPU Metric] --> B[Fault Injector]
    B --> C{Fault Type}
    C -->|Spike| D[CPU x3]
    C -->|Drop| E[CPU x0.3]
    C -->|None| F[Original CPU]
    D --> G[Modified Metric]
    E --> G
    F --> G
    G --> H[HPA Scaling Decision]
```

Fault models implemented:

  Fault Type   Behavior
  ------------ ---------------------------
  spike        artificially increase CPU
  drop         artificially decrease CPU
  none         no modification

------------------------------------------------------------------------

# Requirements

Install the following tools.

## Docker Desktop

Install Docker Desktop and enable Kubernetes.

Docker Desktop → Settings → Kubernetes → **Enable Kubernetes**

Verify:

    kubectl get nodes

Expected:

    docker-desktop   Ready

------------------------------------------------------------------------

## kubectl

Install kubectl:

    brew install kubectl

Verify:

    kubectl version --client

------------------------------------------------------------------------

## Python

Install Python:

    brew install python

Install required packages:

    pip install flask kubernetes locust

------------------------------------------------------------------------

# Project Structure

    project/

    k8s/
      teastore.yaml
      recommender-hpa.yaml
      fault-injector.yaml
      fault-metric-service.yaml

    load/
      locustfile.py

    fault-injection/
      metric_fault_injector.py

    README.md

------------------------------------------------------------------------

# Start Kubernetes

Start Docker Desktop and wait for Kubernetes to initialize.

Verify cluster:

    kubectl get nodes

------------------------------------------------------------------------

# Install Metrics Server

Install the Kubernetes metrics server.

    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

------------------------------------------------------------------------

# Patch Metrics Server (Required for Docker Desktop)

Docker Desktop Kubernetes cannot scrape metrics without this patch.

    kubectl patch deployment metrics-server \
    -n kube-system \
    --type='json' \
    -p='[
    {"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"},
    {"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-preferred-address-types=InternalIP"}
    ]'

Restart metrics server:

    kubectl rollout restart deployment metrics-server -n kube-system

Verify metrics:

    kubectl top pods -n kube-system

------------------------------------------------------------------------

# Deploy TeaStore Service

    kubectl apply -f k8s/teastore.yaml

Verify:

    kubectl get pods -n teastore

------------------------------------------------------------------------

# Deploy Autoscaler

    kubectl apply -f k8s/recommender-hpa.yaml

Check autoscaler:

    kubectl get hpa -n teastore

Example:

    NAME              TARGETS   MINPODS   MAXPODS   REPLICAS
    recommender-hpa   45%/60%   1         10        1

------------------------------------------------------------------------

# Start Fault Injector

Run:

    python fault-injection/metric_fault_injector.py

Endpoint:

    http://localhost:5001/metric

Example output:

    {
      "real_cpu": 120,
      "faulty_cpu": 360
    }

------------------------------------------------------------------------

# Generate Load

Start Locust:

    cd load
    locust

Open:

    http://localhost:8089

Configuration example:

    Host: http://localhost:30080
    Users: 50
    Spawn rate: 5

------------------------------------------------------------------------

# Observe Autoscaling

Watch autoscaler:

    kubectl get hpa -n teastore -w

Watch pods:

    kubectl get pods -n teastore -w

------------------------------------------------------------------------

# Fault Injection Experiments

### False Spike

    Real CPU = 20%
    Injected CPU = 80%

Result:

    Unnecessary scale-up

------------------------------------------------------------------------

### False Drop

    Real CPU = 90%
    Injected CPU = 10%

Result:

    Missed scaling

------------------------------------------------------------------------

### Noisy Telemetry

Random fluctuations in metrics may cause:

-   scaling oscillations
-   unstable replica counts

------------------------------------------------------------------------

# Metrics to Record

During experiments record:

-   scaling latency
-   number of replicas
-   oscillation frequency
-   incorrect scaling events
-   CPU utilization

Example:

  Fault Rate   Wrong Scaling
  ------------ --------------------
  0%           baseline
  10%          minor instability
  20%          noticeable errors
  40%          severe oscillation

------------------------------------------------------------------------

# Reset System

    kubectl delete -f k8s/

Restart Kubernetes if necessary from Docker Desktop.

------------------------------------------------------------------------

# Summary

This project demonstrates how **faulty telemetry can influence
Kubernetes autoscaling decisions**.

By injecting controlled faults into resource metrics, researchers can
study the resilience of cloud orchestration systems under unreliable
monitoring data.
