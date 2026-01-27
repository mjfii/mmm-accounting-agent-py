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
  - `income/<<<YEAR>>>/` - Dividends and interest income
  - `activity/<<<YEAR>>>/` - Securities bought and sold transactions
  - `summary/<<<YEAR>>>/` - Account summary snapshots
- `examples/` - Template files showing correct format
  - `scrapes/` - Example extracted data files (HLD, INC, ACT, SUM)
  - `entries/` - Example journal entry files (DIV, PUR, SAL, UNR)

## Workflow

**When user says "process [month/date] statement"**, automatically extract holdings, income, securities activity, and account summary:

1. User specifies which statement PDF to process (e.g., "process March 2025 statement")
2. Extract data using AI/LLM-based PDF reading
3. Process **ALL** data types per the rules below:
   - **Holdings**: Generate `MMW-YYYY-MM-HLD.csv` per "Holdings Extraction Rules"
   - **Income**: Generate `MMW-YYYY-MM-INC.csv` per "Income Extraction Rules"
   - **Securities Activity**: Generate `MMW-YYYY-MM-ACT.csv` per "Securities Bought and Sold Extraction Rules"
   - **Account Summary**: Generate `MMW-YYYY-MM-SUM.csv` per "Account Summary Extraction Rules"
4. Save holdings to `scrapes/holdings/<<<YEAR>>>/` directory
5. Save income to `scrapes/income/<<<YEAR>>>/` directory
6. Save securities activity to `scrapes/activity/<<<YEAR>>>/` directory
7. Save account summary to `scrapes/summary/<<<YEAR>>>/` directory
8. Update `src/main.py` to set the correct year and month
9. Run `python src/main.py` to generate journal entries

## Basket Configuration

Securities are grouped into baskets for portfolio tracking:

| Basket ID | Name | Securities |
|-----------|------|------------|
| 10001 | Water Investments | AWK, CWT, CWCO, GWRS, XYL, VEGI |
| 10003 | Buy Write ETFs | QYLD, RYLD, XYLD, JEPI, SPYI, TLTW, MUST |
| 10005 | Holding Companies | APO, BX, KKR, TPG, BRKB, L |

Additional securities not in baskets: ALCO, ECL, FERG, WAT, FPI, LAND, FDRXX, SPAXX

## Journal Entry Suffix Ranges

Journal entries use the following suffix ranges by type:

| Entry Type | Suffix Range | Example |
|------------|--------------|---------|
| Dividends (DIV) | 10001+ | MMW-10001 |
| Purchases (PUR) | 20001+ | MMW-20001 |
| Sales (SAL) | 30001+ | MMW-30001 |
| Unrealized (UNR) | 40001+ | MMW-40001 |

## Validation Formula

The statement validation checks that extracted data reconciles:

**For months WITHOUT securities activity (purchases/sales):**
```
Change in Investment Value = Income + Holdings Change
```

**For months WITH securities activity:**
```
Change in Investment Value = Income + Holdings Change - Purchases + Sales
```

Where:
- **Income**: Sum of all dividend amounts from income file
- **Holdings Change**: Sum of (ending_value - beginning_value) for all positions
- **Purchases**: Sum of all "You Bought" transaction amounts from activity file
- **Sales**: Sum of all "You Sold" transaction amounts from activity file

**Note:** When securities are purchased, the holdings change includes both market gains/losses AND the value of newly purchased shares. The purchases must be subtracted to isolate the actual investment performance.

## Unrealized Gain/Loss Calculation

Mark-to-market entries use the following logic for each holding:

```
if beginning_value is available:
    change_in_value = ending_value - beginning_value
else:
    change_in_value = ending_value - cost_basis
```

- Money market funds (FDRXX, SPAXX, FCASH) are excluded from unrealized calculations
- Unrealized entries are grouped by basket and recorded on the last day of the period

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

### Processing Rules

**Symbol Extraction:**
- Extract ticker symbol from parentheses in description
- Example: "GLOBAL X FDS RUSSELL 2000 (RYLD)" → symbol="RYLD", description="GLOBAL X FDS RUSSELL 2000"

**Beginning Value Handling:**
- If PDF shows "unavailable": Leave field empty (null)
- If PDF shows numeric value: Use that value

**Decimal Precision:**
- All numeric values: 3 decimal places
- Empty values: Leave blank (do not use "0" or "null" text)

### Example Output
```csv
symbol,description,quantity,price,beginning_value,ending_value,cost_basis,unrealized_gain
RYLD,GLOBAL X FDS RUSSELL 2000,203.623,16.050,,3268.140,3399.990,-131.850
VEGI,ISHARES INC MSCI AGRICULTURE,10.676,37.250,408.070,397.680,399.980,-2.300
CWCO,CONSOLIDATED WATER CO LTD,19.186,27.070,502.280,519.360,499.990,19.370
```

## "Income" Extraction Rules

### Input
- Source: "Dividends, Interest & Other Income" section of Fidelity PDF statement (typically page 7)
- Extract: All dividend, interest, and reinvestment transactions including money market funds (FDRXX, SPAXX, FCASH)

### Output Format
File: `scrapes/income/<<<YEAR>>>/MMW-YYYY-MM-INC.csv`

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
File: `scrapes/activity/<<<YEAR>>>/MMW-YYYY-MM-ACT.csv`

**Columns:**
1. `settlement_date` - Transaction settlement date (YYYY-MM-DD format)
2. `action` - Transaction type (e.g., "You Bought", "You Sold")
3. `symbol` - Stock/ETF ticker symbol extracted from description
4. `security_name` - Full security name with symbol removed
5. `quantity` - Number of shares/units traded (3 decimal precision)
6. `price` - Price per unit (3 decimal precision)
7. `amount` - Total transaction value (3 decimal precision)
8. `transaction_cost` - Commission/fees charged (3 decimal precision, empty if none)
9. `basket` - Basket identifier if transaction is part of a basket trade (empty if not applicable)

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

**Basket Handling:**
- If the security name contains "BASKET:" followed by a number: Extract the basket identifier
- Format: Extract only the numeric identifier after "BASKET:" (e.g., "BASKET:10003" → "10003")
- Example: "GLOBAL X FDS NASDAQ 100 COVER BASKET:10003" → basket="10003"
- Remove the basket reference from the security_name field
- Example: security_name="GLOBAL X FDS NASDAQ 100 COVER" (without "BASKET:10003")
- Empty values: Leave blank (do not use "0" or "null" text)

**Decimal Precision:**
- All numeric values: 3 decimal places
- Empty values: Leave blank (do not use "0" or "null" text)

**Commission Handling:**
- If commission is $0.00 or not shown: Leave field empty
- If commission exists: Include the value with 3 decimal precision

### Example Output
```csv
settlement_date,action,symbol,security_name,quantity,price,amount,transaction_cost,basket
2025-02-07,You Bought,MUST,COLUMBIA ETF TR I MULTI SEC MUNI,48.000,20.500,984.000,,10003
2025-02-07,You Bought,QYLD,GLOBAL X FDS NASDAQ 100 COVER,182.000,18.615,3387.910,,10003
2025-02-07,You Bought,RYLD,GLOBAL X FDS RUSSELL 2000,203.000,16.698,3389.590,,10003
2025-02-28,You Bought,APO,APOLLO GLOBAL MGMT INC COM,5.000,150.169,750.840,,10005
2025-02-28,You Bought,BRKB,BERKSHIRE HATHAWAY INC COM USD0.0033 CLASS B,9.000,503.280,4529.520,,10005
2025-02-28,You Sold,VEGI,ISHARES INC MSCI AGRICULTURE,10.676,37.250,397.680,,
```

## "Account Summary" Extraction Rules

### Input
- Source: "Account Summary" section of Fidelity PDF statement (typically page 2)
- Extract: Account value summary and activity breakdown for both "This Period" and "Year-to-Date"

### Output Format
File: `scrapes/summary/<<<YEAR>>>/MMW-YYYY-MM-SUM.csv`

**Columns:**
1. `period_start` - Statement period start date (YYYY-MM-DD format)
2. `period_end` - Statement period end date (YYYY-MM-DD format)
3. `beginning_value_period` - Beginning account value for this period (3 decimal precision)
4. `additions_period` - Additions for this period (3 decimal precision)
5. `subtractions_period` - Subtractions for this period (3 decimal precision)
6. `change_investment_value_period` - Change in investment value for this period (3 decimal precision)
7. `ending_value_period` - Ending account value for this period (3 decimal precision)
8. `beginning_value_ytd` - Beginning account value year-to-date (3 decimal precision)
9. `additions_ytd` - Additions year-to-date (3 decimal precision)
10. `subtractions_ytd` - Subtractions year-to-date (3 decimal precision)
11. `change_investment_value_ytd` - Change in investment value year-to-date (3 decimal precision)
12. `ending_value_ytd` - Ending account value year-to-date (3 decimal precision)
13. `income_period` - Total income for this period from Income Summary (3 decimal precision)
14. `income_ytd` - Total income year-to-date from Income Summary (3 decimal precision)

### Processing Rules

**Date Format:**
- Extract period dates from statement header (e.g., "February 1, 2025 - February 28, 2025")
- Convert to YYYY-MM-DD format
- period_start: "2025-02-01"
- period_end: "2025-02-28"

**Value Extraction:**
- Extract all values from "Account Summary" table on page 2
- "This Period" column → *_period fields
- "Year-to-Date" column → *_ytd fields
- Extract income totals from "Income Summary" section (Taxable dividends total)

**Decimal Precision:**
- All numeric values: 3 decimal places
- Negative values: Preserve the negative sign (e.g., -16000.000)

**Single Row Output:**
- This CSV contains only ONE row per statement (plus header)
- All summary data is captured in a single line

### Example Output
```csv
period_start,period_end,beginning_value_period,additions_period,subtractions_period,change_investment_value_period,ending_value_period,beginning_value_ytd,additions_ytd,subtractions_ytd,change_investment_value_ytd,ending_value_ytd,income_period,income_ytd
2025-02-01,2025-02-28,6119.670,50000.000,-16000.000,-48.540,40071.130,5873.110,50000.000,-16000.000,198.020,40071.130,139.310,216.470
```
