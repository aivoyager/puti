"""
@Author: obstacle
@Time: 28/06/25
@Description: Test script for logs command with real-time output
"""

import sys
import os
import click

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from puti.cli import scheduler


@click.command()
@click.argument('service', type=click.Choice(['worker', 'beat', 'scheduler']), default='worker')
@click.option('--lines', '-n', default=10, help="Number of log lines to show.")
@click.option('--follow', '-f', is_flag=True, help="Follow log output in real-time.")
@click.option('--filter', help="Filter logs by keyword.")
@click.option('--level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']), 
              help="Filter logs by minimum level.")
@click.option('--simple', is_flag=True, help="Use simple output format without timestamps.")
@click.option('--raw', is_flag=True, help="Show raw log output without any formatting.")
def test_logs(service, lines, follow, filter, level, simple, raw):
    """Test script for the logs command.
    
    This script makes it easy to test the logs command with various options.
    
    Example usage:
    python test/test_logs_command.py worker -n 5 -f
    python test/test_logs_command.py scheduler --level WARNING
    python test/test_logs_command.py beat --filter "ERROR" --simple
    """
    # 构建参数列表
    args = ['logs', service]
    if lines:
        args.extend(['-n', str(lines)])
    if follow:
        args.append('-f')
    if filter:
        args.extend(['--filter', filter])
    if level:
        args.extend(['--level', level])
    if simple:
        args.append('--simple')
    if raw:
        args.append('--raw')
    
    # 调用scheduler命令
    scheduler(args=args)


if __name__ == "__main__":
    test_logs() 