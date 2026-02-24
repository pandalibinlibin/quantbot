"""
Notification Service for Paper Trading

Handles email notification configuration and sending.
Uses FastAPI Full Stack Template's existing email utilities.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.core.config import settings
from app.utils import send_email

logger = logging.getLogger(__name__)

# Configuration file path
CONFIG_DIR = Path("/app/config")
NOTIFICATION_CONFIG_FILE = CONFIG_DIR / "notification.json"


class NotificationService:
    """Service for managing notification configuration and sending emails."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """Ensure configuration directory exists."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> Dict[str, Any]:
        """Load notification configuration from file."""
        if not NOTIFICATION_CONFIG_FILE.exists():
            return self._get_default_config()

        try:
            with open(NOTIFICATION_CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load notification config: {e}")
            return self._get_default_config()

    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Save notification configuration to file."""
        try:
            with open(NOTIFICATION_CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save notification config: {e}")
            return False

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default notification configuration using FastAPI template settings."""
        return {
            "enabled": False,
            "recipients": [],
            "smtp_host": settings.SMTP_HOST,
            "smtp_port": settings.SMTP_PORT,
            "smtp_user": settings.SMTP_USER,
            "smtp_tls": settings.SMTP_TLS,
            "from_email": settings.EMAILS_FROM_EMAIL,
            "from_name": settings.EMAILS_FROM_NAME,
            "updated_at": None,
        }

    def get_config(self) -> Dict[str, Any]:
        """
        Get current notification configuration.

        Returns:
            Configuration dictionary with enabled status, recipients, etc.
        """
        config = self._load_config()
        # Don't expose SMTP password
        config.pop("smtp_password", None)
        return {
            "success": True,
            "config": config,
        }

    def update_config(
        self,
        enabled: Optional[bool] = None,
        recipients: Optional[List[str]] = None,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_tls: Optional[bool] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update notification configuration.

        Args:
            enabled: Enable/disable notifications
            recipients: List of email recipients
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password (stored securely)
            smtp_tls: Use TLS
            from_email: Sender email address
            from_name: Sender name

        Returns:
            Updated configuration
        """
        config = self._load_config()

        if enabled is not None:
            config["enabled"] = enabled
        if recipients is not None:
            # Validate email format
            valid_recipients = [r.strip() for r in recipients if "@" in r and "." in r]
            config["recipients"] = valid_recipients
        if smtp_host is not None:
            config["smtp_host"] = smtp_host
        if smtp_port is not None:
            config["smtp_port"] = smtp_port
        if smtp_user is not None:
            config["smtp_user"] = smtp_user
        if smtp_password is not None:
            config["smtp_password"] = smtp_password
        if smtp_tls is not None:
            config["smtp_tls"] = smtp_tls
        if from_email is not None:
            config["from_email"] = from_email
        if from_name is not None:
            config["from_name"] = from_name

        config["updated_at"] = datetime.now().isoformat()

        if self._save_config(config):
            # Don't expose password in response
            response_config = config.copy()
            response_config.pop("smtp_password", None)
            return {
                "success": True,
                "message": "Configuration updated successfully",
                "config": response_config,
            }
        else:
            return {
                "success": False,
                "error": "Failed to save configuration",
            }

    def add_recipient(self, email: str) -> Dict[str, Any]:
        """Add a recipient email address."""
        if "@" not in email or "." not in email:
            return {
                "success": False,
                "error": "Invalid email format",
            }

        config = self._load_config()
        email = email.strip().lower()

        if email in config["recipients"]:
            return {
                "success": False,
                "error": "Email already exists",
            }

        config["recipients"].append(email)
        config["updated_at"] = datetime.now().isoformat()

        if self._save_config(config):
            return {
                "success": True,
                "message": f"Added {email}",
                "recipients": config["recipients"],
            }
        else:
            return {
                "success": False,
                "error": "Failed to save configuration",
            }

    def remove_recipient(self, email: str) -> Dict[str, Any]:
        """Remove a recipient email address."""
        config = self._load_config()
        email = email.strip().lower()

        if email not in config["recipients"]:
            return {
                "success": False,
                "error": "Email not found",
            }

        config["recipients"].remove(email)
        config["updated_at"] = datetime.now().isoformat()

        if self._save_config(config):
            return {
                "success": True,
                "message": f"Removed {email}",
                "recipients": config["recipients"],
            }
        else:
            return {
                "success": False,
                "error": "Failed to save configuration",
            }

    def send_test_email(self, recipient: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a test email to verify configuration.
        Uses FastAPI template's send_email utility.

        Args:
            recipient: Optional specific recipient (uses first configured if not provided)

        Returns:
            Result of sending test email
        """
        # Check if emails are enabled in settings
        if not settings.emails_enabled:
            return {
                "success": False,
                "error": "Email sending is not configured. Check SMTP settings.",
            }

        config = self._load_config()

        # Determine recipient
        if recipient:
            to_email = recipient
        elif config.get("recipients"):
            to_email = config["recipients"][0]
        else:
            return {
                "success": False,
                "error": "No recipient specified or configured",
            }

        try:
            # Build HTML content
            html_content = f"""
            <html>
            <body>
            <h2>QuantBot Notification Test</h2>
            <p>This is a test email from QuantBot Paper Trading system.</p>
            <p>If you received this email, your notification configuration is working correctly.</p>
            <hr>
            <p><small>Sent at: {datetime.now().isoformat()}</small></p>
            </body>
            </html>
            """

            # Use FastAPI template's send_email function
            send_email(
                email_to=to_email,
                subject=f"{settings.PROJECT_NAME} - Test Email",
                html_content=html_content,
            )

            return {
                "success": True,
                "message": f"Test email sent to {to_email}",
            }

        except AssertionError as e:
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            self.logger.error(f"Failed to send test email: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def send_trading_report(
        self,
        subject: str,
        report_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send trading report email to all configured recipients.
        Uses FastAPI template's send_email utility.

        Args:
            subject: Email subject
            report_data: Trading report data to include

        Returns:
            Result of sending emails
        """
        # Check if emails are enabled in settings
        if not settings.emails_enabled:
            return {
                "success": False,
                "error": "Email sending is not configured. Check SMTP settings.",
            }

        config = self._load_config()

        if not config.get("enabled"):
            return {
                "success": False,
                "error": "Notifications are disabled",
            }

        if not config.get("recipients"):
            return {
                "success": False,
                "error": "No recipients configured",
            }

        # Build email body
        html_content = self._build_trading_report_html(report_data)

        sent_count = 0
        errors = []

        for recipient in config["recipients"]:
            try:
                send_email(
                    email_to=recipient,
                    subject=f"{settings.PROJECT_NAME} - {subject}",
                    html_content=html_content,
                )
                sent_count += 1
            except Exception as e:
                errors.append(f"{recipient}: {str(e)}")

        if sent_count == len(config["recipients"]):
            return {
                "success": True,
                "message": f"Report sent to {sent_count} recipients",
            }
        elif sent_count > 0:
            return {
                "success": True,
                "message": f"Report sent to {sent_count}/{len(config['recipients'])} recipients",
                "errors": errors,
            }
        else:
            return {
                "success": False,
                "error": "Failed to send to any recipients",
                "errors": errors,
            }

    def send_trading_plan_email(self, trading_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send trading plan email after execution.

        Args:
            trading_plan: Trading plan data including sells, buys, and execution results

        Returns:
            Result of sending emails
        """
        # Check if emails are enabled in settings
        if not settings.emails_enabled:
            return {
                "success": False,
                "error": "Email sending is not configured.",
            }

        config = self._load_config()

        if not config.get("enabled"):
            return {
                "success": False,
                "error": "Notifications are disabled",
            }

        if not config.get("recipients"):
            return {
                "success": False,
                "error": "No recipients configured",
            }

        # Build email content
        html_content = self._build_trading_plan_html(trading_plan)
        date = trading_plan.get("date", datetime.now().strftime("%Y-%m-%d"))

        sent_count = 0
        errors = []

        for recipient in config["recipients"]:
            try:
                send_email(
                    email_to=recipient,
                    subject=f"QuantBot: Trading Plan {date}",
                    html_content=html_content,
                )
                sent_count += 1
            except Exception as e:
                errors.append(f"{recipient}: {str(e)}")

        if sent_count == len(config["recipients"]):
            return {
                "success": True,
                "message": f"Trading plan sent to {sent_count} recipients",
            }
        elif sent_count > 0:
            return {
                "success": True,
                "message": f"Trading plan sent to {sent_count}/{len(config['recipients'])} recipients",
                "errors": errors,
            }
        else:
            return {
                "success": False,
                "error": "Failed to send to any recipients",
                "errors": errors,
            }

    def _build_trading_plan_html(self, trading_plan: Dict[str, Any]) -> str:
        """Build HTML email body for trading plan."""
        date = trading_plan.get("date", datetime.now().strftime("%Y-%m-%d"))
        strategy = trading_plan.get("strategy", "TopkDropout")

        # Get execution results
        sells_executed = trading_plan.get("sells_executed", 0)
        buys_executed = trading_plan.get("buys_executed", 0)

        # Get portfolio info
        portfolio = trading_plan.get("portfolio", {})
        total_value = portfolio.get("total_value", 0)
        cash = portfolio.get("cash", 0)

        # Build sell orders table
        sell_orders = trading_plan.get("sell_orders", [])
        sell_rows = ""
        for order in sell_orders:
            sell_rows += f"""
            <tr>
                <td>{order.get('instrument', '')}</td>
                <td>{order.get('sell_pct', 0):.1%}</td>
                <td>¥{order.get('reference_price', 0):,.2f}</td>
                <td>{order.get('reason', '')}</td>
            </tr>
            """

        # Build buy orders table
        buy_orders = trading_plan.get("buy_orders", [])
        buy_rows = ""
        for order in buy_orders:
            # target_weight is already in percentage (e.g., 2.0 means 2%)
            target_weight = order.get("target_weight", 0)
            buy_rows += f"""
            <tr>
                <td>{order.get('instrument', '')}</td>
                <td>{target_weight:.2f}%</td>
                <td>¥{order.get('reference_price', 0):,.2f}</td>
                <td>{order.get('score', 0):.4f}</td>
            </tr>
            """

        return f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h2 {{ color: #333; }}
                h3 {{ color: #666; margin-top: 20px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .summary {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .sell {{ color: #e74c3c; }}
                .buy {{ color: #27ae60; }}
            </style>
        </head>
        <body>
            <h2>📊 QuantBot Trading Plan</h2>
            <p><strong>Date:</strong> {date} | <strong>Strategy:</strong> {strategy}</p>
            
            <div class="summary">
                <h3>📈 Execution Summary</h3>
                <p>
                    <span class="sell">Sells Executed: {sells_executed}</span> | 
                    <span class="buy">Buys Executed: {buys_executed}</span>
                </p>
                <p>
                    Portfolio Value: <strong>¥{total_value:,.2f}</strong> | 
                    Cash: ¥{cash:,.2f}
                </p>
            </div>
            
            <h3 class="sell">📉 Sell Orders ({len(sell_orders)})</h3>
            {f'''
            <table>
                <tr>
                    <th>Stock</th>
                    <th>Sell %</th>
                    <th>Ref Price</th>
                    <th>Reason</th>
                </tr>
                {sell_rows}
            </table>
            ''' if sell_orders else '<p>No sell orders</p>'}
            
            <h3 class="buy">📈 Buy Orders ({len(buy_orders)})</h3>
            {f'''
            <table>
                <tr>
                    <th>Stock</th>
                    <th>Target Weight</th>
                    <th>Ref Price</th>
                    <th>Score</th>
                </tr>
                {buy_rows}
            </table>
            ''' if buy_orders else '<p>No buy orders</p>'}
            
            <hr>
            <p><small>This is an automated email from QuantBot Paper Trading system.</small></p>
        </body>
        </html>
        """

    def _build_trading_report_html(self, report_data: Dict[str, Any]) -> str:
        """Build HTML email body for trading report."""
        date = report_data.get("date", datetime.now().strftime("%Y-%m-%d"))
        sells = report_data.get("sells_executed", 0)
        buys = report_data.get("buys_executed", 0)
        total_value = report_data.get("total_value", 0)
        total_return = report_data.get("total_return", 0)

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
        <h2>QuantBot Daily Trading Report</h2>
        <p><strong>Date:</strong> {date}</p>

        <h3>Trading Summary</h3>
        <table border="1" cellpadding="8" cellspacing="0">
            <tr><td>Sells Executed</td><td>{sells}</td></tr>
            <tr><td>Buys Executed</td><td>{buys}</td></tr>
            <tr><td>Portfolio Value</td><td>¥{total_value:,.2f}</td></tr>
            <tr><td>Total Return</td><td>{total_return:.2%}</td></tr>
        </table>

        <hr>
        <p><small>This is an automated email from QuantBot Paper Trading system.</small></p>
        </body>
        </html>
        """


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get or create notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
