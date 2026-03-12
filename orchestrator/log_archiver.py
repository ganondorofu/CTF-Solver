"""
Log archiver: moves old logs to date-based directories before each run.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def archive_old_logs(logs_dir: Path = Path("logs")) -> None:
    """
    Archive all existing log files to a timestamped directory.
    Called at the start of each orchestrator run.
    
    Args:
        logs_dir: Directory containing log files (default: logs/)
    """
    if not logs_dir.exists():
        logs_dir.mkdir(exist_ok=True)
        return
    
    # Find all log files in the main logs directory
    log_files = list(logs_dir.glob("*.log"))
    
    if not log_files:
        logger.info("No log files to archive")
        return
    
    # Create archive directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = logs_dir / f"archive_{timestamp}"
    archive_dir.mkdir(exist_ok=True)
    
    # Move each log file to the archive
    moved_count = 0
    total_size = 0
    
    for log_file in log_files:
        try:
            file_size = log_file.stat().st_size
            dest = archive_dir / log_file.name
            shutil.move(str(log_file), str(dest))
            moved_count += 1
            total_size += file_size
            logger.debug(f"Archived: {log_file.name} ({file_size / 1024:.1f} KB)")
        except Exception as e:
            logger.warning(f"Failed to archive {log_file.name}: {e}")
    
    if moved_count > 0:
        logger.info(
            f"Archived {moved_count} log files "
            f"({total_size / (1024 * 1024):.2f} MB) to {archive_dir.name}"
        )
    else:
        # Remove empty archive directory
        archive_dir.rmdir()


def cleanup_old_archives(logs_dir: Path = Path("logs"), keep_count: int = 10) -> None:
    """
    Remove oldest archive directories, keeping only the most recent ones.
    
    Args:
        logs_dir: Directory containing log archives
        keep_count: Number of recent archives to keep
    """
    if not logs_dir.exists():
        return
    
    # Find all archive directories
    archives = sorted(logs_dir.glob("archive_*"), key=lambda p: p.name)
    
    if len(archives) <= keep_count:
        return
    
    # Remove oldest archives
    to_remove = archives[:-keep_count]
    removed_count = 0
    
    for archive in to_remove:
        try:
            shutil.rmtree(archive)
            removed_count += 1
            logger.debug(f"Removed old archive: {archive.name}")
        except Exception as e:
            logger.warning(f"Failed to remove archive {archive.name}: {e}")
    
    if removed_count > 0:
        logger.info(f"Cleaned up {removed_count} old archives (keeping {keep_count} most recent)")
