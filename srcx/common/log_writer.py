from pathlib import Path


def write_log(content: str, log_file: Path) -> None:
    """
    Append content to a log file.

    Args:
        content: The text content to write
        log_file: Path to the log file
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(content + "\n\n")
