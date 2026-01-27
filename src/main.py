"""Example usage of the statement scrape classes."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.statement import Statement


def main():
    """Example demonstrating how to use the Statement class."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent

    # Load data for May 2025 from scrapes directory
    statement = Statement(year=2025, month=5, base_path=project_root, auto_load=True)

    # Display statement information
    print("=" * 100)
    print(f"STATEMENT: {statement}")
    print("=" * 100)
    print()

    # Summary
    if statement.summary:
        print("SUMMARY:")
        print("-" * 100)
        print(f"  Period: {statement.summary.period_start} to {statement.summary.period_end}")
        print(f"  Beginning value: ${statement.summary.beginning_value_period:,.2f}")
        print(f"  Ending value: ${statement.summary.ending_value_period:,.2f}")
        print(f"  Change in investment value: ${statement.summary.change_investment_value_period:,.2f}")
        print(f"  Income (from summary): ${statement.summary.income_period:,.2f}")
        print()

    # Holdings summary
    if statement.holdings:
        print("HOLDINGS:")
        print("-" * 100)
        print(f"  Total positions: {len(statement.holdings)}")
        print(f"  Total change in value: ${statement.holdings.change_in_value:,.2f}")

        # Count money market vs regular
        mm_count = sum(1 for h in statement.holdings if h.is_money_market)
        reg_count = len(statement.holdings) - mm_count
        print(f"  Money market funds: {mm_count}")
        print(f"  Regular holdings: {reg_count}")
        print()

        print("  Holdings:")
        for i, holding in enumerate(statement.holdings):
            h_type = "MM" if holding.is_money_market else ""
            bv = "unavailable" if holding.beginning_value is None else f"${holding.beginning_value:,.2f}"
            print(f"    {holding.symbol:6} {h_type:3}| Qty: {holding.quantity:>10,.3f} | "
                  f"End: ${holding.ending_value:>10,.2f} | Change: ${holding.change_in_value:>10,.2f}")
        print()

    # Income summary
    if statement.income:
        print("INCOME:")
        print("-" * 100)
        print(f"  Total transactions: {len(statement.income)}")
        print(f"  Total income amount: ${statement.income.amount:,.2f}")
        print()

        print("  Transactions:")
        for transaction in statement.income:
            amount_str = f"${transaction.amount:,.2f}" if transaction.amount >= 0 else f"-${abs(transaction.amount):,.2f}"
            print(f"    {transaction.settlement_date} | {transaction.symbol:6} | {transaction.description:30} | {amount_str:>12}")
        print()

    # Activity summary
    if statement.activity:
        print("ACTIVITY:")
        print("-" * 100)
        print(f"  Total transactions: {len(statement.activity)}")

        # Sample transactions
        print("  Transactions:")
        for i, transaction in enumerate(statement.activity):
            qty_str = f"{transaction.quantity:,.3f}" if transaction.quantity else "N/A"
            price_str = f"${transaction.price:,.2f}" if transaction.price else "N/A"
            print(f"    {transaction.settlement_date} | {transaction.action:15} | {transaction.symbol:6} | "
                  f"Qty: {qty_str:>12} @ {price_str:>10}")
        print()

    # Validation
    print("VALIDATION:")
    print("-" * 100)
    print(f"  Expected (Summary change in value):    ${statement.summary.change_investment_value_period:>12,.2f}")
    print(f"  Calculated (Income + Holdings change): ${statement.income.amount + statement.holdings.change_in_value:>12,.2f}")
    print(f"  Difference:                            ${statement.summary.change_investment_value_period - (statement.income.amount + statement.holdings.change_in_value):>12,.2f}")
    print()
    print(f"  Is Validated:                           {statement.is_validated}")

    if not statement.is_validated:
        print()
        print("  Note: Validation failed - income transactions may be incomplete.")
        print(f"        Summary shows income of ${statement.summary.income_period:,.2f}")
        print(f"        but transactions total ${statement.income.amount:,.2f}")
        print(f"        Missing: ${statement.summary.income_period - statement.income.amount:,.2f}")

    print("=" * 100)
    print()

    # Write journal entries
    print("WRITING JOURNAL ENTRIES:")
    print("-" * 100)
    entries_file = statement.write_entries()
    print(f"  Journal entries written to: {entries_file}")
    print(f"  Total income amount: ${statement.income.amount:,.2f}")

    # Count entries
    import csv
    with open(entries_file, 'r') as f:
        reader = csv.DictReader(f)
        entries = list(reader)
        journal_count = len(set(e['Journal Number Suffix'] for e in entries))
        print(f"  Total journal entries: {len(entries)}")
        print(f"  Number of journals: {journal_count}")

    print("=" * 100)


if __name__ == '__main__':
    main()
