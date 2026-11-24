---
doc_id: doc_08_dotnet_azure_cloud
title: Cloud-Native Healthcare Claims Processing on Microsoft Azure
domain: .NET Enterprise & Azure Cloud Modernization
tech_stack: C#, ASP.NET Core, SQL Server, Azure, Entity Framework, Azure DevOps
link: https://www.capgemini.com/solutions/digital-services/
---

## Project Overview
We migrated an on-premises claims adjudication platform to Microsoft Azure for an insurance administration provider seeking elastic scaling, automated CI/CD, and modernized API integrations.

## Technical Architecture
Core APIs were refactored from legacy .NET Framework into cross-platform ASP.NET Core services utilizing Entity Framework Core and Azure SQL Server. Azure Service Bus decoupled document ingestion from downstream verification rules, while Azure Key Vault and Managed Identities secured database credentials and third-party tokens.

## Engineering Execution
Infrastructure-as-code templates provisioned repeatable staging and production environments. Automated Azure DevOps pipelines executed static analysis, unit/integration suites, and zero-downtime slot deployments.

## Outcomes Delivered
The client eliminated manual server patching windows and gained cloud-native elasticity for peak open-enrollment processing cycles.
