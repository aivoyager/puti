"""
@Author: obstacle
@Time: 26/06/20 11:00
@Description: Handles the daemonization of the Celery Beat scheduler.
"""
import os
import sys
import atexit
import subprocess
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any, Optional, Union
from puti.constant.base import Pathh
from puti.conf.config import conf
from puti.logs import logger_factory
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

lgr = logger_factory.default
console = Console()


def get_default_log_dir():
    """Reads the log directory from the global config, with a fallback."""
    try:
        return Path(conf.cc.module['common']['log_dir'])
    except (KeyError, AttributeError):
        return Path.home() / 'puti' / 'logs'


class SchedulerDaemon(BaseModel):
    """Handles the daemonization of the Celery Beat scheduler."""
    
    # Allow arbitrary attributes to be set
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}
    
    def __init__(self, **data):
        super().__init__(**data)
        # Initialize database managers
        from puti.db.base_manager import BaseManager
        from puti.db.model.system import SystemSetting
        self.setting_manager = BaseManager(model_type=SystemSetting)

    def model_post_init(self, __context: Any) -> None:
        """Initialize any resources needed by the daemon."""
        log_dir = get_default_log_dir()
        os.makedirs(log_dir, exist_ok=True)

    def _get_pid(self) -> Optional[int]:
        """Read the PID from the database."""
        setting = self.setting_manager.get_one(where_clause="name = 'scheduler_pid'")
        if setting:
            try:
                return int(setting.value)
            except (ValueError, TypeError):
                return None
        return None

    def _set_pid(self, pid: int) -> None:
        """Store the PID in the database."""
        from puti.db.model.system import SystemSetting
        setting = self.setting_manager.get_one(where_clause="name = 'scheduler_pid'")
        if setting:
            self.setting_manager.update(setting.id, {"value": str(pid)})
        else:
            setting = SystemSetting(
                name="scheduler_pid",
                value=str(pid),
                description="PID of the currently running Celery Beat scheduler daemon"
            )
            self.setting_manager.save(setting)

    def _clear_pid(self) -> None:
        """Remove the stored PID from the database."""
        setting = self.setting_manager.get_one(where_clause="name = 'scheduler_pid'")
        if setting:
            self.setting_manager.delete(setting.id, soft_delete=False)

    def is_running(self) -> bool:
        """Check if the daemon is currently running."""
        pid = self._get_pid()
        if not pid:
            return False
        
        try:
            os.kill(pid, 0)
        except OSError:
            # Process doesn't exist or we don't have permission to send signals
            # Clean up the stale PID record
            self._clear_pid()
            return False
        else:
            return True

    def start(self, activate_tasks: bool = True):
        """
        Start the Celery Beat scheduler as a daemon.
        
        Args:
            activate_tasks: Whether to activate all enabled schedules when starting
        """
        if self.is_running():
            pid = self._get_pid()
            lgr.warning(f"调度器已经在运行中，PID: {pid}")
            console.print(Panel(f"[yellow]调度器已经在运行中[/yellow]\nPID: [bold]{pid}[/bold]", 
                               title="调度器状态", border_style="yellow"))
            return

        lgr.info("正在启动Celery Beat调度器...")
        console.print("[blue]正在后台启动调度器守护进程...[/blue]")
        
        # 获取当前活跃任务状态
        try:
            from puti.db.schedule_manager import ScheduleManager
            manager = ScheduleManager()
            enabled_tasks = manager.get_active_schedules()
            active_count = len(enabled_tasks)
            lgr.info(f"发现 {active_count} 个已启用的计划任务")
        except Exception as e:
            lgr.error(f"获取活跃任务失败: {e}")
            active_count = -1
        
        # 激活所有已启用的计划任务 - 现在默认不激活
        if activate_tasks:
            try:
                result = self._ensure_enabled_schedules_run()
                if result:
                    lgr.info("已触发任务调度检查，所有任务将被自动启动")
                else:
                    lgr.warning("无法触发任务调度检查")
            except Exception as e:
                lgr.error(f"激活任务失败: {e}")
                console.print("[yellow]注意: 无法立即触发计划任务检查。[/yellow]")
                console.print("[yellow]计划任务仍将在下一个Celery Beat周期中被检测。[/yellow]")
        else:
            lgr.info("调度器启动时不自动激活任务，任务需要手动启动或等待下一个计划时间")

        # 使用共享的应用程序配置目录存放日志
        log_dir = get_default_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        # 将stdout和stderr合并到同一个日志文件中，方便监控
        log_path = log_dir / 'scheduler_beat.log'

        # 我们使用默认的Celery Beat调度器。它在celery_config.py中配置为
        # 运行我们的`check_dynamic_schedules`任务，该任务会从数据库中读取自定义调度。
        command = [
            'celery', '-A', 'celery_queue.celery_app', 'beat',
            '--loglevel=INFO'
        ]

        try:
            log_file = open(log_path, 'a')
            
            process = subprocess.Popen(
                command,
                stdout=log_file,
                stderr=subprocess.STDOUT, # 将stderr重定向到stdout
                preexec_fn=os.setsid
            )
            
            # 子进程已复制文件描述符，父进程应关闭其副本
            log_file.close()

            # 将PID存储到数据库中
            self._set_pid(process.pid)

            lgr.info(f"调度器已启动，PID: {process.pid}")
            
            # 构建任务启动说明
            task_info = ""
            if not activate_tasks:
                task_info = "\n[yellow]注意: 调度器启动时不会自动启动所有任务[/yellow]\n" \
                            "- 使用 [bold]puti scheduler run <任务ID>[/bold] 立即启动指定任务\n" \
                            "- 使用 [bold]puti scheduler list[/bold] 查看所有可用任务\n" \
                            "- 任务将在其下一个计划时间点自动执行"
            
            # 使用Rich创建更美观的输出
            start_panel = Panel(
                f"[green]调度器已成功启动[/green]\n\n"
                f"PID: [bold]{process.pid}[/bold]\n"
                f"日志文件: [cyan]{log_path.resolve()}[/cyan]\n"
                f"已启用任务数: [yellow]{active_count if active_count >= 0 else '未知'}[/yellow]"
                f"{task_info}",
                title="调度器状态",
                border_style="green"
            )
            console.print(start_panel)
            
            # 显示已启用任务的详细信息
            if enabled_tasks and len(enabled_tasks) > 0:
                task_table = Table(title="已启用的任务")
                task_table.add_column("ID", style="dim")
                task_table.add_column("名称", style="cyan")
                task_table.add_column("类型", style="magenta")
                task_table.add_column("Cron表达式", style="blue")
                task_table.add_column("下次执行", style="yellow")
                
                for task in enabled_tasks[:5]:  # 只显示前5个，避免过多输出
                    task_type_display = f"{task.task_type} ({task.task_type_display})" if hasattr(task, 'task_type_display') else task.task_type
                    next_run = task.next_run.strftime("%Y-%m-%d %H:%M:%S") if task.next_run else "未设置"
                    
                    task_table.add_row(
                        str(task.id),
                        task.name,
                        task_type_display,
                        task.cron_schedule,
                        next_run
                    )
                
                if len(enabled_tasks) > 5:
                    console.print(f"显示前5个任务 (共{len(enabled_tasks)}个)")
                    
                console.print(task_table)
                
                # 添加启动提示
                if not activate_tasks and len(enabled_tasks) > 0:
                    console.print("\n[cyan]提示: 要立即启动某个任务，请使用:[/cyan]")
                    console.print(f"  [bold]puti scheduler run <任务ID>[/bold]  例如: puti scheduler run {enabled_tasks[0].id}")
        except Exception as e:
            lgr.error(f"启动调度器失败: {e}")
            console.print(f"[red]启动调度器失败: {e}[/red]")
            return False
            
        return True

    def _ensure_enabled_schedules_run(self):
        """Makes sure that all active schedules in the database are running."""
        # Trigger an immediate check of all enabled schedules
        try:
            from celery_queue.simplified_tasks import check_dynamic_schedules
            result = check_dynamic_schedules.delay()
            lgr.info("已触发对所有已启用计划的立即检查。")
            return True
        except Exception as e:
            lgr.error(f"触发计划检查失败: {str(e)}")
            return False

    def stop(self):
        """停止调度器守护进程。"""
        pid = self._get_pid()
        if not pid:
            lgr.warning("调度器未运行（或在数据库中未找到PID）。")
            console.print("[yellow]调度器未运行。[/yellow]")
            return False

        lgr.info(f"正在停止PID为 {pid} 的调度器...")
        console.print(f"[blue]正在停止调度器 (PID: {pid})...[/blue]")

        try:
            # 尝试终止与PID关联的进程组
            os.killpg(os.getpgid(pid), 15)
            
            # 等待进程结束
            import time
            for _ in range(10):  # 最多等待5秒钟
                time.sleep(0.5)
                try:
                    # 检查进程是否仍在运行
                    os.kill(pid, 0)
                except OSError:
                    # 进程已经终止
                    break
            else:
                # 如果循环正常结束，表示进程仍在运行，尝试强制终止
                try:
                    lgr.warning(f"进程未响应SIGTERM信号，正在强制终止 (PID: {pid})...")
                    os.killpg(os.getpgid(pid), 9)  # SIGKILL
                except Exception as e:
                    lgr.error(f"强制终止进程失败: {e}")
            
            # 从数据库中清除PID
            self._clear_pid()
            
            lgr.info("调度器已成功停止。")
            console.print(Panel("[green]调度器已成功停止[/green]", 
                               title="调度器状态", 
                               border_style="green"))
            return True
        except ProcessLookupError:
            # 这不是致命错误。它只是意味着给定PID的进程未找到。
            # 可以安全地假设它已经停止。
            lgr.warning(f"未找到PID为 {pid} 的进程，可能已经停止。正在清理PID记录。")
            self._clear_pid()
            console.print(Panel("[yellow]未找到调度器进程，可能已经停止[/yellow]\n已清理数据库中的PID记录", 
                               title="调度器状态", 
                               border_style="yellow"))
            return True
        except OSError as e:
            # 清理数据库中的PID
            self._clear_pid()
            lgr.error(f"停止调度器失败: {e}")
            console.print(f"[red]停止调度器失败: {e}[/red]\n已清理数据库中的PID记录")
            return False
        except Exception as e:
            lgr.error(f"停止调度器时发生未知错误: {e}")
            console.print(f"[red]停止调度器失败: {e}[/red]")
            self._clear_pid()
            return False


# 避免自动清理守护进程
# 在CLI命令中，我们不应该自动清理已启动的守护进程
# 只需在异常情况下进行清理，例如CTRL+C中断启动过程时
_should_cleanup = False

def cleanup_daemon():
    """
    清理函数，只在特定条件下执行
    比如在调度器启动过程中异常终止时清理
    """
    global _should_cleanup
    if not _should_cleanup:
        return
        
    try:
        daemon = SchedulerDaemon()
        if daemon.is_running():
            lgr.warning("Cleaning up scheduler daemon due to abnormal termination")
            daemon.stop()
    except Exception as e:
        lgr.error(f"Error in cleanup_daemon: {e}")

# 注册清理函数，但默认情况下不会清理守护进程
atexit.register(cleanup_daemon) 