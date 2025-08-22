"""Notification service for PulseStream alerts."""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from core.config import settings
from core.constants import NotificationChannel
from apps.storage.models.alert import Alert, AlertRule

logger = get_logger(__name__)


class NotificationService:
    """Service for sending alert notifications via various channels."""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def send_alert_notifications(self, alert: Alert, rule: AlertRule) -> None:
        """Send notifications for an alert via configured channels."""
        try:
            # Get notification channels from rule
            channels = rule.get_notification_channels()
            
            if not channels:
                logger.info(f"No notification channels configured for rule {rule.name}")
                return
            
            logger.info(f"Sending notifications for alert {alert.id} via channels: {channels}")
            
            # Send notifications to each channel
            for channel in channels:
                try:
                    await self._send_notification(channel, alert, rule)
                except Exception as e:
                    logger.error(f"Failed to send notification via {channel}: {e}")
                    # Record failure in alert
                    alert.record_notification_sent(channel, False, {"error": str(e)})
            
            await self._update_alert_notifications(alert)
            
        except Exception as e:
            logger.error(f"Error sending alert notifications: {e}")
    
    async def _send_notification(
        self, 
        channel: str, 
        alert: Alert, 
        rule: AlertRule
    ) -> None:
        """Send notification via a specific channel."""
        try:
            if channel == NotificationChannel.EMAIL:
                await self._send_email_notification(alert, rule)
            elif channel == NotificationChannel.SLACK:
                await self._send_slack_notification(alert, rule)
            elif channel == NotificationChannel.WEBHOOK:
                await self._send_webhook_notification(alert, rule)
            else:
                logger.warning(f"Unsupported notification channel: {channel}")
                
        except Exception as e:
            logger.error(f"Error sending {channel} notification: {e}")
            raise
    
    async def _send_email_notification(self, alert: Alert, rule: AlertRule) -> None:
        """Send email notification."""
        try:
            # Check if email is configured
            if not settings.smtp_host or not settings.smtp_username:
                logger.warning("SMTP not configured, skipping email notification")
                return
            
            # Get email template
            subject = f"[{alert.severity.upper()}] {alert.title}"
            body = self._generate_email_body(alert, rule)
            
            # TODO: Implement actual SMTP sending
            # For now, just log the email content
            logger.info(f"Email notification prepared:")
            logger.info(f"  To: {settings.email_from}")
            logger.info(f"  Subject: {subject}")
            logger.info(f"  Body: {body[:200]}...")
            
            # Record success
            alert.record_notification_sent(NotificationChannel.EMAIL, True, {
                "subject": subject,
                "body_length": len(body)
            })
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            raise
    
    async def _send_slack_notification(self, alert: Alert, rule: AlertRule) -> None:
        """Send Slack notification."""
        try:
            # Check if Slack is configured
            if not settings.slack_webhook_url:
                logger.warning("Slack webhook not configured, skipping Slack notification")
                return
            
            # Prepare Slack message
            slack_message = self._generate_slack_message(alert, rule)
            
            # Send to Slack webhook
            response = await self.http_client.post(
                settings.slack_webhook_url,
                json=slack_message,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info(f"Slack notification sent successfully")
                alert.record_notification_sent(NotificationChannel.SLACK, True, {
                    "response_status": response.status_code
                })
            else:
                logger.error(f"Slack notification failed: {response.status_code}")
                alert.record_notification_sent(NotificationChannel.SLACK, False, {
                    "response_status": response.status_code,
                    "response_text": response.text
                })
                
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            raise
    
    async def _send_webhook_notification(self, alert: Alert, rule: AlertRule) -> None:
        """Send webhook notification."""
        try:
            # Get webhook configuration from rule
            webhook_config = rule.get_channel_config(NotificationChannel.WEBHOOK)
            webhook_url = webhook_config.get("url")
            
            if not webhook_url:
                logger.warning("Webhook URL not configured, skipping webhook notification")
                return
            
            # Prepare webhook payload
            webhook_payload = self._generate_webhook_payload(alert, rule)
            
            # Send webhook
            response = await self.http_client.post(
                webhook_url,
                json=webhook_payload,
                headers=webhook_config.get("headers", {"Content-Type": "application/json"})
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Webhook notification sent successfully to {webhook_url}")
                alert.record_notification_sent(NotificationChannel.WEBHOOK, True, {
                    "webhook_url": webhook_url,
                    "response_status": response.status_code
                })
            else:
                logger.error(f"Webhook notification failed: {response.status_code}")
                alert.record_notification_sent(NotificationChannel.WEBHOOK, False, {
                    "webhook_url": webhook_url,
                    "response_status": response.status_code,
                    "response_text": response.text
                })
                
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
            raise
    
    def _generate_email_body(self, alert: Alert, rule: AlertRule) -> str:
        """Generate email body content."""
        body = f"""
Alert Details:
==============

Title: {alert.title}
Severity: {alert.severity.upper()}
Status: {alert.status}
Triggered: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

Message:
{alert.message}

Rule Information:
=================
Rule Name: {rule.name}
Description: {rule.description or 'No description'}
Time Window: {rule.time_window}
Evaluation Interval: {rule.evaluation_interval} seconds

Alert Context:
==============
Alert ID: {alert.id}
Rule ID: {rule.id}
Tenant ID: {alert.tenant_id}

This is an automated alert from PulseStream.
        """
        
        return body.strip()
    
    def _generate_slack_message(self, alert: Alert, rule: AlertRule) -> Dict[str, Any]:
        """Generate Slack message format."""
        # Determine color based on severity
        color_map = {
            "low": "#36a64f",      # Green
            "medium": "#ff8c00",   # Orange
            "high": "#ff0000",     # Red
            "critical": "#8b0000"  # Dark Red
        }
        color = color_map.get(alert.severity.lower(), "#36a64f")
        
        # Create Slack message
        message = {
            "attachments": [
                {
                    "color": color,
                    "title": alert.title,
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.upper(),
                            "short": True
                        },
                        {
                            "title": "Status",
                            "value": alert.status,
                            "short": True
                        },
                        {
                            "title": "Rule",
                            "value": rule.name,
                            "short": True
                        },
                        {
                            "title": "Time Window",
                            "value": rule.time_window,
                            "short": True
                        },
                        {
                            "title": "Triggered At",
                            "value": alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
                            "short": False
                        }
                    ],
                    "footer": "PulseStream Alerting System",
                    "ts": int(alert.triggered_at.timestamp())
                }
            ]
        }
        
        return message
    
    def _generate_webhook_payload(self, alert: Alert, rule: AlertRule) -> Dict[str, Any]:
        """Generate webhook payload."""
        return {
            "alert": {
                "id": str(alert.id),
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity,
                "status": alert.status,
                "triggered_at": alert.triggered_at.isoformat(),
                "trigger_data": alert.trigger_data
            },
            "rule": {
                "id": str(rule.id),
                "name": rule.name,
                "description": rule.description,
                "severity": rule.severity,
                "time_window": rule.time_window
            },
            "metadata": {
                "source": "pulsestream",
                "version": "1.0",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    
    async def _update_alert_notifications(self, alert: Alert) -> None:
        """Update alert with notification records."""
        try:
            # This would typically update the alert in the database
            # For now, we'll just log the notification records
            if alert.notifications_sent:
                logger.info(f"Alert {alert.id} notifications: {alert.notifications_sent}")
                
        except Exception as e:
            logger.error(f"Error updating alert notifications: {e}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()


class NotificationTemplateService:
    """Service for managing notification templates."""
    
    @staticmethod
    def get_default_email_template() -> str:
        """Get default email template."""
        return """
Alert: {alert_title}

Severity: {alert_severity}
Status: {alert_status}
Triggered: {alert_triggered_at}

{alert_message}

Rule: {rule_name}
Description: {rule_description}

This alert was generated by PulseStream.
        """
    
    @staticmethod
    def get_default_slack_template() -> Dict[str, Any]:
        """Get default Slack template."""
        return {
            "attachments": [
                {
                    "color": "{severity_color}",
                    "title": "{alert_title}",
                    "text": "{alert_message}",
                    "fields": [
                        {"title": "Severity", "value": "{alert_severity}", "short": True},
                        {"title": "Status", "value": "{alert_status}", "short": True},
                        {"title": "Rule", "value": "{rule_name}", "short": True},
                        {"title": "Triggered", "value": "{alert_triggered_at}", "short": False}
                    ]
                }
            ]
        }
    
    @staticmethod
    def get_default_webhook_template() -> Dict[str, Any]:
        """Get default webhook template."""
        return {
            "alert": {
                "id": "{alert_id}",
                "title": "{alert_title}",
                "message": "{alert_message}",
                "severity": "{alert_severity}",
                "status": "{alert_status}",
                "triggered_at": "{alert_triggered_at}"
            },
            "rule": {
                "id": "{rule_id}",
                "name": "{rule_name}",
                "description": "{rule_description}"
            },
            "metadata": {
                "source": "pulsestream",
                "timestamp": "{timestamp}"
            }
        }
    
    @staticmethod
    def render_template(template: str, variables: Dict[str, Any]) -> str:
        """Render a template with variables."""
        try:
            return template.format(**variables)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return template
    
    @staticmethod
    def render_json_template(template: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """Render a JSON template with variables."""
        try:
            # Convert to string, render, then back to JSON
            template_str = json.dumps(template)
            rendered_str = NotificationTemplateService.render_template(template_str, variables)
            return json.loads(rendered_str)
        except Exception as e:
            logger.error(f"Error rendering JSON template: {e}")
            return template
