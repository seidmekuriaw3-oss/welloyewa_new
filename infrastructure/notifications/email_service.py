# ============================
# WOLLOYEWA STORE BOT - EMAIL SERVICE
# ============================
"""Email notification service using SMTP."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, Dict, Any, List
from pathlib import Path

from infrastructure.notifications.base import (
    NotificationProvider,
    NotificationRequest,
    NotificationResponse,
    NotificationType,
    NotificationError,
)
from core.config import settings
from core.logger import logger


class EmailService(NotificationProvider):
    """
    Email notification service using SMTP.
    
    Features:
    - HTML email support
    - Template rendering
    - Attachment support
    - Batch sending
    """
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.EMAIL_FROM
        self._templates = self._load_templates()
    
    @property
    def name(self) -> str:
        return "smtp"
    
    @property
    def notification_type(self) -> NotificationType:
        return NotificationType.EMAIL
    
    def _load_templates(self) -> Dict[str, str]:
        """Load email templates."""
        templates = {
            "welcome": """
            <h1>Welcome to Wolloyewa Store, {{name}}!</h1>
            <p>Thank you for joining Wolloyewa Store - Ethiopia's premier e-commerce platform.</p>
            <p>Get started by exploring our wide range of products and exclusive offers.</p>
            <br>
            <p>Best regards,<br>The Wolloyewa Team</p>
            """,
            
            "order_confirmation": """
            <h1>Order Confirmation</h1>
            <p>Dear {{name}},</p>
            <p>Thank you for your order! Your order <strong>#{{order_number}}</strong> has been confirmed.</p>
            <p><strong>Order Total:</strong> {{total}} ETB</p>
            <p>You can track your order status in the bot.</p>
            <br>
            <p>Thank you for shopping with Wolloyewa!</p>
            """,
            
            "password_reset": """
            <h1>Password Reset Request</h1>
            <p>Dear {{name}},</p>
            <p>We received a request to reset your password. Use the code below to reset your password:</p>
            <h2 style="padding: 10px; background: #f0f0f0; text-align: center;">{{code}}</h2>
            <p>This code will expire in 10 minutes.</p>
            <p>If you didn't request this, please ignore this email.</p>
            """,
            
            "payment_received": """
            <h1>Payment Received</h1>
            <p>Dear {{name}},</p>
            <p>We have received your payment of <strong>{{amount}} ETB</strong> for order <strong>#{{order_number}}</strong>.</p>
            <p>Your order is now being processed.</p>
            """,
            
            "order_shipped": """
            <h1>Your Order Has Been Shipped!</h1>
            <p>Dear {{name}},</p>
            <p>Great news! Your order <strong>#{{order_number}}</strong> has been shipped.</p>
            <p><strong>Tracking Number:</strong> {{tracking_number}}</p>
            <p>Estimated delivery: {{estimated_delivery}}</p>
            """,
        }
        return templates
    
    def _render_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """Render email template with data."""
        template = self._templates.get(template_name, "")
        if not template:
            return data.get("content", "")
        
        import jinja2
        env = jinja2.Environment()
        tmpl = env.from_string(template)
        return tmpl.render(**data)
    
    async def send(self, request: NotificationRequest) -> NotificationResponse:
        """
        Send an email.
        
        Args:
            request: Notification request
            
        Returns:
            Notification response
        """
        try:
            # Render content
            if request.template:
                content = self._render_template(request.template, request.template_data)
            else:
                content = request.content or ""
            
            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = request.to
            msg["Subject"] = request.subject or "Notification from Wolloyewa"
            
            # Attach HTML content
            msg.attach(MIMEText(content, "html"))
            
            # Add attachments
            for attachment in request.attachments:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.get("content", b""))
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={attachment.get('filename', 'attachment')}"
                )
                msg.attach(part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {request.to}")
            
            return NotificationResponse(
                success=True,
                status="sent",
                sent_at=datetime.utcnow(),
            )
            
        except Exception as e:
            logger.error(f"Failed to send email to {request.to}: {e}")
            return NotificationResponse(
                success=False,
                error=str(e),
                status="failed",
            )

    async def get_status(self, message_id: str) -> dict:
        """Get status of a sent email (not trackable via SMTP, return unknown)."""
        return {"message_id": message_id, "status": "unknown"}


# Global email service instance
_email_service = EmailService()


async def send_email(
    to: str,
    subject: str,
    content: Optional[str] = None,
    template: Optional[str] = None,
    template_data: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Send an email.
    
    Args:
        to: Recipient email address
        subject: Email subject
        content: Plain content (if no template)
        template: Template name
        template_data: Data for template
        
    Returns:
        True if sent successfully
    """
    request = NotificationRequest(
        type=NotificationType.EMAIL,
        to=to,
        subject=subject,
        content=content,
        template=template,
        template_data=template_data or {},
    )
    
    response = await _email_service.send(request)
    return response.success


async def send_order_confirmation_email(
    to: str,
    name: str,
    order_number: str,
    total: str,
) -> bool:
    """Send order confirmation email."""
    return await send_email(
        to=to,
        subject=f"Order Confirmation - #{order_number}",
        template="order_confirmation",
        template_data={
            "name": name,
            "order_number": order_number,
            "total": total,
        },
    )


async def send_password_reset_email(
    to: str,
    name: str,
    code: str,
) -> bool:
    """Send password reset email."""
    return await send_email(
        to=to,
        subject="Password Reset Request",
        template="password_reset",
        template_data={
            "name": name,
            "code": code,
        },
    )


async def send_welcome_email(to: str, name: str) -> bool:
    """Send welcome email."""
    return await send_email(
        to=to,
        subject="Welcome to Wolloyewa Store!",
        template="welcome",
        template_data={"name": name},
    )


__all__ = [
    "EmailService",
    "send_email",
    "send_order_confirmation_email",
    "send_password_reset_email",
    "send_welcome_email",
]