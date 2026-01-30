from pathlib import Path


class FileLocation(object):
    def __init__(self, year: int, month: int, root: str = None):

        if not 1 <= month <= 12:
            raise ValueError(f"Month must be between 1 and 12, got {month}")

        self._year: int = year
        self._month: int = month
        if root is None:
            self._root: Path = Path.cwd()
        else:
            self._root: Path = Path(root)

        # Build file path and load data
        # Input scrape files
        self._summary_file: Path = self._root / 'scrapes' / 'summary' / str(year) / f"MMW-{year}-{month:02d}-SUM.csv"
        self._income_file: Path = self._root / 'scrapes' / 'income' / str(year) / f"MMW-{year}-{month:02d}-INC.csv"
        self._activity_file: Path = self._root / 'scrapes' / 'activity' / str(year) / f"MMW-{year}-{month:02d}-ACT.csv"
        self._holdings_file: Path = self._root / 'scrapes' / 'holdings' / str(year) / f"MMW-{year}-{month:02d}-HLD.csv"
        # Output journal entry files
        self._dividend_file: Path = self._root / 'entries' / 'dividends' / str(year) / f"MMW-{year}-{month:02d}-DIV.csv"
        self._purchase_file: Path = self._root / 'entries' / 'purchases' / str(year) / f"MMW-{year}-{month:02d}-PUR.csv"
        self._sale_file: Path = self._root / 'entries' / 'sales' / str(year) / f"MMW-{year}-{month:02d}-SAL.csv"
        self._unrealized_file: Path = self._root / 'entries' / 'unrealized' / str(year) / f"MMW-{year}-{month:02d}-UNR.csv"
        self._entries_file: Path = self._root / 'entries' / f"MMW-{year}-{month:02d}-ENT.csv"
        # Log file
        self._log_file: Path = self._root / 'logs' / str(year) / f"{year}-{month:02d}.log"

    @property
    def year(self):
        return self._year

    @property
    def month(self):
        return self._month

    @property
    def root(self):
        return self._root

    @property
    def summary_file(self):
        return self._summary_file

    @property
    def income_file(self):
        return self._income_file

    @property
    def activity_file(self):
        return self._activity_file

    @property
    def holdings_file(self):
        return self._holdings_file

    @property
    def dividend_file(self):
        return self._dividend_file

    @property
    def purchase_file(self):
        return self._purchase_file

    @property
    def sale_file(self):
        return self._sale_file

    @property
    def unrealized_file(self):
        return self._unrealized_file

    @property
    def entries_file(self):
        return self._entries_file

    @property
    def log_file(self):
        return self._log_file

    def __repr__(self):
        return (
            f"FileLocation(\n"
            f"  year = {self.year},\n"
            f"  month = {self.month},\n"
            f"  summary file = {self.summary_file},\n"
            f"  income file = {self.income_file},\n"
            f"  activity file = {self.activity_file},\n"
            f"  holdings file = {self.holdings_file}\n"
            f")"
        )

if __name__ == '__main__':
    _summary = FileLocation(2025, 9)
    print(repr(_summary))
