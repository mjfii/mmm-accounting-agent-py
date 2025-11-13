
# Bookkeeping and Accounting Calculations and Integrations

## Purpose
To convert monthly Fidelity brokerage statements (PDF) into viable accounting journal entries for import
into the accounting system.

## Directory Structure
- `statements/<<<YEAR>>>/` - Source PDF statements to be processed
- `books/` - Reference files (chart of accounts and GL transactions) - **READ ONLY**
  - `chart_of_accounts.csv` - Account master list
  - `gl_entries.csv` - Historical general ledger entries
- `entries/` - Generated journal entry files by transaction type
  - `dividends/<<<YEAR>>>/` - Dividend journal entries
  - `purchases/<<<YEAR>>>/` - Purchase transaction entries (future)
  - `sales/<<<YEAR>>>/` - Sale transaction entries (future)
  - `unrealized/<<<YEAR>>>/` - Mark-to-market entries (future)
- `examples/` - Template files showing correct format

## Workflow
1. User specifies which statement PDF to process
2. Extract dividend transactions using AI/LLM-based PDF reading
3. Process dividends per "Dividend Processing Rules" below
4. Generate CSV file in the format: `MMW-YYYY-MM-DIV.csv`
5. Save to appropriate `entries/dividends/<<<YEAR>>>/` directory

## Current Processing Steps
1. Process Dividends per "Dividend Processing Rules"
2. Process Purchases per "Purchase Processing Rules"
3. Future: Process sales and unrealized gains/losses

## Dividend Processing Rules
Define the standardized process for recording dividend activity in GL transaction format based 
on brokerage statement data. For each **dividend payment date**, create a journal entry consisting of:

### 1. Cash Lines
- One debit line **per symbol** receiving a dividend on that date.
- Debit Account: **Cash - Fidelity Cash Management Account**
- Debit Amount: Dividend amount for that specific symbol.

### 2. Income Line
- One aggregated credit line for all dividends paid on that date.
- Credit Account: **Income - Ordinary Dividend**
- Credit Amount: Sum of all dividends for that date.

## File Naming Convention
- Format: `MMW-YYYY-MM-DIV.csv`
- Example: `MMW-2025-01-DIV.csv` for January 2025 dividends
- Suffix `-DIV` indicates dividend transactions
- One file per month containing all dividend entries for that month

## Journal Numbering
- **Journal Number Prefix**: `MMW-` (constant)
- **Journal Number Suffix**: Sequential number starting at 1 for each file
  - Resets to 1 for each new month/file
  - Increments for each unique payment date
  - API will assign new numbers upon import, so local numbers are temporary
- **Reference Number**: Format `DIV-YYYY-MM-DD` using the dividend payment date

## CSV File Structure
Required columns (in order):
1. Journal Date - Payment date in YYYY-MM-DD format
2. Reference Number - Format: DIV-YYYY-MM-DD
3. Journal Number Prefix - Always "MMW-"
4. Journal Number Suffix - Sequential: 1, 2, 3, etc.
5. Notes - Description format (must be quoted to handle commas):
   - **Same for all lines in a transaction** (both debits and credits)
   - Format: `"YYYY-MM-DD Dividends - [SYMBOL1, SYMBOL2, ...]"`
   - Example: `"2025-01-31 Dividends - CWCO, FDRXX, SPAXX, LAND, GWRS"`
6. Journal Type - Always "both"
7. Currency - Always "USD"
8. Account - Account name from chart of accounts
9. Description - Transaction detail format (must be quoted):
   - For debit lines: `"Dividend - [SYMBOL]"` (one line per symbol, e.g., `"Dividend - FDRXX"`)
   - For credit lines: `"Income - [SYMBOL1, SYMBOL2, ...]"` (e.g., `"Income - CWCO, FDRXX, SPAXX, LAND, GWRS"`)
10. Contact Name - Leave empty
11. Debit - Debit amount or empty
12. Credit - Credit amount or empty
13. Project Name - Leave empty
14. Status - Always "published"
15. Exchange Rate - Leave empty

## Processing Rules
- Dates must be recorded in **YYYY-MM-DD** format.
- No empty rows may appear in the CSV file.
- Do **not** combine dividends from different dates into the same journal entry.
- Maintain exact payment dates as shown on the brokerage statement.
- Money market funds (e.g., SPAXX, FDRXX) receive the same treatment—record dividend income only.
  No valuation entries are required.
- Each journal entry must balance (total debits = total credits).
- **Quote both the Notes and Description fields** to properly handle comma-separated symbol lists in CSV format.

## Excluded Fields
The following fields must **not** be included in dividend journal entries:
- Exemption Code
- Item Tax Exemption Reason
- Tax Authority
- Tax Name
- Tax Percentage
- Tax Type

## Example: Single Date with Multiple Dividends

For dividends paid on 2025-01-31:
- CWCO: $2.11
- FDRXX: $4.62
- SPAXX: $0.01
- LAND: $2.60
- GWRS: $0.19
- **Total: $9.53**

**Journal Entry:**
```
Journal Date: 2025-01-31
Reference: DIV-2025-01-31
Journal Number: MMW-4
Notes (for ALL lines): "2025-01-31 Dividends - CWCO, FDRXX, SPAXX, LAND, GWRS"

Debit  - Cash - Fidelity Cash Management Account - "Dividend - CWCO"  - $2.11
Debit  - Cash - Fidelity Cash Management Account - "Dividend - FDRXX" - $4.62
Debit  - Cash - Fidelity Cash Management Account - "Dividend - SPAXX" - $0.01
Debit  - Cash - Fidelity Cash Management Account - "Dividend - LAND"  - $2.60
Debit  - Cash - Fidelity Cash Management Account - "Dividend - GWRS"  - $0.19
Credit - Income - Ordinary Dividend - "Income - CWCO, FDRXX, SPAXX, LAND, GWRS" - $9.53
```

## Example Files and Templates
- Reference template: `examples/MMW-2025-02-DIV.csv`
- Output location: `entries/dividends/<<<YEAR>>>/MMW-YYYY-MM-DIV.csv`
- Example output: `entries/dividends/2025/MMW-2025-01-DIV.csv`

## Data Sources
When processing dividend information from Fidelity statements:
1. Look for "Dividends, Interest & Other Income" section in the Activity pages
2. Extract: Settlement Date, Security Name, Symbol/CUSIP, and Amount
3. Group all dividends by Settlement Date
4. Ignore reinvestment transactions (they are already reflected in the dividend amount)

## Account Names
All account names in the CSV must exactly match the account names in `books/chart_of_accounts.csv`:
- **Cash account**: `Cash - Fidelity Cash Management Account` (Account Code: 1001-001)
- **Income account**: `Income - Ordinary Dividend` (Account Code: 4001-001)

## CSV Formatting Best Practices
- **Always quote fields containing commas**: Both Notes and Description fields contain comma-separated symbol lists and must be quoted
- **Consistent quoting**: While only fields with commas require quotes, quoting all text fields ensures consistency
- **No empty rows**: The CSV must end immediately after the last transaction line
- **Line endings**: Standard CSV line endings (LF or CRLF)
- **Encoding**: UTF-8

## Quality Checks
Before finalizing a dividend CSV file, verify:
1. **Totals match statement**: Sum of all dividend amounts equals the total dividend income shown on the Fidelity statement
2. **All dates present**: Every dividend payment date from the statement is represented
3. **Balanced entries**: For each journal entry (same Journal Number Suffix), total debits equal total credits
4. **Symbol accuracy**: Ticker symbols match exactly as shown on the statement
5. **Sequential numbering**: Journal Number Suffix increments sequentially (1, 2, 3, ...)
6. **Proper quoting**: All Notes and Description fields are properly quoted

## Common Patterns
- **Single dividend per date**: One debit line + one credit line (e.g., 2025-01-08 with FPI only)
- **Multiple dividends per date**: Multiple debit lines (one per symbol) + one aggregated credit line (e.g., 2025-01-31 with 5 symbols)
- **Money market dividends**: SPAXX and FDRXX are treated identically to stock dividends—record income only, no special treatment
- **Date format consistency**: Always use YYYY-MM-DD (e.g., 2025-01-31, not 01/31/2025)

## Purchase Processing Rules
Define the standardized process for recording security purchase activity in GL transaction format based
on brokerage statement data. Purchases are organized by **basket** and **settlement date**.

### Investment Baskets
Securities are organized into thematic baskets (see `books/baskets.md`):
- **Water Stocks Basket (1102-001)**: ALCO, AWK, CWCO, CWT, ECL, FERG, FPI, GWRS, LAND, VEGI, WAT, XYL
- **Buy-Write ETFs (1102-002)**: JEPI, QYLD, RYLD, SPYI, TLTW, XYLD, MUST
- **Holding Companies (1102-003)**: APO, BRKB, BX, KKR, L, TPG
- **Balanced ETFs (1102-004)**: FDEM, FDEV, FELC, FESM, FMDE, ONEQ

### Basket Identification
Fidelity statements include basket notations in the purchase description:
- Example: "BASKET:10003" typically corresponds to Buy-Write ETFs (1102-002)
- Example: "BASKET:10005" typically corresponds to Holding Companies (1102-003)

### Journal Entry Structure
For each **basket** on each **settlement date**, create one journal entry:

1. **Cash Line (Credit)**
   - One credit line for the total purchase amount across all securities in that basket
   - Credit Account: **Cash - Fidelity Cash Management Account**
   - Credit Amount: Sum of all purchase amounts for that basket on that date

2. **Investment Lines (Debit)**
   - One debit line **per ticker** purchased in that basket on that date
   - Debit Account: The specific ticker account from the chart of accounts
     - Example: `JPMorgan Equity Premium Income ETF (JEPI)` (Account Code: 1102-002-001)
   - Debit Amount: Total purchase amount for that ticker (combining fractional and whole shares)

### Fractional and Multiple Purchase Prices
When a security has multiple purchase lines at different prices (fractional + whole shares):
- **Combine all quantities and amounts** into a single journal entry line
- Example: QYLD purchased as 0.649 shares @ $18.62 ($12.08) + 182.000 shares @ $18.61490 ($3,387.91)
- Result: One debit line for QYLD totaling $3,399.99

### File Naming Convention
- Format: `MMW-YYYY-MM-PUR.csv`
- Example: `MMW-2025-02-PUR.csv` for February 2025 purchases
- Suffix `-PUR` indicates purchase transactions
- One file per month containing all purchase entries for that month

### Journal Numbering for Purchases
- **Journal Number Prefix**: `MMW-` (constant)
- **Journal Number Suffix**: Sequential number starting at 1 for each file
  - Resets to 1 for each new month/file
  - Increments for each basket purchase on each settlement date
  - API will assign new numbers upon import, so local numbers are temporary
- **Reference Number**: Format `PUR-YYYY-MM-DD-BASKETID`
  - Example: `PUR-2025-02-07-10003` for basket 10003 purchases on 02/07/2025

### CSV File Structure
Identical to dividend CSV structure (same 15 columns in same order):
1. Journal Date - Settlement date in YYYY-MM-DD format
2. Reference Number - Format: PUR-YYYY-MM-DD-BASKETID
3. Journal Number Prefix - Always "MMW-"
4. Journal Number Suffix - Sequential: 1, 2, 3, etc.
5. Notes - Description format (must be quoted):
   - **Same for all lines in a transaction**
   - Format: `"YYYY-MM-DD Purchase - [BASKET NAME] - [SYMBOL1, SYMBOL2, ...]"`
   - Example: `"2025-02-07 Purchase - Buy-Write ETFs - JEPI, QYLD, RYLD, SPYI, TLTW, XYLD, MUST"`
6. Journal Type - Always "both"
7. Currency - Always "USD"
8. Account - Account name from chart of accounts (exact match required)
9. Description - Transaction detail format (must be quoted):
   - For debit lines: `"Purchase - [SYMBOL]"` (e.g., `"Purchase - JEPI"`)
   - For credit line: `"Cash for [BASKET NAME] - [SYMBOL1, SYMBOL2, ...]"` (e.g., `"Cash for Buy-Write ETFs - JEPI, QYLD, RYLD, SPYI, TLTW, XYLD, MUST"`)
10. Contact Name - Leave empty
11. Debit - Debit amount or empty
12. Credit - Credit amount or empty
13. Project Name - Leave empty
14. Status - Always "published"
15. Exchange Rate - Leave empty

### Purchase Processing Rules
- Dates must be recorded in **YYYY-MM-DD** format (use settlement date, not trade date)
- No empty rows may appear in the CSV file
- **Ignore money market fund transactions** (FDRXX, SPAXX) - these are cash management, not investments
- **Ignore "REDEEMED TO COVER A SETTLED OBLIGATION"** transactions - these are netted automatically
- Combine purchases with different prices for the same ticker on the same date into one line
- Each journal entry must balance (total debits = total credits)
- **Quote both the Notes and Description fields** to properly handle comma-separated symbol lists
- Group by basket AND settlement date - do not mix different baskets or dates in the same entry

### Example: Single Basket Purchase on One Date

**Statement Data (02/07/2025 - BASKET:10003):**
- MUST: 0.783 @ $20.43 ($16.00) + 48.000 @ $20.49990 ($984.00) = **$1,000.00**
- QYLD: 0.649 @ $18.62 ($12.08) + 182.000 @ $18.61490 ($3,387.91) = **$3,399.99**
- RYLD: 0.623 @ $16.69990 ($10.40) + 203.000 @ $16.69750 ($3,389.59) = **$3,399.99**
- XYLD: 0.691 @ $42.56500 ($29.41) + 51.000 @ $42.56010 ($2,170.57) = **$2,199.98**
- TLTW: 0.407 @ $23.62000 ($9.61) + 25.000 @ $23.61500 ($590.38) = **$599.99**
- JEPI: 0.744 @ $58.96200 ($43.87) + 23.000 @ $58.96200 ($1,356.13) = **$1,400.00**
- SPYI: 0.514 @ $51.77350 ($26.61) + 154.000 @ $51.77500 ($7,973.35) = **$7,999.96**
- **Total: $19,999.91**

**Journal Entry:**
```
Journal Date: 2025-02-07
Reference: PUR-2025-02-07-10003
Journal Number: MMW-1
Notes (for ALL lines): "2025-02-07 Purchase - Buy-Write ETFs - MUST, QYLD, RYLD, XYLD, TLTW, JEPI, SPYI"

Debit  - Columbia Multi-Sector Municipal Income ETF (MUST)    - "Purchase - MUST" - $1,000.00
Debit  - Global X NASDAQ 100 Covered Call ETF (QYLD)          - "Purchase - QYLD" - $3,399.99
Debit  - Global X Russell 2000 Covered Call ETF (RYLD)        - "Purchase - RYLD" - $3,399.99
Debit  - Global X S&P 500 Covered Call ETF (XYLD)             - "Purchase - XYLD" - $2,199.98
Debit  - iShares 20+ Year Treasury Bond ETF (TLTW)            - "Purchase - TLTW" - $599.99
Debit  - JPMorgan Equity Premium Income ETF (JEPI)            - "Purchase - JEPI" - $1,400.00
Debit  - Neos S&P 500 High Income ETF (SPYI)                  - "Purchase - SPYI" - $7,999.96
Credit - Cash - Fidelity Cash Management Account              - "Cash for Buy-Write ETFs - MUST, QYLD, RYLD, XYLD, TLTW, JEPI, SPYI" - $19,999.91
```

### Example Files and Templates
- Output location: `entries/purchases/<<<YEAR>>>/MMW-YYYY-MM-PUR.csv`
- Example output: `entries/purchases/2025/MMW-2025-02-PUR.csv`

### Data Sources
When processing purchase information from Fidelity statements:
1. Look for "Securities Bought & Sold" section in the Activity pages
2. Extract: Settlement Date, Security Name, Symbol/CUSIP, Description (for basket ID), Quantity, Price, and Amount
3. Group all purchases by Basket ID and Settlement Date
4. Ignore "You Sold" transactions (money market redemptions)
5. Combine multiple price points for the same security on the same date

### Account Names for Purchases
All account names in the CSV must exactly match the account names in `books/chart_of_accounts.csv`:
- **Cash account**: `Cash - Fidelity Cash Management Account` (Account Code: 1001-001)
- **Investment accounts**: Use the full account name from the chart of accounts
  - Example: `JPMorgan Equity Premium Income ETF (JEPI)` (Account Code: 1102-002-001)
  - Example: `Berkshire Hathaway Inc. Class B (BRKB)` (Account Code: 1102-003-002)

### Quality Checks for Purchases
Before finalizing a purchase CSV file, verify:
1. **Totals match statement**: Sum of all purchase amounts equals the total securities bought shown on the statement
2. **All baskets present**: Every basket purchase from the statement is represented
3. **Balanced entries**: For each journal entry (same Journal Number Suffix), total debits equal total credits
4. **Symbol accuracy**: Ticker symbols match exactly as shown on the statement and chart of accounts
5. **Sequential numbering**: Journal Number Suffix increments sequentially (1, 2, 3, ...)
6. **Proper quoting**: All Notes and Description fields are properly quoted
7. **No money market funds**: FDRXX, SPAXX, and similar money market funds should not appear in purchase entries
8. **Correct account names**: All account names exactly match the chart of accounts

### Common Patterns
- **Single basket, single date**: Multiple debit lines (one per ticker) + one credit line
- **Multiple baskets in one month**: Separate journal entries for each basket/date combination
- **Fractional shares**: Always combine with whole shares for the same ticker on the same date
- **Date format consistency**: Always use YYYY-MM-DD for settlement date (not trade date)

## Future Development Notes
- Python code will automate the PDF extraction and CSV generation process
- API integration will handle the import and reassign journal numbers
- The system is designed to scale to other transaction types (purchases, sales, unrealized gains)
- Journal numbers are temporary and reset each month; the accounting system assigns permanent numbers on import
