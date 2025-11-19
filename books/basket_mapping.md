# Fidelity Basket ID to Account Code Mapping

This document maps Fidelity's internal basket identifiers (as shown on brokerage statements) to the corresponding account codes in the chart of accounts.

## Confirmed Mappings

Based on analysis of actual Fidelity statements:

| Fidelity Basket ID | Basket Name | Account Code | Securities | Confirmed Date |
|-------------------|-------------|--------------|------------|----------------|
| **BASKET:10001** | Water Stocks Basket | 1102-001 | ALCO, AWK, CWCO, CWT, ECL, FERG, FPI, GWRS, LAND, VEGI, WAT, XYL | October 2024 |
| **BASKET:10003** | Buy Write ETFs | 1102-002 | JEPI, QYLD, RYLD, SPYI, TLTW, XYLD, MUST | February 2025 |
| **BASKET:10005** | Holding Companies | 1102-003 | APO, BRKB, BX, KKR, L, TPG | February 2025 |
| **BASKET:10007** | Balanced ETFs | 1102-004 | FDEM, FDEV, FELC, FESM, FMDE, ONEQ | User Confirmed |

## How to Identify Basket IDs

When reviewing Fidelity brokerage statements:

1. Look in the **"Securities Bought & Sold"** section
2. Find the **Description** column
3. Basket purchases will show: `BASKET:##### where ##### is the 5-digit basket identifier

## Usage

When processing purchase transactions:
- Extract the basket ID from the Fidelity statement Description field
- Use this mapping to determine the correct basket name and account code
- Group all securities purchased under the same basket ID and settlement date into a single journal entry

## Last Updated

2025-11-19: **Complete mapping of all 4 baskets confirmed:**
- BASKET:10001 (Water Stocks) - found in October 2024 statement
- BASKET:10003 (Buy Write ETFs) - found in February 2025 statement
- BASKET:10005 (Holding Companies) - found in February 2025 statement
- BASKET:10007 (Balanced ETFs) - user confirmed
