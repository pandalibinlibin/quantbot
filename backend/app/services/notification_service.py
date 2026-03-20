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

        # Build detailed positions table
        def build_detail_row(pos):
            action_color = (
                "#27ae60"
                if pos.get("action") == "buy"
                else ("#e74c3c" if pos.get("action") == "sell" else "#666")
            )
            action_text = (
                "买入"
                if pos.get("action") == "buy"
                else ("卖出" if pos.get("action") == "sell" else "持有")
            )
            pos_type = "ETF" if pos.get("type") == "etf" else "股票"
            return f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 8px; text-align: center;">{pos.get('rank', '-')}</td>
                <td style="padding: 8px;"><strong>{pos.get('symbol', '')}</strong><br><small style="color: #666;">{pos.get('name', '')}</small></td>
                <td style="padding: 8px; text-align: center;"><small>{pos_type}</small></td>
                <td style="padding: 8px; text-align: right;">{pos.get('score', 0):.4f}</td>
                <td style="padding: 8px; text-align: right;">{pos.get('weight', 0):.2%}</td>
                <td style="padding: 8px; text-align: right;">¥{pos.get('target_value', 0):,.0f}</td>
                <td style="padding: 8px; text-align: right;">¥{pos.get('reference_price', 0):,.3f}</td>
                <td style="padding: 8px; text-align: right;">{pos.get('target_shares', 0):,}</td>
                <td style="padding: 8px; text-align: right;">{pos.get('current_shares', 0):,}</td>
                <td style="padding: 8px; text-align: center; color: {action_color};"><strong>{action_text}</strong></td>
                <td style="padding: 8px; text-align: right; font-weight: bold;">{pos.get('action_lots', 0):,}手</td>
                <td style="padding: 8px; text-align: right;">{pos.get('action_shares', 0):,}股</td>
            </tr>
            """

        detail_rows = "".join([build_detail_row(p) for p in positions])

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
                
                <!-- Detailed Portfolio -->
                <div class="section">
                    <div class="section-title">📋 完整持仓明细</div>
                    <table class="detail-table">
                        <thead>
                            <tr>
                                <th style="width: 40px;">排名</th>
                                <th>代码/名称</th>
                                <th style="width: 50px;">类型</th>
                                <th style="width: 65px; text-align: right;">分数</th>
                                <th style="width: 55px; text-align: right;">权重</th>
                                <th style="width: 85px; text-align: right;">目标金额</th>
                                <th style="width: 75px; text-align: right;">参考价</th>
                                <th style="width: 70px; text-align: right;">目标股数</th>
                                <th style="width: 70px; text-align: right;">当前持股</th>
                                <th style="width: 50px; text-align: center;">操作</th>
                                <th style="width: 60px; text-align: right;">手数</th>
                                <th style="width: 70px; text-align: right;">股数</th>
                            </tr>
                        </thead>
                        <tbody>
                            {detail_rows}
                        </tbody>
                    </table>
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
        <p><small style="color: #888;">This is an automated email from QuantBot Enhanced Indexing system.</small></p>
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
