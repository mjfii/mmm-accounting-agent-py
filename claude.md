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
  - `purchases/<<<YEAR>>>/` - Purchase journal entries
  - `sales/<<<YEAR>>>/` - Sale journal entries
  - `unrealized/<<<YEAR>>>/` - Mark-to-market journal entries (future)
- `scrapes/` - Extracted data files (non-journal entries)
  - `holdings/<<<YEAR>>>/` - Holdings/positions snapshots
  - `inc/<<<YEAR>>>/` - Dividends and interest income
  - `activity/<<<YEAR>>>/` - Securities bought and sold transactions
- `examples/` - Template files showing correct format

## Workflow

**When user says "process [month/date] statement"**, automatically extract holdings, income, and securities activity:

1. User specifies which statement PDF to process (e.g., "process March 2025 statement")
2. Extract data using AI/LLM-based PDF reading
3. Process **ALL** data types per the rules below:
   - **Holdings**: Generate `MMW-YYYY-MM-HLD.csv` per "Holdings Extraction Rules"
   - **Income**: Generate `MMW-YYYY-MM-INC.csv` per "Income Extraction Rules"
   - **Securities Activity**: Generate `MMW-YYYY-MM-SEC.csv` per "Securities Bought and Sold Extraction Rules"
4. Save holdings to `scrapes/holdings/<<<YEAR>>>/` directory
5. Save income to `scrapes/inc/<<<YEAR>>>/` directory
6. Save securities activity to `scrapes/activity/<<<YEAR>>>/` directory

## "Holdings" Extraction Rules

### Input
- Source: "Holdings" section of Fidelity PDF statement (typically pages 3-5)
- Extract: All positions including Mutual Funds, Exchange Traded Products (ETPs), Stocks, Other holdings, and money market funds (FDRXX, SPAXX, FCASH)

### Output Format
File: `scrapes/holdings/<<<YEAR>>>/MMW-YYYY-MM-HLD.csv`

**Columns:**
1. `symbol` - Stock/ETF ticker symbol extracted from description
2. `description` - Security name with symbol removed
3. `quantity` - Number of shares/units (3 decimal precision)
4. `price` - Price per unit (3 decimal precision)
5. `beginning_value` - Beginning market value (empty if "unavailable" in PDF)
6. `ending_value` - Ending market value (3 decimal precision)
7. `cost_basis` - Total cost basis (3 decimal precision)
8. `unrealized_gain` - Unrealized gain/loss (3 decimal precision)
9. `change_from_prior_period` - Calculated change (3 decimal precision)

### Processing Rules

**Symbol Extraction:**
- Extract ticker symbol from parentheses in description
- Example: "GLOBAL X FDS RUSSELL 2000 (RYLD)" → symbol="RYLD", description="GLOBAL X FDS RUSSELL 2000"

**Beginning Value Handling:**
- If PDF shows "unavailable": Leave field empty (null)
- If PDF shows numeric value: Use that value

**Change Calculation:**
- If `cost_basis` is empty or "not applicable": empty
- If `beginning_value` is empty: `change_from_prior_period = ending_value - cost_basis`
- If `beginning_value` exists: `change_from_prior_period = ending_value - beginning_value`

**Decimal Precision:**
- All numeric values: 3 decimal places
- Empty values: Leave blank (do not use "0" or "null" text)

### Example Output
```csv
symbol,description,quantity,price,beginning_value,ending_value,cost_basis,unrealized_gain,change_from_prior_period
RYLD,GLOBAL X FDS RUSSELL 2000,203.623,16.050,,3268.140,3399.990,-131.850,-131.850
VEGI,ISHARES INC MSCI AGRICULTURE,10.676,37.250,408.070,397.680,399.980,-2.300,-10.390
CWCO,CONSOLIDATED WATER CO LTD,19.186,27.070,502.280,519.360,499.990,19.370,17.080
```

## "Income" Extraction Rules

### Input
- Source: "Dividends, Interest & Other Income" section of Fidelity PDF statement (typically page 7)
- Extract: All dividend, interest, and reinvestment transactions including money market funds (FDRXX, SPAXX, FCASH)

### Output Format
File: `scrapes/inc/<<<YEAR>>>/MMW-YYYY-MM-INC.csv`

**Columns:**
1. `settlement_date` - Transaction settlement date (YYYY-MM-DD format)
2. `security_name` - Full security name from statement
3. `symbol` - Stock/ETF ticker symbol (matched from holdings)
4. `cusip` - CUSIP identifier
5. `description` - Transaction type (e.g., "Dividend Received", "Reinvestment")
6. `quantity` - Number of shares (3 decimal precision, empty if not applicable)
7. `price` - Price per share (3 decimal precision, empty if not applicable)
8. `amount` - Dollar amount (3 decimal precision)

### Processing Rules

**Date Format:**
- Convert settlement date from MM/DD format to YYYY-MM-DD
- Use statement year for year value

**Symbol Matching:**
- Match security names to ticker symbols from the Holdings section
- Common mappings:
  - FIDELITY GOVERNMENT CASH RESERVES → FDRXX
  - FIDELITY GOVERNMENT MONEY MARKET → SPAXX
  - GLOBAL X FDS RUSSELL 2000 → RYLD
  - GLOBAL X FDS S&P 500 COVERED → XYLD
  - GLOBAL X FDS NASDAQ 100 COVER → QYLD

**Quantity and Price:**
- Most dividend transactions have empty quantity and price
- Reinvestment transactions include quantity and price
- Empty values: Leave blank (do not use "0" or "null" text)

**Amount:**
- Use the amount from the PDF
- Reinvestments show negative amounts (money going back into fund)
- Regular dividends show positive amounts

**Decimal Precision:**
- All numeric values: 3 decimal places
- Empty values: Leave blank

### Example Output
```csv
settlement_date,security_name,symbol,cusip,description,quantity,price,amount
2025-03-03,GLOBAL X FDS NASDAQ 100 COVER,QYLD,37954Y483,Dividend Received,,,30.140
2025-03-28,NEOS ETF TRUST NEOS S&P 500 HI,SPYI,78433H303,Dividend Received,,,78.260
2025-03-31,FIDELITY GOVERNMENT CASH RESERVES,FDRXX,316067107,Reinvestment,18.140,1.000,-18.140
2025-03-31,FIDELITY GOVERNMENT CASH RESERVES,FDRXX,316067107,Dividend Received,,,18.140
```

## "Securities Bought and Sold" Extraction Rules

### Input
- Source: "Securities Bought and Sold" section of Fidelity PDF statement (typically page 6)
- Extract: All buy and sell transactions for stocks, ETFs, mutual funds, and other securities

### Output Format
File: `scrapes/activity/<<<YEAR>>>/MMW-YYYY-MM-SEC.csv`

**Columns:**
1. `settlement_date` - Transaction settlement date (YYYY-MM-DD format)
2. `action` - Transaction type (e.g., "You Bought", "You Sold")
3. `symbol` - Stock/ETF ticker symbol extracted from description
4. `security_name` - Full security name with symbol removed
5. `quantity` - Number of shares/units traded (3 decimal precision)
6. `price` - Price per unit (3 decimal precision)
7. `amount` - Total transaction value (3 decimal precision)
8. `transaction_cost` - Commission/fees charged (3 decimal precision, empty if none)

### Processing Rules

**Date Format:**
- Convert settlement date from MM/DD format to YYYY-MM-DD
- Use statement year for year value

**Symbol Extraction:**
- Extract ticker symbol from parentheses in description
- Example: "GLOBAL X FDS RUSSELL 2000 (RYLD)" → symbol="RYLD", security_name="GLOBAL X FDS RUSSELL 2000"

**Action Values:**
- Preserve exact action text from PDF (e.g., "You Bought", "You Sold")
- Do not abbreviate or modify the action description

**Decimal Precision:**
- All numeric values: 3 decimal places
- Empty values: Leave blank (do not use "0" or "null" text)

**Commission Handling:**
- If commission is $0.00 or not shown: Leave field empty
- If commission exists: Include the value with 3 decimal precision

### Example Output
```csv
settlement_date,action,symbol,security_name,quantity,price,amount,transaction_cost
2025-02-07,You Bought,MUST,COLUMBIA MULTI-SECTOR MUNICIPAL INCOME ETF,48.783,20.500,1000.000,
2025-02-07,You Bought,QYLD,GLOBAL X FDS NASDAQ 100 COVER,182.649,18.610,3399.990,
2025-02-07,You Bought,RYLD,GLOBAL X FDS RUSSELL 2000,203.623,16.700,3399.990,
2025-02-28,You Bought,APO,APOLLO GLOBAL MANAGEMENT INC,5.860,150.160,879.920,
2025-02-28,You Sold,VEGI,ISHARES INC MSCI AGRICULTURE,10.676,37.250,397.680,
```
