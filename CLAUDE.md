# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a research-and-discovery project aimed at building a **test coverage observability dashboard** for a large-scale CI system (Mozilla Firefox / Taskcluster). The project starts as research and will evolve into an implementation.

### Problem Statement

A team responsible for CI infrastructure images (cloud VMs and dedicated hardware) needs visibility into **where test suites run across OS pools** so they can:

1. Safely "green up" new OS pools (e.g., adding Windows 11) by understanding which skipped tests still have coverage elsewhere.
2. Identify tests that have been **skipped on all platforms** — a hidden coverage gap, especially dangerous when retiring older OS pools.
3. Avoid losing test coverage silently when decommissioning an OS (e.g., dropping Windows 10 without realizing some tests only ran there).

### Key Domain Concepts

- **Pools**: Tagged groups of machines (cloud or hardware) identified by OS version, purpose, and type (e.g., `1-11-24h2-t` = Windows 11 24H2 tester). Pools bucket machines by config: performance, networking (IPv4/IPv6), GUI-based, etc.
- **Greening up**: The process of bringing a new OS pool from alpha to production by iteratively running test suites, skipping failures, filing bugs, and repeating until achieving a full green run with acceptable skip rates.
- **Tiers**: Test priority levels. Tier 1 tests must pass in Autoland before code reaches central (main). Tier 2/3 have lower enforcement.
- **Autoland / Central**: Autoland is the pre-merge branch; code must pass CI there before auto-promoting to central (main). Nightly builds come from central.
- **Try builds**: On-demand CI runs pointed at specific pools, used during greening up.
- **Decision task**: An automated system that analyzes a PR and determines which test suites need to run based on what changed.
- **Sheriffs**: Human operators who monitor Autoland, remove broken PRs from the queue, and perform tree closures (branch freezes tied to release trains).
- **Flaky vs Intermittent**: Flaky = fails first run, passes on immediate retry. Intermittent = randomly fails with no clear pattern.
- **Skipped tests**: Tests disabled on a pool, often with a Bugzilla bug filed. Acceptable when coverage exists on another pool for the same OS family; risky when the covering pool is later decommissioned.

### Data Sources

- **Firefox mono-repo** (GitHub, open source): contains all test suites and test definitions
- **Taskcluster** (open source): CI orchestration, pool definitions, task scheduling
- **Grafana / Prometheus**: internal dashboards with metrics on machine utilization, queue times, test flakiness
- **Bugzilla**: bug tracking for skipped/failing tests
- **wiki.mozilla.org / searchfox**: documentation and code search

### Scale

- 30,000+ distinct tests
- ~130,000 task runs/month
- 24-hour queue timeout; 12-hour queue = problem threshold
- Mixed fleet: cloud VMs (quota-limited per region) + dedicated hardware (performance devices, phones, special configs)

## Project Approach

This project is **iterative and exploratory** — the user has explicitly stated "I don't know what I don't know." Start with high-level discovery, surface what's available, and let findings drive the next step. Avoid over-engineering early; the shape of the dashboard will emerge from the data.

## Key Files

- `history/` — Session recaps and findings
- `coverage_map.json` / `skip_matrix.json` — Parsed data outputs
