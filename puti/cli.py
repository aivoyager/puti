import datetime

import puti.bootstrap  # noqa: F401, must be the first import
import click
import asyncio
import questionary
import os
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from puti.llm.roles.agents import Alex, Ethan
from puti.core.config_setup import ensure_twikit_config_is_present
from puti.constant.base import TaskType
from puti.scheduler import SchedulerDaemon
import re
import sys
import json
import time
import signal
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple, Union


@click.group()
def main():
    """Puti CLI Tool: An interactive AI assistant."""
    pass


@main.command()
@click.option('--name', default='Alex', help='Name of the Alex agent.')
def alex_chat(name):
    """Starts an interactive chat with Alex agent."""
    console = Console()
    console.print(Panel(
        Markdown("Alex is an all-purpose bot with multiple integrated tools to help you with a wide range of tasks."),
        title="🤖 Meet Alex",
        border_style="cyan"
    ))
    welcome_message = Markdown(f"""
# 💬 Chat with {name}
*   Type your message and press Enter to send.
*   Type `exit` or `quit` to end the chat.
*   Press `Ctrl+D` or `Ctrl+C` to exit immediately.
""")
    console.print(welcome_message)

    alex_agent = Alex(name=name)

    async def chat_loop():
        while True:
            try:
                user_input = await questionary.text("👤 You:", qmark="").ask_async()
                if user_input is None or user_input.lower() in ['exit', 'quit']:
                    break

                console.print(Panel(user_input, title="👤 You", border_style="blue"))

                # Show a thinking indicator
                with console.status(f"[bold cyan]{name} is thinking...", spinner="dots"):
                    response = await alex_agent.run(user_input)

                # Print the response in a styled panel
                response_panel = Panel(
                    Markdown(response.content),
                    title=f"🤖 {name}",
                    border_style="green",
                    title_align="left"
                )
                console.print(response_panel)

            except (KeyboardInterrupt, EOFError):
                # Handle Ctrl+C and Ctrl+D
                break

    try:
        asyncio.run(chat_loop())
    finally:
        console.print("\n[bold yellow]Chat session ended. Goodbye![/bold yellow]")


@main.command()
@click.option('--name', default='Ethan', help='Name of the Ethan agent.')
def ethan_chat(name):
    """Starts an interactive chat with Ethan agent."""
    ensure_twikit_config_is_present()
    console = Console()
    console.print(Panel(
        Markdown("Ethan is a Twitter bot designed to help you manage your daily Twitter activities."),
        title="🤖 Meet Ethan",
        border_style="cyan"
    ))
    welcome_message = Markdown(f"""
# 💬 Chat with {name}
*   Type your message and press Enter to send.
*   Type `exit` or `quit` to end the chat.
*   Press `Ctrl+D` or `Ctrl+C` to exit immediately.
""")
    console.print(welcome_message)

    ethan_agent = Ethan(name=name)

    async def chat_loop():
        while True:
            try:
                user_input = await questionary.text("👤 You:", qmark="").ask_async()
                if user_input is None or user_input.lower() in ['exit', 'quit']:
                    break

                console.print(Panel(user_input, title="👤 You", border_style="blue"))

                with console.status(f"[bold cyan]{name} is thinking...", spinner="dots"):
                    response = await ethan_agent.run(user_input)

                response_panel = Panel(
                    Markdown(response),
                    title=f"🤖 {name}",
                    border_style="green",
                    title_align="left"
                )
                console.print(response_panel)

            except (KeyboardInterrupt, EOFError):
                break

    try:
        asyncio.run(chat_loop())
    finally:
        console.print("\n[bold yellow]Chat session ended. Goodbye![/bold yellow]")


def check_scheduler_status():
    """检查调度器状态并返回状态信息"""
    from rich.console import Console
    from rich.panel import Panel
    from puti.db.schedule_manager import ScheduleManager
    
    console = Console()
    daemon = SchedulerDaemon()
    manager = ScheduleManager()
    
    scheduler_running = daemon.is_running()
    scheduler_pid = daemon._get_pid() if scheduler_running else None
    
    # 获取任务统计数据
    try:
        all_schedules = manager.get_all(where_clause="is_del = 0")
        enabled_schedules = [s for s in all_schedules if s.enabled]
        running_schedules = [s for s in all_schedules if s.is_running]
        
        # 计算最近任务信息
        upcoming_tasks = []
        for s in enabled_schedules:
            if s.next_run and not s.is_running:
                upcoming_tasks.append((s.id, s.name, s.next_run))
        
        # 按下次执行时间排序
        upcoming_tasks.sort(key=lambda x: x[2])
        
        # 构建状态文本
        if scheduler_running:
            status_text = f"[green]调度器正在运行[/green] (PID: {scheduler_pid})"
        else:
            status_text = "[red]调度器未运行[/red] (所有任务处于暂停状态)"
        
        # 构建统计信息
        stats_text = (
            f"总计: {len(all_schedules)} 个任务 | "
            f"已启用: {len(enabled_schedules)} | "
            f"运行中: {len(running_schedules)} | "
            f"已禁用: {len(all_schedules) - len(enabled_schedules)}"
        )
        
        # 添加即将执行的任务信息（如果有）
        upcoming_info = ""
        if upcoming_tasks and len(upcoming_tasks) > 0:
            next_task = upcoming_tasks[0]
            time_diff = next_task[2] - datetime.datetime.now()
            if time_diff.total_seconds() > 0:
                days = time_diff.days
                hours, remainder = divmod(time_diff.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                time_str = f"{days}天{hours}时{minutes}分{seconds}秒后"
            else:
                time_str = "即将执行"
            
            upcoming_info = f"\n下一个任务: {next_task[1]} (ID: {next_task[0]}) 将在 {time_str} 执行"
        
        # 显示状态面板
        panel = Panel(
            f"{status_text}\n{stats_text}{upcoming_info}",
            title="调度器状态",
            border_style="cyan"
        )
        console.print(panel)
        
        return scheduler_running
    except Exception as e:
        console.print(f"[red]获取调度器状态时出错: {str(e)}[/red]")
        return scheduler_running


@main.group(invoke_without_command=True)
@click.pass_context
def scheduler(ctx):
    """
    tweet调度器操作。
    """
    # 如果没有调用子命令，就显示帮助信息
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        # 无子命令时，默认检查调度器状态
        check_scheduler_status()
    # 对于list命令不显示状态，因为它有自己的状态显示
    elif ctx.invoked_subcommand not in ['start', 'stop', 'auto_shutdown', 'logs', 'list', 'tasks', 'workers']:
        # 对于不改变调度器状态且不显示状态的命令，显示当前状态
        check_scheduler_status()


@scheduler.command()
@click.option('--all', '-a', is_flag=True, help="显示所有计划，包括已禁用的")
@click.option('--running', '-r', is_flag=True, help="只显示当前正在运行的计划")
@click.option('--type', '-t', help="按任务类型筛选 (post/reply/retweet等)")
@click.option('--simple', '-s', is_flag=True, help="使用简化视图（少量信息）")
def list(all, running, type, simple):
    """列出所有计划任务。默认只显示已启用的任务。"""
    import datetime
    import os
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from puti.constant.base import TaskType
    
    console = Console()
    manager = ScheduleManager()
    
    # 设置是否显示详细信息 (默认显示详细信息，除非指定--simple)
    detail = not simple
    
    # 根据不同的过滤条件获取计划任务
    if running:
        schedules = manager.get_running_schedules()
        table_title = "正在运行的计划任务"
    elif type:
        try:
            task_type_val = TaskType.elem_from_str(type).val
            if all:
                # 获取所有指定类型的任务，包括禁用的，但不包括删除的
                schedules = manager.get_all(where_clause="task_type = ? AND is_del = 0", params=(task_type_val,))
                table_title = f"所有{TaskType.elem_from_str(type).dsp}计划任务"
            else:
                # 获取已启用的指定类型的任务
                schedules = manager.get_all(where_clause="task_type = ? AND enabled = 1 AND is_del = 0", params=(task_type_val,))
                table_title = f"已启用的{TaskType.elem_from_str(type).dsp}计划任务"
        except ValueError:
            console.print(f"[red]错误:[/red] 无效的任务类型: {type}")
            console.print("有效的任务类型: " + ", ".join([f"{t.val} ({t.dsp})" for t in TaskType]))
            return
    elif all:
        schedules = manager.get_all(where_clause="is_del = 0")
        table_title = "所有计划任务 (包括已禁用)"
    else:
        schedules = manager.get_all(where_clause="enabled = 1 AND is_del = 0")
        table_title = "已启用的计划任务"
    
    if not schedules:
        console.print(f"[yellow]没有找到符合条件的计划任务[/yellow]")
        return
    
    # 获取调度器守护进程PID
    from puti.scheduler import SchedulerDaemon
    daemon = SchedulerDaemon()
    scheduler_pid = daemon._get_pid()
    scheduler_running = daemon.is_running()
    
    # 在表格标题中显示调度器状态
    if scheduler_running:
        table_title = f"{table_title} [绿色背景表示正在运行的任务]"
    else:
        table_title = f"{table_title} [调度器当前未运行，任务处于暂停状态]"
    
    # 创建表格
    table = Table(title=table_title)
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("名称", style="cyan")
    table.add_column("类型", style="magenta")
    table.add_column("Cron表达式", style="blue")
    table.add_column("状态", style="green")
    table.add_column("下次执行", style="yellow")
    
    if detail:
        table.add_column("上次执行", style="bright_black")
        table.add_column("进程信息", style="bright_blue")
        table.add_column("参数", style="bright_cyan", no_wrap=False)
    
    # 填充表格
    for schedule in schedules:
        # 行样式 - 运行中的任务使用绿色背景
        row_style = "on green" if schedule.is_running else None
        
        # 基本状态信息
        status = "✅ 已启用" if schedule.enabled else "❌ 已禁用"
        if schedule.is_running:
            status = "🟢 运行中"
            if not scheduler_running:
                status = "⚠️ 运行中(调度器已停止)"
        
        # 获取任务类型显示名称
        try:
            schedule_type = schedule.task_type
            schedule_type_display = schedule.task_type_display
            task_type_display = f"{schedule_type} ({schedule_type_display})"
        except Exception as e:
            task_type_display = str(schedule.task_type)
            console.print(f"[yellow]警告: 无法解析任务类型 {e}[/yellow]")
        
        # 下次执行时间
        if schedule.next_run:
            # 使用croniter实时计算下次执行时间，而不是使用数据库中的值
            from croniter import croniter
            import datetime
            
            now = datetime.datetime.now()
            try:
                # 如果上次执行时间存在且在当前时间之后，则使用上次执行时间作为基准
                base_time = max(now, schedule.last_run) if schedule.last_run else now
                calc_next_run = croniter(schedule.cron_schedule, base_time).get_next(datetime.datetime)
                
                # 格式化显示
                next_run = calc_next_run.strftime("%Y-%m-%d %H:%M:%S")
                
                # 计算距离现在的时间
                time_diff = calc_next_run - now
                if time_diff.total_seconds() > 0:
                    days = time_diff.days
                    hours, remainder = divmod(time_diff.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    countdown = f"({days}天{hours}时{minutes}分后)"
                    next_run += f"\n{countdown}"
                else:
                    next_run += "\n[red](已过期)[/red]"
            except Exception as e:
                next_run = schedule.next_run.strftime("%Y-%m-%d %H:%M:%S") if schedule.next_run else "未设置"
                next_run += f"\n[red](计算错误: {str(e)})[/red]"
        else:
            next_run = "未设置"
        
        if detail:
            # 上次执行时间
            last_run = schedule.last_run.strftime("%Y-%m-%d %H:%M:%S") if schedule.last_run else "从未执行"
            
            # 进程信息 - 增强显示
            process_info = ""
            # 检查PID是否存在且进程是否在运行
            if schedule.pid:
                try:
                    # 尝试发送信号0检查进程是否存在
                    os.kill(schedule.pid, 0)
                    process_info = f"[green]PID: {schedule.pid} (运行中)[/green]"
                except OSError:
                    process_info = f"[red]PID: {schedule.pid} (已终止)[/red]"
            
            # 添加Celery任务ID
            if schedule.task_id:
                if process_info:
                    process_info += f"\nTask ID: {schedule.task_id}"
                else:
                    process_info = f"Task ID: {schedule.task_id}"
            
            if not process_info:
                process_info = "[dim]无进程信息[/dim]"
            
            # 参数信息 - 简化处理，避免类型错误
            params_str = ""
            if schedule.params:
                for k, v in schedule.params.items():
                    params_str += f"{k}: {v}\n"
                params_str = params_str.strip()
            else:
                params_str = "[dim]无[/dim]"
            
            # 添加行
            table.add_row(
                str(schedule.id),
                schedule.name,
                task_type_display,
                schedule.cron_schedule,
                status,
                next_run,
                last_run,
                process_info,
                params_str,
                style=row_style
            )
        else:
            # 添加基本信息行
            table.add_row(
                str(schedule.id),
                schedule.name,
                task_type_display,
                schedule.cron_schedule,
                status,
                next_run,
                style=row_style
            )
    
    console.print(table)
    
    # 无论是否详细模式，都显示调度器和任务汇总信息
    if scheduler_running:
        scheduler_status = f"[green]调度器正在运行[/green] (PID: {scheduler_pid})"
    else:
        scheduler_status = "[red]调度器未运行[/red] (所有任务处于暂停状态)"
    
    summary = Panel(
        f"{scheduler_status}\n"
        f"总计: {len(schedules)} 个任务 | "
        f"运行中: {sum(1 for s in schedules if s.is_running)} | "
        f"等待执行: {sum(1 for s in schedules if s.enabled and not s.is_running)} | "
        f"已禁用: {sum(1 for s in schedules if not s.enabled)}",
        title="调度器与任务统计",
        border_style="cyan"
    )
    console.print(summary)


@scheduler.command()
@click.argument('name', required=True)
@click.argument('cron', required=True)
@click.option('--topic', '-t', help='推文生成的主题')
@click.option('--disabled', is_flag=True, help='创建时禁用此计划')
@click.option('--type', '-y', default='post', help='任务类型 (post/reply/retweet等)')
@click.option('--autostart', '-a', is_flag=True, help='创建后自动启动任务，不等待定时')
def create(name, cron, topic=None, disabled=False, type='post', autostart=False):
    """创建新的计划推文任务。可选择创建后立即启动，而不是等待定时触发。"""
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    from rich.panel import Panel
    import datetime
    from croniter import croniter
    from puti.constant.base import TaskType
    
    console = Console()
    manager = ScheduleManager()
    
    # 检查名称是否已存在
    existing = manager.get_by_name(name)
    if existing:
        console.print(f"[red]错误:[/red] 名为 '{name}' 的计划任务已存在 (ID: {existing.id})。")
        console.print("请使用不同的名称，或先删除现有计划任务。")
        return
    
    # 验证任务类型
    try:
        task_type = TaskType.elem_from_str(type).val
        task_type_display = TaskType.elem_from_str(type).dsp
    except ValueError:
        console.print(f"[red]错误:[/red] 无效的任务类型: {type}")
        console.print("可用的任务类型: " + ", ".join([f"{t.val} ({t.dsp})" for t in TaskType]))
        return
    
    # 验证cron表达式
    try:
        now = datetime.datetime.now()
        next_run = croniter(cron, now).get_next(datetime.datetime)
    except ValueError as e:
        console.print(f"[red]错误:[/red] 无效的cron表达式: {cron}")
        console.print(f"详细信息: {str(e)}")
        return
    
    # 准备参数
    params = {}
    if topic:
        params['topic'] = topic
    
    # 创建计划
    try:
        schedule = manager.create_schedule(
            name=name,
            cron_schedule=cron,
            enabled=not disabled,
            params=params,
            task_type=task_type
        )
        
        # 构建任务信息面板
        info_lines = [
            f"[green]✅ 已创建计划任务:[/green] '{name}' (ID: {schedule.id})",
            f"任务类型: [magenta]{task_type_display}[/magenta]",
            f"Cron表达式: [blue]{cron}[/blue]",
            f"下次执行: [yellow]{schedule.next_run.strftime('%Y-%m-%d %H:%M:%S')}[/yellow]",
            f"状态: {('[green]已启用[/green]' if not disabled else '[red]已禁用[/red]')}"
        ]
        
        if topic:
            info_lines.append(f"主题: [cyan]{topic}[/cyan]")
            
        console.print(Panel("\n".join(info_lines), title="计划任务创建成功", border_style="green"))
        
        # 如果设置了自动启动选项且任务未被禁用，立即启动任务
        if autostart and not disabled:
            from puti.scheduler import SchedulerDaemon
            daemon = SchedulerDaemon()
            scheduler_running = daemon.is_running()
            
            if not scheduler_running:
                console.print("[yellow]警告: 调度器未运行，无法自动启动任务。[/yellow]")
                console.print("请先使用 [bold]puti scheduler start[/bold] 启动调度器，然后使用 [bold]puti scheduler run {schedule.id}[/bold] 手动启动任务。")
            else:
                try:
                    console.print(f"[cyan]正在自动启动计划任务 '{name}'...[/cyan]")
                    if manager.start_task(schedule.id):
                        console.print(f"[green]✅ 已自动启动计划任务 '{name}'[/green]")
                        console.print("使用 [bold]puti scheduler logs[/bold] 命令监控任务进度。")
                    else:
                        console.print(f"[yellow]警告: 无法自动启动计划任务 '{name}'[/yellow]")
                except Exception as e:
                    console.print(f"[yellow]警告: 自动启动任务时出错: {str(e)}[/yellow]")
        
        # 提示用户如何启动任务
        if not autostart and not disabled:
            console.print("\n[cyan]提示: 要立即启动此任务，请运行:[/cyan]")
            console.print(f"  [bold]puti scheduler run {schedule.id}[/bold]")
            
    except Exception as e:
        console.print(f"[red]创建计划任务时出错:[/red] {str(e)}")


@scheduler.command()
@click.argument('schedule_id', type=int)
def stop(schedule_id):
    """停止指定的任务。"""
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    manager = ScheduleManager()
    
    # 检查任务是否存在
    schedule = manager.get_by_id(schedule_id)
    if not schedule:
        console.print(f"[red]错误: 未找到ID为 {schedule_id} 的任务[/red]")
        return
    
    # 检查任务是否正在运行
    if not schedule.is_running:
        console.print(f"[yellow]任务 '{schedule.name}' 当前未在运行，无需停止。[/yellow]")
        return
    
    # 尝试停止任务
    console.print(f"[cyan]正在停止任务 '{schedule.name}'...[/cyan]")
    
    if manager.stop_task(schedule_id):
        console.print(Panel(
            f"[green]✅ 已成功停止任务 '{schedule.name}'[/green]\n"
            f"任务ID: {schedule_id}",
            title="任务已停止",
            border_style="green"
        ))
    else:
        console.print(Panel(
            f"[red]停止任务 '{schedule.name}' 失败[/red]\n"
            "可能是由于任务已经结束或进程无法被终止。",
            title="停止失败",
            border_style="red"
        ))


@scheduler.command()
@click.argument('schedule_ids', required=False)
@click.option('--all', '-a', is_flag=True, help="删除所有计划任务")
@click.option('--force', '-f', is_flag=True, help="强制删除，不进行确认")
@click.option('--type', '-t', help="按类型删除计划任务")
def delete(schedule_ids, all, force, type):
    """删除计划任务。支持单个ID、多个ID (以逗号分隔)、ID范围 (如5-10)、指定类型或全部删除。"""
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import Confirm
    from puti.constant.base import TaskType
    
    console = Console()
    manager = ScheduleManager()
    
    # 用于存储要删除的计划ID
    ids_to_delete = []
    
    # 根据类型筛选
    if type:
        try:
            task_type_val = TaskType.elem_from_str(type).val
            schedules = manager.get_schedules_by_type(task_type_val)
            if not schedules:
                console.print(f"[yellow]没有找到类型为 '{type}' 的计划任务。[/yellow]")
                return
            
            ids_to_delete = [s.id for s in schedules]
            type_display = TaskType.elem_from_str(type).dsp
            
            # 显示将被删除的任务
            console.print(f"[yellow]将删除 {len(ids_to_delete)} 个类型为 '{type_display}' 的任务。[/yellow]")
            
            if not force and not Confirm.ask("确定要继续吗?"):
                console.print("[yellow]操作已取消。[/yellow]")
                return
                
        except ValueError:
            console.print(f"[red]错误:[/red] 无效的任务类型: {type}")
            console.print("有效的任务类型: " + ", ".join([f"{t.val} ({t.dsp})" for t in TaskType]))
            return
    
    # 删除所有计划
    elif all:
        schedules = manager.get_all()
        if not schedules:
            console.print("[yellow]没有找到任何计划任务。[/yellow]")
            return
            
        ids_to_delete = [s.id for s in schedules]
        
        # 显示将被删除的任务数量
        console.print(f"[yellow]将删除所有 {len(ids_to_delete)} 个计划任务。[/yellow]")
        
        if not force and not Confirm.ask("确定要继续吗?"):
            console.print("[yellow]操作已取消。[/yellow]")
            return
    
    # 根据ID筛选
    elif schedule_ids:
        # 检查是否是范围格式 (如 "5-10")
        if '-' in schedule_ids and schedule_ids.count('-') == 1 and ',' not in schedule_ids:
            try:
                start, end = map(int, schedule_ids.split('-'))
                if start > end:
                    start, end = end, start  # 交换，确保start小于end
                
                # 验证每个ID是否存在
                for id in range(start, end + 1):
                    schedule = manager.get_by_id(id)
                    if schedule:
                        ids_to_delete.append(id)
                
                if not ids_to_delete:
                    console.print(f"[yellow]ID范围 {start}-{end} 内没有找到任何计划任务。[/yellow]")
                    return
                
                console.print(f"[yellow]将删除ID范围 {start}-{end} 内的 {len(ids_to_delete)} 个计划任务。[/yellow]")
                
                if not force and not Confirm.ask("确定要继续吗?"):
                    console.print("[yellow]操作已取消。[/yellow]")
                    return
                    
            except ValueError:
                console.print(f"[red]错误:[/red] 无效的ID范围格式: {schedule_ids}")
                console.print("正确格式示例: 5-10")
                return
        
        # 检查是否是逗号分隔的ID列表
        elif ',' in schedule_ids:
            try:
                id_list = [int(id.strip()) for id in schedule_ids.split(',')]
                
                # 验证每个ID是否存在
                for id in id_list:
                    schedule = manager.get_by_id(id)
                    if schedule:
                        ids_to_delete.append(id)
                    else:
                        console.print(f"[yellow]警告: ID为 {id} 的计划任务不存在，将跳过。[/yellow]")
                
                if not ids_to_delete:
                    console.print("[yellow]指定的ID列表中没有找到任何有效的计划任务。[/yellow]")
                    return
                
                console.print(f"[yellow]将删除 {len(ids_to_delete)} 个计划任务。[/yellow]")
                
                if not force and not Confirm.ask("确定要继续吗?"):
                    console.print("[yellow]操作已取消。[/yellow]")
                    return
                    
            except ValueError:
                console.print(f"[red]错误:[/red] 无效的ID格式: {schedule_ids}")
                console.print("正确格式示例: 1,3,5")
                return
        
        # 单个ID
        else:
            try:
                schedule_id = int(schedule_ids)
                schedule = manager.get_by_id(schedule_id)
                
                if not schedule:
                    console.print(f"[red]错误:[/red] ID为 {schedule_id} 的计划任务不存在。")
                    return
                
                ids_to_delete = [schedule_id]
                
                console.print(f"[yellow]将删除计划任务 '{schedule.name}' (ID: {schedule_id})。[/yellow]")
                
                if not force and not Confirm.ask("确定要继续吗?"):
                    console.print("[yellow]操作已取消。[/yellow]")
                    return
                    
            except ValueError:
                console.print(f"[red]错误:[/red] 无效的ID格式: {schedule_ids}")
                return
    else:
        # 如果没有提供参数，显示帮助信息
        console.print("[yellow]请指定要删除的计划任务ID、类型或使用--all参数删除所有任务。[/yellow]")
        console.print("示例:")
        console.print("  delete 1                # 删除ID为1的任务")
        console.print("  delete 1,3,5            # 删除ID为1、3和5的任务")
        console.print("  delete 5-10             # 删除ID在5到10范围内的任务")
        console.print("  delete --type post      # 删除所有类型为post的任务")
        console.print("  delete --all            # 删除所有任务")
        return
    
    # 执行删除操作
    if ids_to_delete:
        # 显示要删除的任务的详细信息
        if len(ids_to_delete) > 1:
            table = Table(title=f"将删除以下 {len(ids_to_delete)} 个计划任务")
            table.add_column("ID", style="dim")
            table.add_column("名称", style="cyan")
            table.add_column("类型", style="magenta")
            table.add_column("Cron表达式", style="blue")
            table.add_column("状态", style="green")
            
            for id in ids_to_delete:
                schedule = manager.get_by_id(id)
                if schedule:
                    status = "✅ 已启用" if schedule.enabled else "❌ 已禁用"
                    if schedule.is_running:
                        status = "🟢 运行中"
                    
                    try:
                        task_type_display = f"{schedule.task_type} ({schedule.task_type_display})"
                    except:
                        task_type_display = str(schedule.task_type)
                    
                    table.add_row(
                        str(schedule.id),
                        schedule.name,
                        task_type_display,
                        schedule.cron_schedule,
                        status
                    )
            
            console.print(table)
            
            if not force and not Confirm.ask("最后确认: 是否删除这些任务?"):
                console.print("[yellow]操作已取消。[/yellow]")
                return
        
        # 执行批量删除
        success_count = 0
        error_count = 0
        for id in ids_to_delete:
            schedule = manager.get_by_id(id)
            if not schedule:
                continue
                
            # 如果计划正在运行，先停止它
            if schedule.is_running:
                manager.stop_task(id)
                console.print(f"[yellow]已停止正在运行的任务 '{schedule.name}'。[/yellow]")
            
            # 删除计划
            if manager.delete(id):
                success_count += 1
            else:
                error_count += 1
                console.print(f"[red]删除计划任务 '{schedule.name}' (ID: {id}) 失败。[/red]")
        
        # 显示删除结果
        if success_count > 0:
            console.print(f"[green]已成功删除 {success_count} 个计划任务。[/green]")
        if error_count > 0:
            console.print(f"[red]删除 {error_count} 个计划任务时出错。[/red]")
            
        # 如果成功删除了一些任务，触发调度器更新
        if success_count > 0:
            try:
                from celery_queue.simplified_tasks import check_dynamic_schedules
                check_dynamic_schedules.delay()
                console.print("[green]已触发调度器更新。[/green]")
            except Exception as e:
                console.print(f"[yellow]警告: 无法触发调度器更新: {str(e)}[/yellow]")


@scheduler.command()
@click.argument('schedule_id', type=int)
def run(schedule_id):
    """启动指定的任务。"""
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm
    import os
    import datetime
    
    console = Console()
    
    # 确保PUTI_DATA_PATH环境变量已设置
    if 'PUTI_DATA_PATH' not in os.environ:
        from pathlib import Path
        default_path = str(Path.home() / 'puti' / 'data')
        if Path(default_path).exists():
            os.environ['PUTI_DATA_PATH'] = default_path
            console.print(f"[yellow]已自动设置环境变量: PUTI_DATA_PATH={default_path}[/yellow]")
        else:
            parent_path = str(Path.home() / 'puti')
            if Path(parent_path).exists():
                os.environ['PUTI_DATA_PATH'] = parent_path
                console.print(f"[yellow]已自动设置环境变量: PUTI_DATA_PATH={parent_path}[/yellow]")
    
    # 检查系统日期是否异常
    current_date = datetime.datetime.now()
    if current_date.year > 2024:
        console.print(Panel(
            f"[red]警告: 系统日期可能不正确: {current_date.strftime('%Y-%m-%d %H:%M:%S')}[/red]\n"
            "不正确的系统日期会导致任务调度和执行出现问题。\n"
            "建议修正系统日期后再使用调度器。",
            title="系统日期警告",
            border_style="red"
        ))
        if not Confirm.ask("系统日期异常，是否仍然继续?", default=False):
            return
    
    manager = ScheduleManager()
    
    # 获取调度器状态
    from puti.scheduler import SchedulerDaemon
    daemon = SchedulerDaemon()
    scheduler_running = daemon.is_running()
    
    # 检查任务是否存在
    schedule = manager.get_by_id(schedule_id)
    if not schedule:
        console.print(f"[red]错误: 未找到ID为 {schedule_id} 的任务[/red]")
        return
    
    # 对于已禁用的计划显示警告
    if not schedule.enabled:
        console.print(f"[yellow]警告: 计划任务 '{schedule.name}' 当前已禁用。[/yellow]")
        confirm = Confirm.ask("是否仍然要运行该任务?", default=True)
        if not confirm:
            console.print("[yellow]已取消执行任务。[/yellow]")
            return
    
    # 检查任务是否已在运行
    if schedule.is_running:
        console.print(f"[yellow]警告: 计划任务 '{schedule.name}' 当前正在运行。[/yellow]")
        console.print(f"进程ID: {schedule.pid if schedule.pid else '未知'}")
        console.print(f"任务ID: {schedule.task_id if schedule.task_id else '未知'}")
        
        confirm = Confirm.ask("是否要强制启动新的任务实例?", default=False)
        if not confirm:
            console.print("[yellow]已取消执行任务。[/yellow]")
            return
    
    # 自动启动调度器如果未运行
    if not scheduler_running:
        console.print("[yellow]调度器当前未运行，正在启动...[/yellow]")
        daemon.start(activate_tasks=False)
        # 等待调度器启动
        time.sleep(2)
        if daemon.is_running():
            console.print("[green]调度器已成功启动[/green]")
        else:
            console.print("[red]调度器启动失败[/red]")
            confirm = Confirm.ask("是否仍然尝试运行任务?", default=True)
            if not confirm:
                console.print("[yellow]已取消执行任务。[/yellow]")
                return
    
    # 从计划中提取参数
    params = schedule.params or {}
    topic = params.get('topic', '')
    
    # 发送celery任务
    try:
        from celery_queue.simplified_tasks import generate_tweet_task
        
        # 更新运行状态
        manager.update_schedule(schedule_id, is_running=True)
        
        # 确定任务类型
        use_graph_workflow = False
        if hasattr(schedule, 'task_type'):
            from puti.constant.base import TaskType
            if schedule.task_type == TaskType.POST.val:
                use_graph_workflow = True
        
        # 启动任务
        task = generate_tweet_task.delay(topic=topic, use_graph_workflow=use_graph_workflow)
        
        # 更新任务信息
        manager.update_schedule(schedule_id, task_id=task.id)
        
        console.print(Panel(
            f"任务ID: [cyan]{task.id}[/cyan]\n"
            f"主题: [cyan]{topic if topic else '默认'}[/cyan]\n"
            f"使用Graph Workflow: [cyan]{'是' if use_graph_workflow else '否'}[/cyan]",
            title=f"[green]已成功启动任务 '{schedule.name}'[/green]",
            border_style="green"
        ))
    except Exception as e:
        console.print(Panel(
            f"错误详情: {str(e)}",
            title=f"[red]启动任务 '{schedule.name}' 失败[/red]",
            border_style="red"
        ))
        # 更新运行状态
        manager.update_schedule(schedule_id, is_running=False)


@scheduler.command()
@click.option('--lines', '-n', default=50, help='显示的日志行数')
@click.option('--follow', '-f', is_flag=True, help='持续查看日志（类似tail -f）')
@click.option('--filter', help='只显示包含特定文本的日志行')
def logs(lines, follow, filter):
    """查看任务日志。"""
    from puti.scheduler import get_default_log_dir
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    import subprocess
    import os
    from pathlib import Path
    
    console = Console()
    log_dir = get_default_log_dir()
    log_path = log_dir / 'scheduler_beat.log'
    
    # 检查调度器状态
    from puti.scheduler import SchedulerDaemon
    daemon = SchedulerDaemon()
    scheduler_running = daemon.is_running()
    
    # 显示调度器状态信息
    if scheduler_running:
        pid = daemon._get_pid()
        status_text = f"[green]调度器正在运行[/green] (PID: {pid})"
    else:
        status_text = "[yellow]调度器当前未运行[/yellow]"
    
    console.print(Panel(status_text, title="调度器状态", border_style="cyan"))
    
    # 检查日志文件是否存在
    if not log_path.exists():
        console.print(Panel(
            f"[yellow]日志文件不存在: {log_path}[/yellow]\n"
            f"调度器可能尚未启动或日志路径配置有误。\n"
            f"日志目录: {log_dir}\n\n"
            f"请先使用 [bold]puti scheduler start[/bold] 启动调度器。",
            title="未找到日志文件",
            border_style="yellow"
        ))
        return
    
    # 获取日志文件大小和修改时间
    log_size = os.path.getsize(log_path) / 1024  # KB
    log_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(log_path))
    log_age = datetime.datetime.now() - log_mtime
    
    console.print(f"日志文件: [cyan]{log_path}[/cyan]")
    console.print(f"大小: [yellow]{log_size:.2f} KB[/yellow]")
    console.print(f"最后修改: [blue]{log_mtime.strftime('%Y-%m-%d %H:%M:%S')}[/blue] ({log_age.seconds // 60} 分钟前)")
    
    # 使用subprocess显示日志内容
    try:
        # 构建命令
        if filter:
            console.print(f"[cyan]显示最近 {lines} 行日志，过滤条件: '{filter}'[/cyan]")
            if follow:
                cmd = ['tail', '-n', str(lines), '-f', str(log_path)]
                grep_cmd = ['grep', '--color=auto', filter]
                
                # 使用管道组合命令
                p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                p2 = subprocess.Popen(grep_cmd, stdin=p1.stdout)
                
                try:
                    # 等待用户按Ctrl+C中断
                    p2.wait()
                except KeyboardInterrupt:
                    console.print("\n[yellow]日志查看已停止。[/yellow]")
                finally:
                    # 确保子进程被终止
                    try:
                        p1.terminate()
                        p2.terminate()
                    except:
                        pass
            else:
                # 不需要持续跟踪，直接使用grep过滤
                cmd = f"tail -n {lines} {log_path} | grep --color=auto '{filter}'"
                os.system(cmd)
        else:
            if follow:
                console.print(f"[cyan]显示最近 {lines} 行日志并持续更新 (按Ctrl+C停止)[/cyan]")
                subprocess.run(['tail', '-n', str(lines), '-f', str(log_path)], check=True)
            else:
                console.print(f"[cyan]显示最近 {lines} 行日志[/cyan]")
                result = subprocess.run(['tail', '-n', str(lines), str(log_path)], 
                                     capture_output=True, text=True, check=False)
                
                # 使用Syntax高亮显示日志内容
                if result.stdout:
                    syntax = Syntax(result.stdout, "log", theme="monokai", 
                                   line_numbers=True, start_line=1)
                    console.print(syntax)
                else:
                    console.print("[yellow]日志文件为空。[/yellow]")
                
    except KeyboardInterrupt:
        console.print("\n[yellow]日志查看已停止。[/yellow]")
    except Exception as e:
        console.print(f"[red]查看日志时出错: {str(e)}[/red]")
        
    # 显示提示信息
    console.print("\n[dim]提示: 使用 --lines/-n 选项可以指定显示的日志行数[/dim]")
    console.print("[dim]使用 --follow/-f 选项可以持续查看日志更新[/dim]")
    console.print("[dim]使用 --filter 选项可以过滤日志内容[/dim]")


@scheduler.command()
def workers():
    """查看worker状态。"""
    from rich.console import Console
    from rich.panel import Panel
    from rich.status import Status
    from rich.table import Table
    import subprocess
    import sys
    import os
    
    console = Console()
    
    # 确保PUTI_DATA_PATH环境变量已设置
    if 'PUTI_DATA_PATH' not in os.environ:
        from pathlib import Path
        default_path = str(Path.home() / 'puti' / 'data')
        if Path(default_path).exists():
            os.environ['PUTI_DATA_PATH'] = default_path
            console.print(f"[yellow]已自动设置环境变量: PUTI_DATA_PATH={default_path}[/yellow]")
        else:
            parent_path = str(Path.home() / 'puti')
            if Path(parent_path).exists():
                os.environ['PUTI_DATA_PATH'] = parent_path
                console.print(f"[yellow]已自动设置环境变量: PUTI_DATA_PATH={parent_path}[/yellow]")
    
    with Status("[bold cyan]正在检查worker状态...", spinner="dots"):
        try:
            cmd = [sys.executable, "-m", "celery", "-A", "celery_queue.celery_app", "status"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and "celery@" in result.stdout:
                # Worker在线
                table = Table(title="Worker状态", show_header=True)
                table.add_column("节点", style="cyan")
                table.add_column("状态", style="green")
                table.add_column("并发数", style="yellow")
                
                lines = [line for line in result.stdout.splitlines() if line.strip()]
                for line in lines:
                    if "celery@" in line:
                        parts = line.split()
                        node = parts[0] if len(parts) > 0 else "未知"
                        status = "在线" if "OK" in line else "未知"
                        concurrency = "1" # 默认值，状态输出中通常不包含并发数
                        table.add_row(node, status, concurrency)
                
                console.print(table)
                
            else:
                # Worker可能离线
                error_message = result.stderr.strip() if result.stderr else "未收到响应"
                panel = Panel(
                    "[yellow]没有检测到正在运行的worker。[/yellow]\n\n"
                    f"[dim]{error_message}[/dim]\n\n"
                    "要启动worker，请使用:\n"
                    f"[blue]export PUTI_DATA_PATH={os.environ.get('PUTI_DATA_PATH', '$HOME/puti/data')}[/blue]\n"
                    "[blue]python -m celery -A celery_queue.celery_app worker --loglevel=INFO[/blue]",
                    title="Worker状态",
                    border_style="red"
                )
                console.print(panel)
                
        except subprocess.TimeoutExpired:
            console.print("[red]查询worker状态超时，可能是网络问题或Celery服务器未响应。[/red]")
        except Exception as e:
            console.print(f"[red]检查worker状态时出错: {str(e)}[/red]")

    # 检查系统日期是否异常
    import datetime
    current_date = datetime.datetime.now()
    if current_date.year > 2024:
        console.print(Panel(
            f"[red]警告: 系统日期可能不正确: {current_date.strftime('%Y-%m-%d %H:%M:%S')}[/red]\n"
            "不正确的系统日期会导致任务调度和执行出现问题。\n"
            "请考虑修正系统日期后再使用调度器。",
            title="系统日期警告",
            border_style="red"
        ))


@scheduler.command()
def tasks():
    """查看任务执行统计。"""
    from puti.db.base_manager import BaseManager
    from puti.db.model.task.bot_task import TweetSchedule
    from rich.console import Console
    from rich.table import Table
    from celery_queue.celery_app import app
    import time
    
    console = Console()
    
    # Get active schedules
    schedule_manager = BaseManager(model_type=TweetSchedule)
    active_schedules = schedule_manager.get_all(where_clause="enabled = 1")
    
    # Get active tasks from Celery
    try:
        i = app.control.inspect()
        active_tasks = i.active()
        
        # Create active tasks table
        if active_tasks:
            console.print("\n[bold cyan]Currently Executing Tasks:[/bold cyan]")
            active_table = Table()
            active_table.add_column("Worker", style="cyan")
            active_table.add_column("Task ID", style="dim")
            active_table.add_column("Task Name", style="green")
            active_table.add_column("Started", style="magenta")
            active_table.add_column("Runtime", style="blue")
            
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    name = task.get('name', 'Unknown')
                    task_id = task.get('id', 'Unknown')
                    started = time.strftime('%Y-%m-%d %H:%M:%S', 
                                            time.localtime(task.get('time_start', 0)))
                    runtime = f"{task.get('runtime', 0):.2f}s" if 'runtime' in task else 'N/A'
                    
                    active_table.add_row(
                        worker,
                        task_id,
                        name,
                        started,
                        runtime
                    )
            console.print(active_table)
        else:
            console.print("[yellow]No tasks are currently being executed.[/yellow]")
        
        # Create scheduled tasks table
        console.print("\n[bold cyan]Scheduled Tasks:[/bold cyan]")
        schedule_table = Table(title="Tasks scheduled by Celery Beat")
        schedule_table.add_column("ID", style="dim")
        schedule_table.add_column("Name", style="cyan")
        schedule_table.add_column("Cron Schedule", style="green")
        schedule_table.add_column("Next Run", style="magenta")
        schedule_table.add_column("Parameters", style="blue")
        
        for schedule in active_schedules:
            next_run = schedule.next_run.strftime("%Y-%m-%d %H:%M:%S") if schedule.next_run else "Never"
            params_str = ", ".join(f"{k}={v}" for k, v in schedule.params.items()) if schedule.params else "None"
            
            schedule_table.add_row(
                str(schedule.id),
                schedule.name,
                schedule.cron_schedule,
                next_run,
                params_str
            )
        
        console.print(schedule_table)
        
    except Exception as e:
        console.print(f"[red]Error getting task information: {str(e)}[/red]")
        console.print("[yellow]Make sure Celery workers are running.[/yellow]")


@scheduler.command()
@click.option('--activate-tasks', '-a', is_flag=True, help="启动调度器的同时激活所有已启用的任务")
def start(activate_tasks):
    """启动调度器守护进程。"""
    from puti.scheduler import SchedulerDaemon
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm
    import os
    import datetime
    
    console = Console()
    
    # 确保PUTI_DATA_PATH环境变量已设置
    if 'PUTI_DATA_PATH' not in os.environ:
        from pathlib import Path
        default_path = str(Path.home() / 'puti' / 'data')
        if Path(default_path).exists():
            os.environ['PUTI_DATA_PATH'] = default_path
            console.print(f"[yellow]已自动设置环境变量: PUTI_DATA_PATH={default_path}[/yellow]")
        else:
            parent_path = str(Path.home() / 'puti')
            if Path(parent_path).exists():
                os.environ['PUTI_DATA_PATH'] = parent_path
                console.print(f"[yellow]已自动设置环境变量: PUTI_DATA_PATH={parent_path}[/yellow]")
    
    # 检查系统日期是否异常
    current_date = datetime.datetime.now()
    if current_date.year > 2024:
        console.print(Panel(
            f"[red]警告: 系统日期可能不正确: {current_date.strftime('%Y-%m-%d %H:%M:%S')}[/red]\n"
            "不正确的系统日期会导致任务调度和执行出现问题。\n"
            "建议修正系统日期后再使用调度器。",
            title="系统日期警告",
            border_style="red"
        ))
        if not Confirm.ask("系统日期异常，是否仍然继续?", default=False):
            return
    
    daemon = SchedulerDaemon()
    
    # 检查调度器是否已经在运行
    if daemon.is_running():
        console.print(Panel(
            f"调度器已经在运行中 (PID: {daemon._get_pid()})",
            title="[yellow]提示[/yellow]",
            border_style="yellow"
        ))
        return
    
    # 启动调度器
    console.print("[cyan]正在启动调度器...[/cyan]")
    try:
        daemon.start(activate_tasks=activate_tasks)
        
        # 检查启动是否成功
        if daemon.is_running():
            console.print(Panel(
                f"调度器已成功启动 (PID: {daemon._get_pid()})\n"
                f"{'已激活所有启用的任务' if activate_tasks else '仅启动调度器，未激活任务'}",
                title="[green]成功[/green]",
                border_style="green"
            ))
            
            # 提示启动worker
            console.print("\n[yellow]提示: 确保Celery worker已启动，否则任务将无法执行。[/yellow]")
            console.print("启动worker命令: [cyan]python -m celery -A celery_queue.celery_app worker --loglevel=INFO[/cyan]")
        else:
            console.print(Panel(
                "无法确认调度器是否成功启动，请检查系统日志。",
                title="[yellow]警告[/yellow]",
                border_style="yellow"
            ))
    except Exception as e:
        console.print(Panel(
            f"启动调度器时出错: {str(e)}",
            title="[red]错误[/red]",
            border_style="red"
        ))


@scheduler.command()
@click.argument('schedule_id', type=int)
def update_next_run(schedule_id):
    """手动更新任务的下次执行时间。用于修复错误的下次执行时间。"""
    from puti.db.schedule_manager import ScheduleManager
    from rich.console import Console
    from rich.panel import Panel
    from croniter import croniter
    import datetime
    import os
    
    console = Console()
    
    # 确保PUTI_DATA_PATH环境变量已设置
    if 'PUTI_DATA_PATH' not in os.environ:
        from pathlib import Path
        default_path = str(Path.home() / 'puti' / 'data')
        if Path(default_path).exists():
            os.environ['PUTI_DATA_PATH'] = default_path
            console.print(f"[yellow]已自动设置环境变量: PUTI_DATA_PATH={default_path}[/yellow]")
        else:
            parent_path = str(Path.home() / 'puti')
            if Path(parent_path).exists():
                os.environ['PUTI_DATA_PATH'] = parent_path
                console.print(f"[yellow]已自动设置环境变量: PUTI_DATA_PATH={parent_path}[/yellow]")
    
    manager = ScheduleManager()
    
    # 检查任务是否存在
    schedule = manager.get_by_id(schedule_id)
    if not schedule:
        console.print(f"[red]错误: 未找到ID为 {schedule_id} 的任务[/red]")
        return
    
    # 计算下一次执行时间
    now = datetime.datetime.now()
    try:
        next_run = croniter(schedule.cron_schedule, now).get_next(datetime.datetime)
        
        # 显示当前和计算后的下次执行时间
        old_next_run = schedule.next_run.strftime("%Y-%m-%d %H:%M:%S") if schedule.next_run else "未设置"
        new_next_run = next_run.strftime("%Y-%m-%d %H:%M:%S")
        
        console.print(f"当前下次执行时间: [yellow]{old_next_run}[/yellow]")
        console.print(f"计算后的下次执行时间: [green]{new_next_run}[/green]")
        
        # 更新数据库
        result = manager.update_schedule(schedule_id, next_run=next_run)
        if result:
            console.print(Panel(
                f"已成功更新任务 '{schedule.name}' 的下次执行时间\n"
                f"更新前: {old_next_run}\n"
                f"更新后: {new_next_run}",
                title="[green]更新成功[/green]",
                border_style="green"
            ))
        else:
            console.print(Panel(
                "数据库更新失败，请检查数据库连接和权限。",
                title="[red]更新失败[/red]",
                border_style="red"
            ))
    except Exception as e:
        console.print(Panel(
            f"计算下次执行时间出错: {str(e)}\n"
            f"请检查Cron表达式: {schedule.cron_schedule}",
            title="[red]错误[/red]",
            border_style="red"
        ))


@scheduler.command()
def auto_shutdown():
    """检查是否有任务，如果没有则停止调度器。用于自动化管理调度器资源。"""
    from puti.db.schedule_manager import ScheduleManager
    from puti.scheduler import SchedulerDaemon
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    manager = ScheduleManager()
    daemon = SchedulerDaemon()
    
    # 检查调度器是否在运行
    if not daemon.is_running():
        console.print("[yellow]调度器当前未运行。[/yellow]")
        return
    
    # 检查是否有活跃任务或运行中的任务
    active_schedules = manager.get_active_schedules()
    running_schedules = manager.get_running_schedules()
    
    if not active_schedules and not running_schedules:
        console.print("[yellow]没有活跃或运行中的任务，正在停止调度器...[/yellow]")
        daemon.stop()
        console.print("[green]调度器已成功停止。[/green]")
    else:
        active_count = len(active_schedules)
        running_count = len(running_schedules)
        console.print(Panel(
            f"[yellow]调度器仍有任务，无法自动停止[/yellow]\n"
            f"活跃任务数: {active_count}\n"
            f"运行中任务数: {running_count}",
            title="自动停止被取消",
            border_style="yellow"
        ))


# Add the scheduler group to the main CLI
main.add_command(scheduler)

if __name__ == "__main__":
    main()
