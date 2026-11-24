---
doc_id: doc_10_elk_bigdata_observability
title: Centralized Log Analytics & Distributed Telemetry Pipeline
domain: Big Data, Search & Observability Engineering
tech_stack: Elasticsearch, Logstash, Kibana, Hadoop, Spark, Kafka
link: https://www.hcltech.com/digital-analytics-services
---

## Project Overview
We built an enterprise observability and historical log-warehousing platform for a telecommunications client struggling with siloed server logs and slow incident root-cause triage.

## Technical Architecture
Application and network logs were ingested through Logstash pipelines and indexed into sharded Elasticsearch clusters for full-text search and alerting, while Kibana dashboards surfaced error spikes and SLA breakdowns for SRE teams. Cold archives and multi-month usage aggregations were processed in Hadoop and Apache Spark batch pipelines.

## Engineering Execution
Custom Grok parsing rules normalized heterogeneous microservice log formats and stripped sensitive PII fields prior to indexing. Index lifecycle management (ILM) automated hot-warm-cold tier rollover to balance query speed with storage costs.

## Outcomes Delivered
Engineering and security teams gained unified search across distributed microservices plus long-horizon batch analytics for capacity forecasting.
