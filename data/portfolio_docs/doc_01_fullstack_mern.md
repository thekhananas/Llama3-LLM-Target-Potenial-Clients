---
doc_id: doc_01_fullstack_mern
title: Real-Time B2B Marketplace & Order Management Platform
domain: Full-Stack JavaScript / MERN Engineering
tech_stack: React, Node.js, Express, MongoDB, TypeScript, WebSockets
link: https://www.toptal.com/portfolio
---

## Project Overview
Guruji-AI Pvt. Ltd. partnered with a mid-market wholesale distributor to modernize a legacy spreadsheet-driven procurement workflow into a responsive single-page web application supporting live inventory updates and multi-vendor checkout.

## Technical Architecture
The frontend was engineered in React with TypeScript, modular component libraries, and optimistic UI state synchronization. On the backend, Node.js and Express REST services were paired with WebSocket event streams for instant order-status propagation. MongoDB replica sets stored flexible catalog schemas and order audit histories with compound indexing for sub-second filtering.

## Engineering Execution
To eliminate race conditions during concurrent bulk orders, our team implemented atomic MongoDB transactions and idempotency keys across checkout endpoints. Role-based access control (JWT) and automated schema validation ensured strict separation between supplier and buyer tenants.

## Outcomes Delivered
The platform unified product discovery, quote approvals, and fulfillment tracking into one browser portal, replacing fragmented manual email threads and enabling automated partner onboarding.
