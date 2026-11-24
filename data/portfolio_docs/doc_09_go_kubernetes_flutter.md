---
doc_id: doc_09_go_kubernetes_flutter
title: Cloud-Native Logistics Dispatch Backend & Flutter Mobile Client
domain: Go Microservices, Kubernetes & Cross-Platform Apps
tech_stack: Go, Golang, Kubernetes, Flutter, Dart, gRPC, Helm
link: https://www.wipro.com/digital/
---

## Project Overview
Guruji-AI architected a high-concurrency dispatch platform and courier mobile companion for a last-mile delivery operator scaling across multiple metropolitan hubs.

## Technical Architecture
Low-latency routing and telemetry ingestion microservices were written in Go (Golang) with gRPC internal communication and deployed on managed Kubernetes clusters using Helm charts and horizontal pod autoscaling. Couriers used a single-codebase Flutter (Dart) mobile application receiving live route assignments and turn-by-turn status updates.

## Engineering Execution
Graceful shutdown hooks, liveness/readiness probes, and structured Prometheus metrics ensured zero dropped dispatch events during rolling Kubernetes upgrades. In Flutter, clean bloc state management kept map rendering smooth on mid-range Android devices.

## Outcomes Delivered
Platform teams achieved predictable container orchestration at scale alongside a unified iOS and Android courier application shipped from one engineering team.
