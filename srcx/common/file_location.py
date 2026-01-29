from pathlib import Path


class FileLocation(object):
    def __init__(self, year: int, month: int, root: str = None):

        if not 1 <= month <= 12:
            raise ValueError(f"Month must be between 1 and 12, got {month}")

        self._year: int = year
        self._month: int = month
        if root is None:
            self._base_path: Path = Path.cwd()
        else:
            self._base_path: Path = Path(root)

        # Build file path and load data
        self._summary_file: Path = self._base_path / 'scrapes' / 'summary' / str(year) / f"MMW-{year}-{month:02d}-SUM.csv"
        self._income_file: Path = self._base_path / 'scrapes' / 'income' / str(year) / f"MMW-{year}-{month:02d}-INC.csv"

    @property
    def year(self):
        return self._year

    @property
    def month(self):
        return self._month

    @property
    def summary_file(self):
        return self._summary_file

    @property
    def income_file(self):
        return self._income_file

    def __repr__(self):
        return (
            f"FileLocation(\n"
            f"  year = {self.year},\n"
            f"  month = {self.month},\n"
            f"  summary file = {self.summary_file},\n"
            f"  income file = {self.income_file}\n"
            f")"
        )

if __name__ == '__main__':
    _summary = FileLocation(2025, 9)
    print(repr(_summary))
