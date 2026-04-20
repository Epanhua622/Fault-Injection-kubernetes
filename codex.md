# Kubernetes Fault Injection Experiment Guide

This project is a local Kubernetes autoscaling fault-injection testbed. It is designed for Docker Desktop Kubernetes, `metrics-server`, Locust load generation, and a Python experiment collector.

The current implementation focuses on Horizontal Pod Autoscaling (HPA). It does not directly corrupt Kubernetes metrics inside the metrics-server pipeline. Instead, it runs real HPA experiments with clean Kubernetes metrics and uses the Python collector to simulate faulty CPU and memory metrics in CSV output. This gives you experimental data without requiring a Prometheus Adapter or a custom Kubernetes external metrics API server.

## What This Project Measures

The main question is:

```text
How would autoscaling behavior change if Kubernetes made scaling decisions from faulty CPU or memory telemetry?
```

You can measure:

- CPU spike faults causing over-scaling.
- CPU drop faults causing under-scaling.
- Memory spike faults causing over-scaling.
- Memory drop faults causing under-scaling.
- Random faults causing unstable scaling estimates.
- Differences between real HPA behavior and simulated faulty HPA behavior.

## Important Autoscaling Terms

Horizontal scaling means changing the number of pods:

```text
1 pod -> 3 pods -> 6 pods
```

This is handled by HPA.

Vertical scaling means changing CPU and memory requests or limits for a pod:

```text
cpu request: 200m -> 500m
memory request: 256Mi -> 512Mi
```

This requires Vertical Pod Autoscaler (VPA), which is not installed or configured by this project yet.

## Current Architecture

```text
Locust load generator
        |
        v
TeaStore recommender deployment
        |
        v
metrics-server reports CPU and memory
        |
        +--> Kubernetes HPA scales pods from clean metrics
        |
        +--> Python collector simulates faulty metrics and writes CSV results
```

The Python collector does not currently feed `faulty_cpu` or `faulty_memory` back into Kubernetes HPA. That would require an external metrics adapter.

## Files That Matter

```text
k8s/teastore.yaml
```

Creates the `teastore` namespace, deploys the TeaStore recommender, and exposes it with a service named `teastore-recommender`.

```text
k8s/recommender-hpa.yaml
```

Creates the default CPU-based HPA. It targets 60% CPU utilization. Because the pod CPU request is `200m`, the approximate target average CPU is:

```text
200m * 0.60 = 120m
```

```text
k8s/recommender-hpa-memory.yaml
```

Alternative memory-based HPA. Use this instead of the CPU HPA when testing memory-based horizontal scaling. Do not run both HPA manifests against the same deployment at the same time.

```text
fault-injection/metric_fault_injector.py
```

Collects real pod CPU and memory from `kubectl top pods`, injects synthetic faults, estimates desired replica counts, and writes CSV rows.

```text
load/locustfile.py
```

Generates load against the TeaStore web path.

```text
scripts/run_experiment.sh
```

Applies the TeaStore deployment and default CPU HPA, waits briefly, then prints pod and HPA state.

## Setup

Start Docker Desktop and enable Kubernetes.

Verify the cluster:

```sh
kubectl get nodes
```

Install Python dependencies:

```sh
pip install -r requirements.txt
```

Install metrics-server if it is not already installed:

```sh
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

Patch metrics-server for Docker Desktop:

```sh
kubectl patch deployment metrics-server \
  -n kube-system \
  --type='json' \
  -p='[
  {"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"},
  {"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-preferred-address-types=InternalIP"}
  ]'
```

Restart metrics-server:

```sh
kubectl rollout restart deployment metrics-server -n kube-system
```

Verify metrics:

```sh
kubectl top pods -n kube-system
```

## Deploy The Workload

Deploy TeaStore and the default CPU HPA:

```sh
./scripts/run_experiment.sh
```

Or manually:

```sh
kubectl apply -f k8s/teastore.yaml
kubectl apply -f k8s/recommender-hpa.yaml
```

Check the objects:

```sh
kubectl get pods -n teastore
kubectl get service -n teastore
kubectl get hpa -n teastore
```

Forward the TeaStore recommender service to your laptop:

```sh
kubectl port-forward -n teastore service/teastore-recommender 8080:8080
```

## Generate Load

In another terminal:

```sh
cd load
locust
```

Open:

```text
http://localhost:8089
```

Use this Locust host:

```text
http://localhost:8080
```

For repeatable experiments, use the same user count, spawn rate, and duration for every scenario.

## Collect Fault-Injection Data

The collector supports these scenarios:

```text
baseline
cpu-spike
cpu-drop
memory-spike
memory-drop
random
```

Run a baseline:

```sh
python fault-injection/metric_fault_injector.py collect \
  --scenario baseline \
  --duration 600 \
  --interval 15 \
  --output results/baseline.csv
```

Run a CPU spike experiment:

```sh
python fault-injection/metric_fault_injector.py collect \
  --scenario cpu-spike \
  --duration 600 \
  --interval 15 \
  --output results/cpu-spike.csv
```

Run a CPU drop experiment:

```sh
python fault-injection/metric_fault_injector.py collect \
  --scenario cpu-drop \
  --duration 600 \
  --interval 15 \
  --output results/cpu-drop.csv
```

Run a memory spike experiment:

```sh
python fault-injection/metric_fault_injector.py collect \
  --scenario memory-spike \
  --duration 600 \
  --interval 15 \
  --output results/memory-spike.csv
```

Run a memory drop experiment:

```sh
python fault-injection/metric_fault_injector.py collect \
  --scenario memory-drop \
  --duration 600 \
  --interval 15 \
  --output results/memory-drop.csv
```

Run random faults:

```sh
python fault-injection/metric_fault_injector.py collect \
  --scenario random \
  --fault-rate 0.2 \
  --duration 600 \
  --interval 15 \
  --output results/random.csv
```

The default CPU target is `120m`, matching the CPU HPA target of 60% of a `200m` request. The default memory target is `256Mi`.

## CSV Columns

Each CSV row includes:

```text
timestamp
scenario
fault_type
pod_count
current_replicas
real_cpu_m
faulty_cpu_m
real_memory_mi
faulty_memory_mi
desired_replicas_cpu_clean
desired_replicas_cpu_faulty
desired_replicas_memory_clean
desired_replicas_memory_faulty
```

The most important comparisons are:

```text
desired_replicas_cpu_clean vs desired_replicas_cpu_faulty
desired_replicas_memory_clean vs desired_replicas_memory_faulty
current_replicas vs desired_replicas_cpu_faulty
current_replicas vs desired_replicas_memory_faulty
```

If the faulty desired replica count is higher than the clean desired replica count, the fault would cause over-scaling.

If the faulty desired replica count is lower than the clean desired replica count, the fault would cause under-scaling.

## CPU HPA Experiment

Use:

```sh
kubectl apply -f k8s/recommender-hpa.yaml
```

Watch HPA:

```sh
kubectl get hpa -n teastore -w
```

Watch pods:

```sh
kubectl get pods -n teastore -w
```

Collect data at the same time:

```sh
python fault-injection/metric_fault_injector.py collect \
  --scenario cpu-spike \
  --duration 600 \
  --interval 15 \
  --output results/cpu-hpa-spike.csv
```

Expected result:

```text
CPU spike faults should produce desired_replicas_cpu_faulty values higher than desired_replicas_cpu_clean.
```

Interpretation:

```text
If HPA had consumed the faulty CPU metric, it would have over-scaled.
```

## Memory HPA Experiment

Remove the existing HPA first:

```sh
kubectl delete hpa recommender-hpa -n teastore
```

Apply the memory HPA:

```sh
kubectl apply -f k8s/recommender-hpa-memory.yaml
```

Collect memory fault data:

```sh
python fault-injection/metric_fault_injector.py collect \
  --scenario memory-spike \
  --duration 600 \
  --interval 15 \
  --output results/memory-hpa-spike.csv
```

Expected result:

```text
Memory spike faults should produce desired_replicas_memory_faulty values higher than desired_replicas_memory_clean.
```

Interpretation:

```text
If HPA had consumed the faulty memory metric, it would have over-scaled.
```

## Suggested Experiment Matrix

Run each scenario with the same Locust configuration:

```text
baseline
cpu-spike
cpu-drop
memory-spike
memory-drop
random
```

For each run, record:

```text
Locust user count
Locust spawn rate
duration
HPA type: CPU or memory
minimum replicas
maximum replicas
target CPU or memory
CSV output file
```

## Useful Result Metrics

Over-scaling amount:

```text
desired_replicas_faulty - desired_replicas_clean
```

Under-scaling amount:

```text
desired_replicas_clean - desired_replicas_faulty
```

Fault impact duration:

```text
number of CSV rows where desired_replicas_faulty != desired_replicas_clean
```

Replica instability:

```text
number of times desired_replicas_faulty changes between consecutive rows
```

Maximum over-scaling:

```text
max(desired_replicas_faulty - desired_replicas_clean)
```

Maximum under-scaling:

```text
max(desired_replicas_clean - desired_replicas_faulty)
```

## What To Put In The Report

A strong report can use these sections:

```text
1. Objective
2. Kubernetes setup
3. Workload and autoscaling configuration
4. Fault model
5. Experiment matrix
6. Results
7. Analysis
8. Limitations
9. Future work
```

Important limitations to state clearly:

```text
Faults are simulated after metrics collection.
Faulty metrics are not injected into the live Kubernetes HPA control loop.
The current project studies HPA, not full VPA.
Docker Desktop Kubernetes is a local test environment, not a production cluster.
```

Important future work:

```text
Add Prometheus and Prometheus Adapter.
Expose faulty_cpu and faulty_memory as real external metrics.
Configure HPA to consume those external metrics directly.
Install VPA and compare HPA vs VPA under faulty metrics.
Add graph generation scripts for CSV outputs.
```

