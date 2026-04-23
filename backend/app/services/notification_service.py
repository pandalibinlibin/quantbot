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
        # Default recipients: use EMAILS_FROM_EMAIL if available
        default_recipients = []
        if settings.EMAILS_FROM_EMAIL:
            default_recipients = [settings.EMAILS_FROM_EMAIL]

        return {
            "enabled": settings.emails_enabled,  # Auto-enable if SMTP is configured
            "recipients": default_recipients,
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
                    subject=subject,
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
            <div style="background-color: #fef3c7; border: 1px solid #f59e0b; border-radius: 6px; padding: 12px; margin: 16px 0;">
                <p style="margin: 0; font-size: 12px; color: #92400e;">
                    <strong>⚠️ 免责声明 / Disclaimer</strong><br>
                    本邮件内容仅供学习交流和技术研究使用，不构成任何投资建议。投资有风险，入市需谨慎。请根据自身情况独立判断，本系统及开发者不对任何投资决策承担责任。<br>
                    <em>This email is for educational and research purposes only and does not constitute investment advice.</em>
                </p>
            </div>
            <p><small>This is an automated email from QuantBot Paper Trading system.</small></p>
        </body>
        </html>
        """

    def send_target_portfolio_email(
        self,
        portfolio_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send target portfolio email after routine execution.

        Args:
            portfolio_data: Target portfolio data including:
                - target_portfolio: List of portfolio items
                - summary: Portfolio summary statistics

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
        html_content = self._build_target_portfolio_html(portfolio_data)
        summary = portfolio_data.get("summary", {})
        date = summary.get("target_date", datetime.now().strftime("%Y-%m-%d"))

        sent_count = 0
        errors = []

        for recipient in config["recipients"]:
            try:
                send_email(
                    email_to=recipient,
                    subject=f"QuantBot: Target Portfolio {date}",
                    html_content=html_content,
                )
                sent_count += 1
            except Exception as e:
                errors.append(f"{recipient}: {str(e)}")

        if sent_count == len(config["recipients"]):
            return {
                "success": True,
                "message": f"Target portfolio sent to {sent_count} recipients",
            }
        elif sent_count > 0:
            return {
                "success": True,
                "message": f"Target portfolio sent to {sent_count}/{len(config['recipients'])} recipients",
                "errors": errors,
            }
        else:
            return {
                "success": False,
                "error": "Failed to send to any recipients",
                "errors": errors,
            }

    def _build_target_portfolio_html(self, portfolio_data: Dict[str, Any]) -> str:
        """Build HTML email body for target portfolio."""
        summary = portfolio_data.get("summary", {})
        portfolio = portfolio_data.get("target_portfolio", [])

        benchmark = summary.get("benchmark", "unknown")
        benchmark_name = summary.get("benchmark_name", benchmark)
        generated_at = summary.get("generated_at", datetime.now().isoformat())
        target_date = summary.get("target_date", datetime.now().strftime("%Y-%m-%d"))
        total_stocks = summary.get("total_stocks", 0)
        overweight_count = summary.get("overweight_count", 0)
        underweight_count = summary.get("underweight_count", 0)
        neutral_count = summary.get("neutral_count", 0)
        max_deviation = summary.get("max_deviation", 0.02)

        # Build portfolio table rows (all stocks)
        portfolio_rows = ""
        for item in portfolio:
            deviation = item.get("deviation", 0)
            action = item.get("action", "")

            # Color coding for deviation
            if action == "超配":
                color = "#27ae60"  # Green
            elif action == "低配":
                color = "#e74c3c"  # Red
            else:
                color = "#666"  # Gray

            portfolio_rows += f"""
            <tr>
                <td style="text-align: center;">{item.get('rank', '')}</td>
                <td>{item.get('instrument', '')}</td>
                <td style="text-align: right;">{item.get('benchmark_weight', 0):.2%}</td>
                <td style="text-align: right;">{item.get('score', 0):.4f}</td>
                <td style="text-align: right;">{item.get('target_weight', 0):.2%}</td>
                <td style="text-align: right; color: {color};">{item.get('deviation_pct', '')}</td>
                <td style="text-align: center; color: {color};">{action}</td>
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
                th, td {{ border: 1px solid #ddd; padding: 8px; }}
                th {{ background-color: #2c3e50; color: white; text-align: left; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                tr:hover {{ background-color: #f5f5f5; }}
                .info-box {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 15px 0; }}
                .stat-item {{ background-color: #fff; padding: 10px; border-radius: 5px; border: 1px solid #ddd; text-align: center; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
                .stat-label {{ font-size: 12px; color: #666; }}
                .overweight {{ color: #27ae60; }}
                .underweight {{ color: #e74c3c; }}
            </style>
        </head>
        <body>
            <h2>📊 QuantBot Target Portfolio</h2>
            
            <div class="info-box">
                <p><strong>Benchmark:</strong> {benchmark_name} ({benchmark})</p>
                <p><strong>Target Date:</strong> {target_date}</p>
                <p><strong>Generated At:</strong> {generated_at}</p>
                <p><strong>Max Deviation:</strong> {max_deviation:.1%}</p>
            </div>
            
            <h3>📈 Statistics</h3>
            <table style="width: 50%;">
                <tr>
                    <td>Total Stocks</td>
                    <td style="text-align: right;"><strong>{total_stocks}</strong></td>
                </tr>
                <tr>
                    <td>Overweight (<span class="overweight">超配</span>)</td>
                    <td style="text-align: right;"><strong class="overweight">{overweight_count}</strong></td>
                </tr>
                <tr>
                    <td>Underweight (<span class="underweight">低配</span>)</td>
                    <td style="text-align: right;"><strong class="underweight">{underweight_count}</strong></td>
                </tr>
                <tr>
                    <td>Neutral (持平)</td>
                    <td style="text-align: right;"><strong>{neutral_count}</strong></td>
                </tr>
            </table>
            
            <h3>📋 Target Portfolio</h3>
            <table>
                <tr>
                    <th style="width: 50px;">Rank</th>
                    <th>Stock</th>
                    <th style="width: 100px;">Benchmark</th>
                    <th style="width: 80px;">Score</th>
                    <th style="width: 100px;">Target</th>
                    <th style="width: 80px;">Deviation</th>
                    <th style="width: 80px;">Action</th>
                </tr>
                {portfolio_rows}
            </table>
            
            
            <hr>
            <div style="background-color: #fef3c7; border: 1px solid #f59e0b; border-radius: 6px; padding: 12px; margin: 16px 0;">
                <p style="margin: 0; font-size: 12px; color: #92400e;">
                    <strong>⚠️ 免责声明 / Disclaimer</strong><br>
                    本邮件内容仅供学习交流和技术研究使用，不构成任何投资建议。投资有风险，入市需谨慎。请根据自身情况独立判断，本系统及开发者不对任何投资决策承担责任。<br>
                    <em>This email is for educational and research purposes only and does not constitute investment advice.</em>
                </p>
            </div>
            <p><small>This is an automated email from QuantBot Enhanced Indexing system.</small></p>
        </body>
        </html>
        """

    def send_etf_enhanced_portfolio_email(
        self,
        portfolio_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send ETF Enhanced Indexing portfolio email after routine execution.

        Args:
            portfolio_data: ETF enhanced portfolio data including:
                - positions: List of positions (ETF + alpha stocks)
                - weights: ETF/Alpha weight distribution
                - summary: Portfolio summary statistics

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
        html_content = self._build_etf_enhanced_portfolio_html(portfolio_data)
        signal_for_date = portfolio_data.get(
            "signal_for_date", datetime.now().strftime("%Y-%m-%d")
        )

        sent_count = 0
        errors = []

        for recipient in config["recipients"]:
            try:
                send_email(
                    email_to=recipient,
                    subject=f"QuantBot: 交易信号 {signal_for_date}",
                    html_content=html_content,
                )
                sent_count += 1
            except Exception as e:
                errors.append(f"{recipient}: {str(e)}")

        if sent_count == len(config["recipients"]):
            return {
                "success": True,
                "message": f"ETF enhanced portfolio sent to {sent_count} recipients",
            }
        elif sent_count > 0:
            return {
                "success": True,
                "message": f"ETF enhanced portfolio sent to {sent_count}/{len(config['recipients'])} recipients",
                "errors": errors,
            }
        else:
            return {
                "success": False,
                "error": "Failed to send to any recipients",
                "errors": errors,
            }

    def _build_etf_enhanced_portfolio_html(self, portfolio_data: Dict[str, Any]) -> str:
        """Build HTML email body for ETF Enhanced Indexing portfolio - optimized for traders."""
        generated_at = portfolio_data.get("generated_at", datetime.now().isoformat())
        trade_date = portfolio_data.get("trade_date", "")
        signal_for_date = portfolio_data.get("signal_for_date", "")
        total_value = portfolio_data.get("total_value", 1000000)
        region = portfolio_data.get("region", "cn")
        lot_size = portfolio_data.get("lot_size", 100)

        # Weights info
        weights = portfolio_data.get("weights", {})
        etf_weight = weights.get("etf_weight", 0.65)
        alpha_weight = weights.get("alpha_weight", 0.35)
        score_spread = weights.get("score_spread", 0)
        weight_mode = weights.get("weight_mode", "dynamic")

        # Summary
        summary = portfolio_data.get("summary", {})
        total_positions = summary.get("total_positions", 0)
        buy_count = summary.get("buy_count", 0)
        sell_count = summary.get("sell_count", 0)
        hold_count = summary.get("hold_count", 0)

        # Positions
        positions = portfolio_data.get("positions", [])

        # Separate by action type for trader convenience
        buy_positions = [p for p in positions if p.get("action") == "buy"]
        sell_positions = [p for p in positions if p.get("action") == "sell"]
        hold_positions = [p for p in positions if p.get("action") == "hold"]

        # Market info
        market_name = "A股" if region == "cn" else "美股"

        # Build quick action summary for traders (most important section)
        def build_action_row(pos):
            pos_type = "ETF" if pos.get("type") == "etf" else "股票"
            return f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 12px 8px;"><strong style="font-size: 16px;">{pos.get('symbol', '')}</strong></td>
                <td style="padding: 12px 8px;">{pos.get('name', '')}</td>
                <td style="padding: 12px 8px; text-align: center;"><span style="background: #f0f0f0; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{pos_type}</span></td>
                <td style="padding: 12px 8px; text-align: right; font-size: 16px;"><strong>¥{pos.get('reference_price', 0):,.3f}</strong></td>
                <td style="padding: 12px 8px; text-align: right; font-size: 18px; font-weight: bold; color: #1a237e;">{pos.get('action_lots', 0):,} 手</td>
                <td style="padding: 12px 8px; text-align: right; color: #666;">{pos.get('action_shares', 0):,} 股</td>
                <td style="padding: 12px 8px; text-align: right;">¥{pos.get('target_value', 0):,.0f}</td>
            </tr>
            """

        buy_rows = "".join([build_action_row(p) for p in buy_positions])
        sell_rows = "".join([build_action_row(p) for p in sell_positions])
        hold_rows = "".join([build_action_row(p) for p in hold_positions])

        # Build detailed positions table - shows holdings AFTER executing orders
        def build_detail_row(pos):
            pos_type = "ETF" if pos.get("type") == "etf" else "股票"
            score = pos.get("score", 0)
            score_str = f"{score:.4f}" if score else "-"
            return f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 8px; text-align: center;">{pos.get('rank', '-')}</td>
                <td style="padding: 8px;"><strong>{pos.get('symbol', '')}</strong></td>
                <td style="padding: 8px;">{pos.get('name', '')}</td>
                <td style="padding: 8px; text-align: center;"><small>{pos_type}</small></td>
                <td style="padding: 8px; text-align: right;">{pos.get('weight', 0):.2%}</td>
                <td style="padding: 8px; text-align: right;">{score_str}</td>
                <td style="padding: 8px; text-align: right;">¥{pos.get('reference_price', 0):,.3f}</td>
                <td style="padding: 8px; text-align: right;">{pos.get('target_shares', 0):,}</td>
                <td style="padding: 8px; text-align: right;">¥{pos.get('target_value', 0):,.0f}</td>
            </tr>
            """

        # Only include positions with holdings (target_shares > 0)
        holdings_only = [p for p in positions if p.get("target_shares", 0) > 0]
        detail_rows = "".join([build_detail_row(p) for p in holdings_only])

        return f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Microsoft YaHei', 'PingFang SC', Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 1000px; margin: 0 auto; background-color: white; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; }}
                .header {{ background: linear-gradient(135deg, #1a237e 0%, #3949ab 100%); color: white; padding: 25px 30px; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .header .subtitle {{ opacity: 0.9; margin-top: 8px; font-size: 14px; }}
                .section {{ padding: 20px 30px; }}
                .section-title {{ font-size: 18px; font-weight: bold; color: #333; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #1a237e; }}
                
                /* Quick Stats */
                .stats-grid {{ display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 20px; }}
                .stat-box {{ flex: 1; min-width: 120px; background: #f8f9fa; border-radius: 8px; padding: 15px; text-align: center; }}
                .stat-value {{ font-size: 28px; font-weight: bold; color: #1a237e; }}
                .stat-label {{ font-size: 12px; color: #666; margin-top: 5px; }}
                .stat-box.buy {{ background: #e8f5e9; }}
                .stat-box.buy .stat-value {{ color: #27ae60; }}
                .stat-box.sell {{ background: #ffebee; }}
                .stat-box.sell .stat-value {{ color: #e74c3c; }}
                
                /* Action Tables */
                .action-section {{ margin-bottom: 25px; }}
                .action-header {{ padding: 12px 15px; border-radius: 8px 8px 0 0; font-weight: bold; font-size: 16px; }}
                .action-header.buy {{ background: #27ae60; color: white; }}
                .action-header.sell {{ background: #e74c3c; color: white; }}
                .action-header.hold {{ background: #95a5a6; color: white; }}
                .action-table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #ddd; border-top: none; }}
                .action-table th {{ background: #f8f9fa; padding: 10px 8px; text-align: left; font-size: 12px; color: #666; border-bottom: 1px solid #ddd; }}
                .action-table td {{ padding: 12px 8px; }}
                
                /* Detail Table */
                .detail-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
                .detail-table th {{ background: #1a237e; color: white; padding: 10px 8px; text-align: left; font-size: 11px; }}
                .detail-table tr:hover {{ background: #f5f5f5; }}
                
                /* Footer */
                .footer {{ background: #f8f9fa; padding: 15px 30px; font-size: 12px; color: #888; border-top: 1px solid #eee; }}
                
                /* Print optimization */
                @media print {{
                    body {{ background: white; }}
                    .container {{ box-shadow: none; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- Header -->
                <div class="header">
                    <h1>📊 QuantBot 交易信号</h1>
                    <div class="subtitle">
                        信号日期：<strong>{signal_for_date}</strong> | 
                        交易日期：{trade_date} | 
                        市场：{market_name} | 
                        总资产：¥{total_value:,.0f}
                    </div>
                </div>
                
                <!-- Quick Stats -->
                <div class="section">
                    <div class="stats-grid">
                        <div class="stat-box">
                            <div class="stat-value">{etf_weight:.0%}</div>
                            <div class="stat-label">ETF权重</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">{alpha_weight:.0%}</div>
                            <div class="stat-label">Alpha权重</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">{score_spread:.2f}</div>
                            <div class="stat-label">分数离散度</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">{total_positions}</div>
                            <div class="stat-label">总持仓</div>
                        </div>
                        <div class="stat-box buy">
                            <div class="stat-value">{buy_count}</div>
                            <div class="stat-label">买入</div>
                        </div>
                        <div class="stat-box sell">
                            <div class="stat-value">{sell_count}</div>
                            <div class="stat-label">卖出</div>
                        </div>
                    </div>
                </div>
                
                <!-- Trading Actions (Most Important for Traders) -->
                <div class="section" style="background: #fafafa;">
                    <div class="section-title">🎯 今日交易指令</div>
                    
                    {"" if not buy_positions else f'''
                    <div class="action-section">
                        <div class="action-header buy">🟢 买入 ({len(buy_positions)})</div>
                        <table class="action-table">
                            <thead>
                                <tr>
                                    <th style="width: 100px;">代码</th>
                                    <th>名称</th>
                                    <th style="width: 60px;">类型</th>
                                    <th style="width: 90px; text-align: right;">参考价</th>
                                    <th style="width: 80px; text-align: right;">买入手数</th>
                                    <th style="width: 80px; text-align: right;">买入股数</th>
                                    <th style="width: 100px; text-align: right;">目标金额</th>
                                </tr>
                            </thead>
                            <tbody>
                                {buy_rows}
                            </tbody>
                        </table>
                    </div>
                    '''}
                    
                    {"" if not sell_positions else f'''
                    <div class="action-section">
                        <div class="action-header sell">🔴 卖出 ({len(sell_positions)})</div>
                        <table class="action-table">
                            <thead>
                                <tr>
                                    <th style="width: 100px;">代码</th>
                                    <th>名称</th>
                                    <th style="width: 60px;">类型</th>
                                    <th style="width: 90px; text-align: right;">参考价</th>
                                    <th style="width: 80px; text-align: right;">卖出手数</th>
                                    <th style="width: 80px; text-align: right;">卖出股数</th>
                                    <th style="width: 100px; text-align: right;">目标金额</th>
                                </tr>
                            </thead>
                            <tbody>
                                {sell_rows}
                            </tbody>
                        </table>
                    </div>
                    '''}
                    
                    {"" if not hold_positions else f'''
                    <div class="action-section">
                        <div class="action-header hold">⚪ 持有 ({len(hold_positions)})</div>
                        <table class="action-table">
                            <thead>
                                <tr>
                                    <th style="width: 100px;">代码</th>
                                    <th>名称</th>
                                    <th style="width: 60px;">类型</th>
                                    <th style="width: 90px; text-align: right;">参考价</th>
                                    <th style="width: 80px; text-align: right;">调整手数</th>
                                    <th style="width: 80px; text-align: right;">调整股数</th>
                                    <th style="width: 100px; text-align: right;">目标金额</th>
                                </tr>
                            </thead>
                            <tbody>
                                {hold_rows}
                            </tbody>
                        </table>
                    </div>
                    '''}
                </div>
                
                <!-- Detailed Portfolio - Holdings AFTER executing orders -->
                <div class="section">
                    <div class="section-title">📋 完整持仓明细（执行指令后）</div>
                    <table class="detail-table">
                        <thead>
                            <tr>
                                <th style="width: 40px;">排名</th>
                                <th style="width: 90px;">代码</th>
                                <th>名称</th>
                                <th style="width: 50px;">类型</th>
                                <th style="width: 55px; text-align: right;">权重</th>
                                <th style="width: 65px; text-align: right;">分数</th>
                                <th style="width: 75px; text-align: right;">参考价</th>
                                <th style="width: 70px; text-align: right;">持股数</th>
                                <th style="width: 85px; text-align: right;">市值</th>
                            </tr>
                        </thead>
                        <tbody>
                            {detail_rows}
                        </tbody>
                    </table>
                </div>
                
                <!-- Disclaimer -->
                <div style="background-color: #fef3c7; border: 1px solid #f59e0b; border-radius: 6px; padding: 12px; margin: 16px 0;">
                    <p style="margin: 0; font-size: 12px; color: #92400e;">
                        <strong>⚠️ 免责声明 / Disclaimer</strong><br>
                        本邮件内容仅供学习交流和技术研究使用，不构成任何投资建议。投资有风险，入市需谨慎。请根据自身情况独立判断，本系统及开发者不对任何投资决策承担责任。<br>
                        <em>This email is for educational and research purposes only and does not constitute investment advice.</em>
                    </p>
                </div>

                <!-- Footer -->
                <div class="footer">
                    <strong>策略说明：</strong>ETF增强指数策略 | 权重模式：{weight_mode} | 交易单位：{lot_size}股/手<br>
                    <strong>生成时间：</strong>{generated_at}<br>
                    <em>此邮件由 QuantBot 系统自动发送，请勿直接回复。</em>
                </div>
            </div>
        </body>
        </html>
        """

    def _build_trading_report_html(self, report_data: Dict[str, Any]) -> str:
        """Build HTML email body for trading report with target portfolio."""
        target_date = report_data.get(
            "target_date", datetime.now().strftime("%Y-%m-%d")
        )
        executed_at = report_data.get("executed_at", "")
        signal_count = report_data.get("signal_count", 0)
        total_duration = report_data.get("total_duration_seconds", 0)

        # Portfolio summary
        portfolio_summary = report_data.get("portfolio_summary", {})
        benchmark_name = portfolio_summary.get("benchmark_name", "Enhanced Indexing")
        total_stocks = portfolio_summary.get("total_stocks", 0)
        overweight_count = portfolio_summary.get("overweight_count", 0)
        underweight_count = portfolio_summary.get("underweight_count", 0)
        neutral_count = portfolio_summary.get("neutral_count", 0)

        # Build target portfolio table (all stocks, sorted by rank)
        target_portfolio = report_data.get("target_portfolio", [])
        portfolio_rows = ""

        # Sort by rank and include all stocks
        sorted_portfolio = sorted(target_portfolio, key=lambda x: x.get("rank", 999))

        for item in sorted_portfolio:
            deviation = item.get("deviation", 0)
            deviation_pct = item.get("deviation_pct", "0%")
            if deviation > 0:
                color = "green"
            elif deviation < 0:
                color = "red"
            else:
                color = "#666"
            portfolio_rows += f"""
            <tr>
                <td style="text-align:center">{item.get('rank', '')}</td>
                <td>{item.get('instrument', '')}</td>
                <td style="text-align:right">{item.get('score', 0):.4f}</td>
                <td style="text-align:right">{item.get('benchmark_weight', 0):.2%}</td>
                <td style="text-align:right">{item.get('target_weight', 0):.2%}</td>
                <td style="text-align:right;color:{color}">{deviation_pct}</td>
                <td style="text-align:center">{item.get('action', '')}</td>
            </tr>
            """

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
        <h2 style="color: #333;">QuantBot Daily Report</h2>
        <p><strong>Target Date:</strong> {target_date}</p>
        <p><strong>Executed At:</strong> {executed_at}</p>
        <p><strong>Duration:</strong> {total_duration:.1f}s</p>

        <h3 style="color: #555;">Portfolio Summary</h3>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f5f5f5;">
                <td><strong>Benchmark</strong></td>
                <td>{benchmark_name}</td>
            </tr>
            <tr>
                <td><strong>Total Stocks</strong></td>
                <td>{total_stocks}</td>
            </tr>
            <tr>
                <td><strong>Overweight</strong></td>
                <td style="color: green;">{overweight_count}</td>
            </tr>
            <tr>
                <td><strong>Underweight</strong></td>
                <td style="color: red;">{underweight_count}</td>
            </tr>
            <tr>
                <td><strong>Neutral</strong></td>
                <td>{neutral_count}</td>
            </tr>
        </table>

        <h3 style="color: #555;">Target Portfolio (Top Deviations)</h3>
        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 12px;">
            <thead style="background-color: #f5f5f5;">
                <tr>
                    <th>Rank</th>
                    <th>Instrument</th>
                    <th>Score</th>
                    <th>Bench Wt</th>
                    <th>Target Wt</th>
                    <th>Deviation</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {portfolio_rows}
            </tbody>
        </table>
        <p style="color: #888; font-size: 11px;">Showing all {total_stocks} positions in the target portfolio.</p>

        <hr>
        <div style="background-color: #fef3c7; border: 1px solid #f59e0b; border-radius: 6px; padding: 12px; margin: 16px 0;">
            <p style="margin: 0; font-size: 12px; color: #92400e;">
                <strong>⚠️ 免责声明 / Disclaimer</strong><br>
                本邮件内容仅供学习交流和技术研究使用，不构成任何投资建议。投资有风险，入市需谨慎。请根据自身情况独立判断，本系统及开发者不对任何投资决策承担责任。<br>
                <em>This email is for educational and research purposes only and does not constitute investment advice.</em>
            </p>
        </div>
        <p><small style="color: #888;">This is an automated email from QuantBot Enhanced Indexing system.</small></p>
        </body>
        </html>
        """

    def send_topk_portfolio_email(
        self,
        portfolio_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send TopK Strategy portfolio email after routine execution.

        Args:
            portfolio_data: TopK portfolio data including:
                - buy_positions: List of stocks to buy
                - sell_positions: List of stocks to sell
                - hold_positions: List of stocks to hold
                - final_positions: Complete portfolio (30 stocks)
                - summary: Portfolio summary statistics

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
        html_content = self._build_topk_portfolio_html(portfolio_data)
        signal_for_date = portfolio_data.get(
            "signal_for_date", datetime.now().strftime("%Y-%m-%d")
        )

        sent_count = 0
        errors = []

        for recipient in config["recipients"]:
            try:
                send_email(
                    email_to=recipient,
                    subject=f"QuantBot: Target Portfolio {signal_for_date}",
                    html_content=html_content,
                )
                sent_count += 1
            except Exception as e:
                errors.append(f"{recipient}: {str(e)}")

        if sent_count == len(config["recipients"]):
            return {
                "success": True,
                "message": f"TopK portfolio sent to {sent_count} recipients",
            }
        elif sent_count > 0:
            return {
                "success": True,
                "message": f"TopK portfolio sent to {sent_count}/{len(config['recipients'])} recipients",
                "errors": errors,
            }
        else:
            return {
                "success": False,
                "error": "Failed to send to any recipients",
                "errors": errors,
            }

    def _build_topk_portfolio_html(self, portfolio_data: Dict[str, Any]) -> str:
        """Build responsive HTML email for TopK portfolio with confidence percentile."""
        generated_at = portfolio_data.get("generated_at", datetime.now().isoformat())
        signal_for_date = portfolio_data.get("signal_for_date", "")
        topk = portfolio_data.get("topk", 10)
        positions = portfolio_data.get("positions", [])
        total_positions = len(positions)
        conf_percentile = portfolio_data.get("confidence_percentile")
        conf_label = portfolio_data.get("confidence_label", "")
        conf_interpretation = portfolio_data.get("confidence_interpretation", "")

        # Confidence color
        label_color_map = {
            "极强": ("#27ae60", "#e8f5e9"),
            "较强": ("#2ecc71", "#e8f5e9"),
            "正常": ("#3498db", "#e3f2fd"),
            "较弱": ("#f39c12", "#fff8e1"),
            "极弱": ("#e74c3c", "#ffebee"),
        }
        conf_color, conf_bg = label_color_map.get(conf_label, ("#999", "#f8f9fa"))

        # Percentile display
        if conf_percentile is not None:
            percentile_text = f"Top {100 - conf_percentile:.0f}%"
        else:
            percentile_text = ""

        # Build positions table rows
        position_rows = ""
        for pos in positions:
            rank = pos.get("rank", "")
            symbol = pos.get("symbol", "")
            name = pos.get("name", symbol)
            index_name = pos.get("index_name", "")
            score = pos.get("score", 0)
            weight = pos.get("weight", 0)

            # Alternating row background
            row_bg = "#f8f9fa" if rank % 2 == 0 else "#ffffff"
            position_rows += f"""
            <tr style="background: {row_bg};">
                <td style="padding: 10px 8px; text-align: center; color: #666;">{rank}</td>
                <td style="padding: 10px 8px;">
                    <div style="font-family: monospace; font-weight: bold; font-size: 13px;">{symbol}</div>
                    <div style="font-size: 12px; color: #888; margin-top: 2px;">{name}</div>
                </td>
                <td style="padding: 10px 8px; font-size: 12px; color: #666;">{index_name or '-'}</td>
                <td style="padding: 10px 8px; text-align: right; font-family: monospace; font-size: 13px;">{score:.4f}</td>
                <td style="padding: 10px 8px; text-align: right; font-weight: bold; color: #333;">{weight:.1%}</td>
            </tr>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                @media only screen and (max-width: 600px) {{
                    .email-container {{ padding: 8px !important; }}
                    .email-card {{ border-radius: 8px !important; }}
                    .email-header {{ padding: 18px 16px !important; }}
                    .email-header h1 {{ font-size: 18px !important; }}
                    .email-section {{ padding: 14px 12px !important; }}
                    .holdings-table {{ font-size: 12px !important; }}
                    .holdings-table td, .holdings-table th {{ padding: 8px 4px !important; }}
                    .interp-section {{ padding: 0 12px 12px 12px !important; }}
                    .table-section {{ padding: 0 12px 16px 12px !important; }}
                    .notes-section {{ padding: 12px !important; }}
                    .disclaimer-section {{ padding: 10px 12px !important; }}
                    .footer-section {{ padding: 10px 12px !important; }}
                }}
            </style>
        </head>
        <body style="font-family: -apple-system, 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif; margin: 0; padding: 16px; background-color: #f0f2f5;">
            <div class="email-container" style="max-width: 640px; margin: 0 auto;">
            <div class="email-card" style="background-color: white; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); overflow: hidden;">

                <!-- Header -->
                <div class="email-header" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 24px 24px;">
                    <h1 style="margin: 0; font-size: 20px; font-weight: 700;">📊 QuantBot 目标持仓</h1>
                    <p style="margin: 8px 0 0 0; opacity: 0.9; font-size: 14px;">
                        信号日期: <strong>{signal_for_date}</strong>
                    </p>
                </div>

                <!-- Signal Overview -->
                <div class="email-section" style="padding: 20px 24px;">
                    <table role="presentation" style="width: 100%; border-collapse: separate; border-spacing: 10px 0;">
                        <tr>
                            <td style="width: 50%; padding: 20px 12px; background: #f8f9fa; border-radius: 10px; text-align: center; vertical-align: middle;">
                                <div style="font-size: 22px; font-weight: 700; color: #333;">{total_positions}</div>
                                <div style="font-size: 12px; color: #888; margin-top: 4px;">持仓数量</div>
                            </td>
                            <td style="width: 50%; padding: 20px 12px; background: {conf_bg}; border-radius: 10px; text-align: center; vertical-align: middle;">
                                <div style="font-size: 22px; font-weight: 700; color: {conf_color};">{conf_label}</div>
                                <div style="font-size: 16px; font-weight: 600; color: {conf_color}; margin-top: 2px;">{percentile_text}</div>
                                <div style="font-size: 12px; color: #888; margin-top: 4px;">置信度</div>
                            </td>
                        </tr>
                    </table>
                </div>

                <!-- Interpretation -->
                {"" if not conf_interpretation else f'''
                <div class="interp-section" style="padding: 0 24px 16px 24px;">
                    <div style="background: {conf_bg}; border-left: 4px solid {conf_color}; padding: 12px 16px; border-radius: 0 8px 8px 0;">
                        <div style="font-size: 12px; color: #888; margin-bottom: 4px;">💡 信号解读</div>
                        <div style="font-size: 14px; color: #333; line-height: 1.6;">{conf_interpretation}</div>
                    </div>
                </div>
                '''}

                <!-- Target Holdings Table -->
                <div class="table-section" style="padding: 0 24px 20px 24px;">
                    <h2 style="font-size: 15px; color: #333; margin: 0 0 12px 0; padding-bottom: 8px; border-bottom: 2px solid #667eea;">
                        目标持仓 (Top {topk})
                    </h2>
                    <table class="holdings-table" style="width: 100%; border-collapse: collapse; font-size: 13px;">
                        <thead>
                            <tr style="background: #667eea; color: white;">
                                <th style="padding: 10px 8px; text-align: center; width: 32px; border-radius: 6px 0 0 0;">#</th>
                                <th style="padding: 10px 8px; text-align: left;">代码 / 名称</th>
                                <th style="padding: 10px 8px; text-align: left;">跟踪指数</th>
                                <th style="padding: 10px 8px; text-align: right; width: 60px;">分数</th>
                                <th style="padding: 10px 8px; text-align: right; width: 56px; border-radius: 0 6px 0 0;">权重</th>
                            </tr>
                        </thead>
                        <tbody>
                            {position_rows}
                        </tbody>
                    </table>
                </div>

                <!-- Notes -->
                <div class="notes-section" style="padding: 14px 24px; background: #f8f9fa; font-size: 12px; color: #888; line-height: 1.6;">
                    <p style="margin: 0;">
                        权重为模型推荐的配置比例，请按自身资金规模等比例缩放。分数越高代表模型预期收益越高。
                    </p>
                </div>

                <!-- Disclaimer -->
                <div class="disclaimer-section" style="padding: 10px 24px; background: #fef3c7; font-size: 11px; color: #92400e; line-height: 1.5;">
                    <strong>免责声明:</strong> 本邮件仅供学习和研究参考，不构成任何投资建议。
                </div>

                <!-- Footer -->
                <div class="footer-section" style="padding: 10px 24px; font-size: 11px; color: #bbb; border-top: 1px solid #eee;">
                    {generated_at[:19]} ｜ TopK (k={topk}) ｜ QuantBot
                </div>
            </div>
            </div>
        </body>
        </html>
        """

    def send_backtest_report_email(
        self,
        backtest_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send backtest report email after backtest completion.

        Args:
            backtest_result: Backtest result data including metrics and charts

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
        html_content = self._build_backtest_report_html(backtest_result)
        end_time = backtest_result.get("end_time", datetime.now().strftime("%Y-%m-%d"))

        sent_count = 0
        errors = []

        for recipient in config["recipients"]:
            try:
                send_email(
                    email_to=recipient,
                    subject=f"QuantBot: Backtest Report {end_time}",
                    html_content=html_content,
                )
                sent_count += 1
            except Exception as e:
                errors.append(f"{recipient}: {str(e)}")

        if sent_count == len(config["recipients"]):
            return {
                "success": True,
                "message": f"Backtest report sent to {sent_count} recipients",
            }
        elif sent_count > 0:
            return {
                "success": True,
                "message": f"Backtest report sent to {sent_count}/{len(config['recipients'])} recipients",
                "errors": errors,
            }
        else:
            return {
                "success": False,
                "error": "Failed to send to any recipients",
                "errors": errors,
            }

    def _generate_cumulative_returns_svg(
        self, cumulative_returns: List[Dict], max_drawdown_info: Dict
    ) -> str:
        """Generate SVG chart for cumulative returns with benchmark comparison."""
        if not cumulative_returns:
            return '<p style="color: #64748b; text-align: center;">No chart data available</p>'

        # Chart dimensions
        width = 700
        height = 300
        padding_left = 60
        padding_right = 20
        padding_top = 30
        padding_bottom = 50
        chart_width = width - padding_left - padding_right
        chart_height = height - padding_top - padding_bottom

        # Extract data points (sample if too many points)
        data = cumulative_returns
        if len(data) > 100:
            # Sample every nth point to keep chart readable
            step = len(data) // 100
            data = data[::step]
            # Always include the last point
            if cumulative_returns[-1] not in data:
                data.append(cumulative_returns[-1])

        # Get min/max values for scaling
        strategy_values = [d.get("strategy", 0) for d in data]
        benchmark_values = [d.get("benchmark", 0) for d in data if "benchmark" in d]
        all_values = strategy_values + benchmark_values

        if not all_values:
            return '<p style="color: #64748b; text-align: center;">No chart data available</p>'

        min_val = min(all_values)
        max_val = max(all_values)

        # Add padding to y-axis range
        y_range = max_val - min_val if max_val != min_val else 0.1
        min_val -= y_range * 0.1
        max_val += y_range * 0.1
        y_range = max_val - min_val

        # Generate path for strategy line
        def value_to_y(val):
            return (
                padding_top + chart_height - ((val - min_val) / y_range * chart_height)
            )

        def index_to_x(idx):
            return (
                padding_left + (idx / (len(data) - 1) * chart_width)
                if len(data) > 1
                else padding_left
            )

        # Strategy path
        strategy_points = []
        for i, d in enumerate(data):
            x = index_to_x(i)
            y = value_to_y(d.get("strategy", 0))
            strategy_points.append(f"{x:.1f},{y:.1f}")
        strategy_path = "M" + " L".join(strategy_points)

        # Strategy area (fill under the line)
        strategy_area_points = strategy_points.copy()
        strategy_area_points.append(
            f"{index_to_x(len(data)-1):.1f},{padding_top + chart_height}"
        )
        strategy_area_points.append(f"{padding_left},{padding_top + chart_height}")
        strategy_area = "M" + " L".join(strategy_area_points) + " Z"

        # Benchmark path (if available)
        benchmark_path = ""
        if benchmark_values:
            benchmark_points = []
            for i, d in enumerate(data):
                if "benchmark" in d:
                    x = index_to_x(i)
                    y = value_to_y(d.get("benchmark", 0))
                    benchmark_points.append(f"{x:.1f},{y:.1f}")
            if benchmark_points:
                benchmark_path = "M" + " L".join(benchmark_points)

        # Y-axis labels
        y_labels = []
        num_y_labels = 5
        for i in range(num_y_labels + 1):
            val = min_val + (y_range * i / num_y_labels)
            y = value_to_y(val)
            label = f"{val * 100:.0f}%"
            y_labels.append(
                f'<text x="{padding_left - 10}" y="{y:.1f}" text-anchor="end" font-size="10" fill="#64748b">{label}</text>'
            )

        # X-axis labels (show first, middle, last dates)
        x_labels = []
        if data:
            dates_to_show = [0, len(data) // 2, len(data) - 1]
            for idx in dates_to_show:
                if idx < len(data):
                    x = index_to_x(idx)
                    date_str = data[idx].get("date", "")[:10]  # Get YYYY-MM-DD
                    x_labels.append(
                        f'<text x="{x:.1f}" y="{height - 10}" text-anchor="middle" font-size="10" fill="#64748b">{date_str}</text>'
                    )

        # Zero line
        zero_y = value_to_y(0)
        zero_line = ""
        if min_val < 0 < max_val:
            zero_line = f'<line x1="{padding_left}" y1="{zero_y:.1f}" x2="{width - padding_right}" y2="{zero_y:.1f}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="4,4"/>'

        # Max drawdown region (if available)
        drawdown_region = ""
        if max_drawdown_info:
            peak_date = max_drawdown_info.get("peak_date")
            trough_date = max_drawdown_info.get("max_drawdown_date")
            if peak_date and trough_date:
                # Find indices for peak and trough dates
                peak_idx = None
                trough_idx = None
                for i, d in enumerate(data):
                    if d.get("date", "")[:10] == peak_date[:10]:
                        peak_idx = i
                    if d.get("date", "")[:10] == trough_date[:10]:
                        trough_idx = i
                if peak_idx is not None and trough_idx is not None:
                    x1 = index_to_x(peak_idx)
                    x2 = index_to_x(trough_idx)
                    drawdown_region = f'<rect x="{x1:.1f}" y="{padding_top}" width="{x2 - x1:.1f}" height="{chart_height}" fill="#fee2e2" opacity="0.5"/>'

        # Build SVG with viewBox for responsive scaling on mobile
        # Use viewBox so the SVG scales to container width
        svg_parts = [
            f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
            f'style="width:100%;max-width:{width}px;height:auto;">',
            f'<rect width="{width}" height="{height}" fill="white" rx="8"/>',
            # Grid
            f'<line x1="{padding_left}" y1="{padding_top}" x2="{padding_left}" y2="{padding_top + chart_height}" stroke="#e2e8f0" stroke-width="1"/>',
            f'<line x1="{padding_left}" y1="{padding_top + chart_height}" x2="{width - padding_right}" y2="{padding_top + chart_height}" stroke="#e2e8f0" stroke-width="1"/>',
        ]

        if zero_line:
            svg_parts.append(zero_line)
        if drawdown_region:
            svg_parts.append(drawdown_region)

        # Area fill + lines
        svg_parts.append(f'<path d="{strategy_area}" fill="#dcfce7" opacity="0.5"/>')
        if benchmark_path:
            svg_parts.append(
                f'<path d="{benchmark_path}" fill="none" stroke="#3b82f6" stroke-width="2"/>'
            )
        svg_parts.append(
            f'<path d="{strategy_path}" fill="none" stroke="#16a34a" stroke-width="2"/>'
        )

        # Labels
        svg_parts.extend(y_labels)
        svg_parts.extend(x_labels)

        # Legend
        svg_parts.append(
            f'<rect x="{width - 150}" y="10" width="12" height="12" fill="#16a34a"/>'
        )
        svg_parts.append(
            f'<text x="{width - 133}" y="20" font-size="11" fill="#334155">Strategy</text>'
        )
        if benchmark_path:
            svg_parts.append(
                f'<rect x="{width - 150}" y="28" width="12" height="12" fill="#3b82f6"/>'
            )
            svg_parts.append(
                f'<text x="{width - 133}" y="38" font-size="11" fill="#334155">Benchmark</text>'
            )

        svg_parts.append("</svg>")
        svg = "\n".join(svg_parts)

        # Also provide an <img> fallback for email clients that don't render inline SVG
        # Encode SVG as base64 data URI inside an <img> tag
        import base64

        svg_b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        img_tag = (
            f'<img src="data:image/svg+xml;base64,{svg_b64}" '
            f'alt="Cumulative Returns Chart" '
            f'style="width:100%;max-width:{width}px;height:auto;display:block;" />'
        )

        # Return both: inline SVG (for clients that support it) + img fallback
        return f'<div style="width:100%;overflow:hidden;">{img_tag}</div>'

    def _generate_drawdown_analysis_html(
        self, max_drawdown_info: Dict, max_drawdown: float
    ) -> str:
        """Generate HTML for drawdown analysis section."""
        if not max_drawdown_info:
            return ""

        peak_date = max_drawdown_info.get("peak_date", "N/A")
        trough_date = max_drawdown_info.get("max_drawdown_date", "N/A")
        drawdown_days = max_drawdown_info.get("drawdown_days", 0)
        recovery_date = max_drawdown_info.get("recovery_date", "Not recovered")

        # Format max drawdown
        max_dd_pct = f"{max_drawdown * 100:.2f}%" if max_drawdown else "N/A"

        return f"""
        <div style="font-size:15px;font-weight:600;color:#334155;margin-bottom:10px;padding-bottom:6px;border-bottom:2px solid #e2e8f0;">📉 Drawdown Analysis</div>
        <p style="color:#64748b;font-size:13px;margin:0 0 12px 0;">
            Maximum drawdown: <strong style="color:#dc2626;">{max_dd_pct}</strong>
        </p>
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
            <tr>
                <td style="padding:4px;width:50%;">
                    <div style="background-color:#fef2f2;border-radius:8px;padding:10px;">
                        <div style="font-size:11px;color:#64748b;margin-bottom:2px;">Peak Date</div>
                        <div style="font-size:13px;font-weight:600;color:#1e293b;">{peak_date}</div>
                    </div>
                </td>
                <td style="padding:4px;width:50%;">
                    <div style="background-color:#fef2f2;border-radius:8px;padding:10px;">
                        <div style="font-size:11px;color:#64748b;margin-bottom:2px;">Trough Date</div>
                        <div style="font-size:13px;font-weight:600;color:#1e293b;">{trough_date}</div>
                    </div>
                </td>
            </tr>
            <tr>
                <td style="padding:4px;width:50%;">
                    <div style="background-color:#fef2f2;border-radius:8px;padding:10px;">
                        <div style="font-size:11px;color:#64748b;margin-bottom:2px;">Drawdown Days</div>
                        <div style="font-size:13px;font-weight:600;color:#1e293b;">{drawdown_days} days</div>
                    </div>
                </td>
                <td style="padding:4px;width:50%;">
                    <div style="background-color:#fef2f2;border-radius:8px;padding:10px;">
                        <div style="font-size:11px;color:#64748b;margin-bottom:2px;">Recovery Date</div>
                        <div style="font-size:13px;font-weight:600;color:#1e293b;">{recovery_date if recovery_date else "Not recovered"}</div>
                    </div>
                </td>
            </tr>
        </table>
        """

    def _build_backtest_report_html(self, backtest_result: Dict[str, Any]) -> str:
        """Build HTML email body for backtest report.

        Uses table-based layout for maximum email client compatibility
        (especially mobile clients like WeChat, iOS Mail, etc.).
        """
        # Extract data from backtest result
        start_time = backtest_result.get("start_time", "N/A")
        end_time = backtest_result.get("end_time", "N/A")
        data_start_time = backtest_result.get("data_start_time", start_time)
        data_end_time = backtest_result.get("data_end_time", end_time)
        trading_days = backtest_result.get("trading_days", 0)
        total_return = backtest_result.get("total_return", 0)
        final_account = backtest_result.get("final_account", 0)
        strategy = backtest_result.get("strategy", "ETF Enhanced Indexing")
        benchmark = backtest_result.get("benchmark", "SH510300")

        # Risk metrics
        risk_metrics = backtest_result.get("risk_metrics", {})
        annualized_return = risk_metrics.get("annualized_return", 0)
        net_cagr = risk_metrics.get("net_cagr", 0)
        max_drawdown = risk_metrics.get("max_drawdown", 0)
        sharpe_ratio = risk_metrics.get("sharpe_ratio", 0)
        volatility = risk_metrics.get("volatility", 0)
        calmar_ratio = risk_metrics.get("calmar_ratio", 0)
        win_rate = risk_metrics.get("win_rate", 0)
        profit_loss_ratio = risk_metrics.get("profit_loss_ratio", 0)
        turnover_rate = risk_metrics.get("turnover_rate", 0)
        alpha = risk_metrics.get("alpha", 0)
        beta = risk_metrics.get("beta", 0)

        # Charts data
        charts = backtest_result.get("charts", {})
        cumulative_returns = charts.get("cumulative_returns", [])
        max_drawdown_info = charts.get("max_drawdown_info", {})

        # Format helpers
        def fmt_pct(value):
            if value is None:
                return "N/A"
            return f"{value * 100:+.2f}%" if value >= 0 else f"{value * 100:.2f}%"

        def fmt_cny(value):
            if value is None:
                return "N/A"
            return f"¥{value:,.0f}"

        def fmt_ratio(value):
            if value is None:
                return "N/A"
            return f"{value:.2f}"

        # Color helpers
        return_color = "#16a34a" if total_return >= 0 else "#dc2626"
        cagr_color = "#16a34a" if net_cagr >= 0 else "#dc2626"
        annual_return_color = "#16a34a" if annualized_return >= 0 else "#dc2626"
        sharpe_color = (
            "#16a34a"
            if sharpe_ratio >= 1
            else ("#ea580c" if sharpe_ratio >= 0 else "#dc2626")
        )

        # Generate SVG chart for cumulative returns
        chart_svg = self._generate_cumulative_returns_svg(
            cumulative_returns, max_drawdown_info
        )

        # Generate drawdown analysis HTML (table-based)
        drawdown_html = self._generate_drawdown_analysis_html(
            max_drawdown_info, max_drawdown
        )

        # Helper to build a metric cell for 2-column table
        def metric_cell(label, value, color="#1e293b"):
            return f"""
            <td style="padding:8px;width:50%;">
                <div style="background-color:#f8fafc;border-radius:8px;padding:12px;">
                    <div style="font-size:11px;color:#64748b;margin-bottom:4px;">{label}</div>
                    <div style="font-size:18px;font-weight:700;color:{color};">{value}</div>
                </div>
            </td>"""

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin:0;padding:12px;background-color:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;color:#1e293b;">
            <table width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;background-color:#ffffff;border-radius:12px;overflow:hidden;">
                <!-- Header -->
                <tr>
                    <td style="background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%);color:white;padding:20px;">
                        <div style="font-size:20px;font-weight:600;margin-bottom:4px;">📊 Backtest Report</div>
                        <div style="font-size:13px;opacity:0.9;">{start_time} ~ {end_time}</div>
                    </td>
                </tr>

                <tr><td style="padding:16px;">
                    <!-- Strategy Config -->
                    <div style="font-size:15px;font-weight:600;color:#334155;margin-bottom:10px;padding-bottom:6px;border-bottom:2px solid #e2e8f0;">⚙️ Configuration</div>
                    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
                        <tr>
                            <td style="padding:4px 0;color:#64748b;font-size:13px;">Strategy</td>
                            <td style="padding:4px 0;font-size:13px;font-weight:500;text-align:right;">{strategy}</td>
                        </tr>
                        <tr>
                            <td style="padding:4px 0;color:#64748b;font-size:13px;">Benchmark</td>
                            <td style="padding:4px 0;font-size:13px;font-weight:500;text-align:right;">{benchmark}</td>
                        </tr>
                        <tr>
                            <td style="padding:4px 0;color:#64748b;font-size:13px;">Period</td>
                            <td style="padding:4px 0;font-size:13px;font-weight:500;text-align:right;">{data_start_time} ~ {data_end_time}</td>
                        </tr>
                    </table>

                    <!-- Backtest Results -->
                    <div style="font-size:15px;font-weight:600;color:#334155;margin-bottom:10px;padding-bottom:6px;border-bottom:2px solid #e2e8f0;">📈 Backtest Results</div>
                    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
                        <tr>
                            {metric_cell("📅 Trading Days", str(trading_days))}
                            {metric_cell("� Net Return", fmt_pct(total_return), return_color)}
                        </tr>
                        <tr>
                            {metric_cell("� CAGR (Net)", fmt_pct(net_cagr), cagr_color)}
                            {metric_cell("💰 Initial Capital", fmt_cny(1000000))}
                        </tr>
                        <tr>
                            <td colspan="2" style="padding:8px;">
                                <div style="background-color:#f8fafc;border-radius:8px;padding:12px;">
                                    <div style="font-size:11px;color:#64748b;margin-bottom:4px;">💵 Final Account Value</div>
                                    <div style="font-size:22px;font-weight:700;color:#1e293b;">{fmt_cny(final_account)}</div>
                                </div>
                            </td>
                        </tr>
                    </table>

                    <!-- Risk Metrics -->
                    <div style="font-size:15px;font-weight:600;color:#334155;margin-bottom:10px;padding-bottom:6px;border-bottom:2px solid #e2e8f0;">⚡ Risk Metrics</div>
                    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
                        <tr>
                            {metric_cell("� Max Drawdown", fmt_pct(max_drawdown), "#dc2626")}
                            {metric_cell("🎯 Sharpe Ratio", fmt_ratio(sharpe_ratio), sharpe_color)}
                        </tr>
                        <tr>
                            {metric_cell("📊 Volatility", fmt_pct(volatility), "#64748b")}
                            {metric_cell("⚖️ Calmar Ratio", fmt_ratio(calmar_ratio))}
                        </tr>
                        <tr>
                            {metric_cell("🏆 Win Rate", fmt_pct(win_rate))}
                            {metric_cell("📊 P/L Ratio", fmt_ratio(profit_loss_ratio))}
                        </tr>
                        <tr>
                            {metric_cell("📈 Alpha", f"{alpha:.3f}", "#16a34a" if alpha >= 0 else "#dc2626")}
                            {metric_cell("📉 Beta", f"{beta:.3f}")}
                        </tr>
                    </table>

                    <!-- Cumulative Returns Chart -->
                    <div style="font-size:15px;font-weight:600;color:#334155;margin-bottom:10px;padding-bottom:6px;border-bottom:2px solid #e2e8f0;">📈 Cumulative Returns</div>
                    <div style="background-color:#f8fafc;border-radius:8px;padding:12px;margin-bottom:20px;overflow-x:auto;">
                        {chart_svg}
                    </div>

                    <!-- Drawdown Analysis -->
                    {drawdown_html}

                    <!-- Metric Explanations -->
                    <div style="background-color:#f8fafc;padding:12px;border-radius:8px;margin-top:12px;font-size:11px;color:#64748b;line-height:1.6;">
                        <strong>📖 Metric Explanations:</strong><br>
                        • <strong>Net Return</strong>: Cumulative return after trading costs<br>
                        • <strong>CAGR</strong>: Compound annual growth rate<br>
                        • <strong>Max Drawdown</strong>: Largest peak-to-trough decline<br>
                        • <strong>Sharpe Ratio</strong>: Risk-adjusted return (&gt;1 good, &gt;2 excellent)<br>
                        • <strong>Win Rate</strong>: Percentage of profitable trading days
                    </div>
                </td></tr>

                <!-- Disclaimer -->
                <tr>
                    <td style="padding:0 16px 12px 16px;">
                        <div style="background-color:#fef3c7;border:1px solid #f59e0b;border-radius:6px;padding:10px;">
                            <p style="margin:0;font-size:11px;color:#92400e;">
                                <strong>⚠️ 免责声明</strong><br>
                                本邮件仅供学习交流和技术研究使用，不构成任何投资建议。投资有风险，入市需谨慎。<br>
                                <em>For educational and research purposes only. Not investment advice.</em>
                            </p>
                        </div>
                    </td>
                </tr>

                <!-- Footer -->
                <tr>
                    <td style="background-color:#f8fafc;padding:12px;text-align:center;font-size:11px;color:#94a3b8;border-top:1px solid #e2e8f0;">
                        QuantBot Backtest System · {datetime.now().strftime("%Y-%m-%d %H:%M")}
                    </td>
                </tr>
            </table>
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
