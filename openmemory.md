# WLJ Data Hub - OpenMemory Guide

## Overview
A data dictionary generation tool that extracts table structures from various databases (SQL Server, MySQL, PostgreSQL, Oracle) and generates documentation in multiple formats (Markdown, Excel, HTML, etc.).

## Architecture
- **Main Entry**: `generate_data_dictionary.py` handles the core logic of connecting to databases and extracting metadata.
- **Config Management**: `multi_db_support.py` provides support for multiple environments and complex configuration files.
- **Incremental Sync**: Supports tracking changes and only updating specific tables to reduce database load.

## User Defined Namespaces
- [Leave blank - user populates]

## Components
- **Database Engine**: SQLAlchemy-based connection management.
- **Metadata Extractors**: Specialized functions for each database type to fetch table and column comments.
- **Output Handlers**: Logic to format extracted data into Markdown, Excel, HTML, and CSV.

## Patterns
- **CLI Interface**: Uses `argparse` for flexible command-line operations.
- **Configuration**: Uses `configparser` with extensions for multi-environment support.
- **State Management**: Uses `example_incremental_state.json` to track sync progress.
