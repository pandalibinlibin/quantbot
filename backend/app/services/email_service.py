"""
Email Service - 邮件通知服务
"""

from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EmailResult:
    """邮件发送结果"""

    success: bool
    message: str = ""
    error: str = None


class EmailService:
    """邮件服务"""

    def __init__(self):
        self.smtp_server = getattr(settings, "SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = getattr(settings, "SMTP_PORT", 587)
        self.smtp_user = getattr(settings, "SMTP_USER", "")
        self.smtp_password = getattr(settings, "SMTP_PASSWORD", "")
        self.from_email = getattr(settings, "FROM_EMAIL", self.smtp_user)

    async def send_run_task_notification(
        self, email_data: Dict[str, Any]
    ) -> EmailResult:
        """
        发送Run Signal邮件通知

        功能边界: 只反映Run Signal的结果，不包含backtest信息

        Args:
            email_data: 邮件数据，包含权重变化和投资组合信息

        Returns:
            邮件发送结果
        """
        try:
            # 格式化邮件内容
            subject = f"📊 最新投资组合 ({email_data['timestamp'].strftime('%Y-%m-%d %H:%M')})"
            content = self._format_run_task_email(email_data)

            # 发送邮件
            result = await self._send_email(
                to_email=email_data["user_email"], subject=subject, content=content
            )

            logger.info(f"Run Task邮件发送{'成功' if result.success else '失败'}")
            return result

        except Exception as e:
            logger.error(f"发送Run Task邮件失败: {str(e)}")
            return EmailResult(success=False, error=str(e))

    def _format_run_task_email(self, data: Dict[str, Any]) -> str:
        """
        格式化Run Task邮件内容

        Args:
            data: 邮件数据

        Returns:
            格式化的邮件内容
        """
        content = (
            f"📊 最新投资组合 ({data['timestamp'].strftime('%Y-%m-%d %H:%M')})\n\n"
        )

        # 卖出部分
        if data["sell_changes"]:
            content += "🔴 卖出:\n"
            for etf, change in data["sell_changes"].items():
                content += f"  {etf}: {change['from']:.1f}% → {change['to']:.1f}% ({change['change']:+.1f}%)\n"
            content += "\n"

        # 买入部分
        if data["buy_changes"]:
            content += "🟢 买入:\n"
            for etf, change in data["buy_changes"].items():
                content += f"  {etf}: {change['from']:.1f}% → {change['to']:.1f}% ({change['change']:+.1f}%)\n"
            content += "\n"

        # 如果没有变化
        if not data["sell_changes"] and not data["buy_changes"]:
            content += "📋 投资组合无变化\n\n"

        # 最新持仓 (显示前20只)
        content += "📋 最新持仓比例 (Top 20):\n"
        sorted_portfolio = sorted(
            data["latest_portfolio"].items(), key=lambda x: x[1], reverse=True
        )

        for i, (etf, weight) in enumerate(sorted_portfolio[:20]):
            content += f"  {etf}: {weight:.1f}%\n"

        if len(sorted_portfolio) > 20:
            content += f"  ... (共{len(sorted_portfolio)}只ETF)\n"

        # 统计信息
        total_positions = len(data["latest_portfolio"])
        sell_count = len(data["sell_changes"])
        buy_count = len(data["buy_changes"])
        cash_ratio = data["latest_portfolio"].get("CASH", 0.0)

        content += f"\n📊 统计信息:\n"
        content += f"  总持仓数量: {total_positions}只\n"
        content += f"  买入信号: {buy_count}只\n"
        content += f"  卖出信号: {sell_count}只\n"
        content += f"  现金比例: {cash_ratio:.1f}%\n"

        content += f"\n⏰ 生成时间: {data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += "💡 这是基于最新数据的投资组合权重配置"

        return content

    async def _send_email(
        self, to_email: str, subject: str, content: str
    ) -> EmailResult:
        """
        发送邮件

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            content: 邮件内容

        Returns:
            发送结果
        """
        try:
            # 如果没有配置SMTP，则只记录日志
            if not self.smtp_user or not self.smtp_password:
                logger.info("SMTP未配置，邮件内容:")
                logger.info(f"收件人: {to_email}")
                logger.info(f"主题: {subject}")
                logger.info(f"内容:\n{content}")

                return EmailResult(
                    success=True, message="邮件内容已记录到日志 (SMTP未配置)"
                )

            # 创建邮件
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg["Subject"] = subject

            # 添加邮件内容
            msg.attach(MIMEText(content, "plain", "utf-8"))

            # 发送邮件
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            return EmailResult(success=True, message="邮件发送成功")

        except Exception as e:
            logger.error(f"邮件发送失败: {str(e)}")
            return EmailResult(success=False, error=str(e))


# 全局服务实例
_email_service = None


def get_email_service() -> EmailService:
    """获取邮件服务实例"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
