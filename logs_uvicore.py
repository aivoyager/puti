"""
@Author: obstacle
@Time: 20/01/25 14:46
@Description:  
"""
import logging
import os
from datetime import datetime
from typing import Any
from colorama import Fore, Style, init

init(autoreset=True)


# 配置日志格式并添加颜色
class ColorFormatter(logging.Formatter):
    LEVEL_COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT
    }

    def format(self, record):
        level_color = self.LEVEL_COLORS.get(record.levelname, "")
        log_message = f"{level_color}{super().format(record)}{Style.RESET_ALL}"
        return log_message


class HTMLColorFormatter(logging.Formatter):
    log_level_colors = {
        'DEBUG': '#00FFFF',  # 青色对应的 Hex
        'INFO': '#008000',  # 绿色对应的 Hex
        'WARNING': '#FFFF00',  # 黄色对应的 Hex
        'ERROR': '#FF0000',  # 红色对应的 Hex
        'CRITICAL': '#FF0000',  # 明亮红色
    }

    def format(self, record):
        log_level_color = self.log_level_colors.get(record.levelname, "#000000")

        # 格式化日志内容并添加颜色
        log_message = super().format(record)
        return f'<span style="color:{log_level_color}">{log_message}</span>'


def get_uvicorn_log_config(base_log_dir, log_level="DEBUG"):
    """
    获取动态配置的 Uvicorn 日志配置
    :param base_log_dir: 基础日志目录
    :param log_level: 最低日志级别，允许选择 DEBUG, INFO, WARNING, ERROR
    :return: 日志配置字典
    """
    log_dirs = {
        'debug': os.path.join(base_log_dir, 'debug'),
        'info': os.path.join(base_log_dir, 'info'),
        'warning': os.path.join(base_log_dir, 'warning'),
        'error': os.path.join(base_log_dir, 'error'),
    }

    # 创建日志目录
    for dir_path in log_dirs.values():
        os.makedirs(dir_path, exist_ok=True)
    all_logs_dir = os.path.join(base_log_dir, 'all')
    os.makedirs(all_logs_dir, exist_ok=True)

    current_date = datetime.now().strftime('%Y-%m-%d')

    # 定义动态生成的 handlers 和 loggers
    handlers = {}
    loggers = {}

    # 定义日志级别及其对应的文件名和级别
    levels = {
        "debug": "DEBUG",
        "info": "INFO",
        "warning": "WARNING",
        "error": "ERROR"
    }

    # 统一存储所有级别日志的 handler
    all_logs_path = os.path.join(all_logs_dir, f"{current_date}.log")
    # 动态生成 handlers 和 loggers 配置
    for level_name, level_value in levels.items():
        file_log_path = os.path.join(log_dirs[level_name], f"{current_date}.log")

        handlers[f"file_{level_name}"] = {
            "formatter": "default",
            "level": level_value,
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": file_log_path,
            "when": "midnight",
            "interval": 1,
            "backupCount": 7,
        }

        handlers[f"file_all_{level_name}"] = {
            "formatter": "html",
            "level": level_value,  # 捕获所有级别
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": all_logs_path,
            "when": "midnight",
            "interval": 1,
            "backupCount": 7,
        }

        loggers[f"uvicorn.{level_name}"] = {
            "handlers": ["colored", f"file_{level_name}", f"file_all_{level_name}"],  # 增加file_all
            "level": level_value,
            "propagate": False,
        }

    # 定义选择性的日志级别（根据传入的 log_level 过滤日志输出）
    log_level_priority = {
        "DEBUG": 0,
        "INFO": 1,
        "WARNING": 2,
        "ERROR": 3,
    }

    selected_priority = log_level_priority.get(log_level, 0)  # 默认设置为 DEBUG

    # 过滤 loggers 配置，根据选择的 log_level 设置最小日志级别
    for level_name, level_value in levels.items():
        if log_level_priority[level_value] >= selected_priority:
            # 保证大于等于选择级别的日志能够记录
            loggers[f"uvicorn.{level_name}"]["level"] = level_value
        else:
            # 小于选择级别的日志不记录
            loggers[f"uvicorn.{level_name}"]["level"] = "NOTSET"

    LOGGING_CONFIG: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "format": "%(asctime)s - %(levelname)-8s - %(message)s",
                "use_colors": None,
            },
            "colored": {
                "()": ColorFormatter,
                "format": "%(asctime)s - %(levelname)-8s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "html": {
                "()": HTMLColorFormatter,
                "format": "%(asctime)s - %(levelname)-8s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "colored": {
                "formatter": "colored",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            **handlers,  # 动态添加文件日志 handlers
        },
        "loggers": {
            **loggers,  # 动态添加 loggers 配置
        },
    }

    return LOGGING_CONFIG
