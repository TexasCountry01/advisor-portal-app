"""
Management command to send a test email to verify email template rendering.
Usage: python manage.py send_test_email
"""
import os
from email.mime.image import MIMEImage

from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.conf import settings


class Command(BaseCommand):
    help = 'Send a test email to verify email delivery and template rendering'

    def handle(self, *args, **options):
        recipients = [
            'tsdspyj@sbcglobal.net',
            'chris@profeds.com',
        ]

        subject = '[TEST] ProFeds Advisor Portal - Email Template Test'

        html_message = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, Helvetica, sans-serif; line-height: 1.6; color: #333333; margin: 0; padding: 0; background-color: #f4f4f4;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f4f4f4;">
        <tr>
            <td align="center">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; background-color: #ffffff;">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #ffffff; padding: 25px 20px 15px 30px; text-align: left; border-bottom: 2px solid #072A84;">
                            <img src="cid:logo" alt="FedImpact" width="180" style="width: 180px; height: auto; display: block;">
                        </td>
                    </tr>
                    <!-- Body -->
                    <tr>
                        <td style="padding: 30px 30px 20px 30px;">
                            <h2 style="margin: 0 0 10px 0; font-size: 20px; color: #072A84; border-bottom: 1px solid #dddddd; padding-bottom: 10px;">
                                &#9888; TEST EMAIL &#9888;
                            </h2>

                            <p style="margin: 0 0 16px 0; font-size: 15px; color: #333333;">
                                This is a <strong>TEST email</strong> sent from the ProFeds Advisor Portal to verify that email delivery and template rendering are working correctly.
                            </p>

                            <p style="margin: 0 0 16px 0; font-size: 15px; color: #333333;">
                                <strong>Please verify the following:</strong>
                            </p>

                            <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin: 0 0 16px 20px;">
                                <tr>
                                    <td style="padding: 4px 8px; font-size: 15px; color: #333333;">&#10004;</td>
                                    <td style="padding: 4px 8px; font-size: 15px; color: #333333;">The FedImpact logo appears at a reasonable size (not giant)</td>
                                </tr>
                                <tr>
                                    <td style="padding: 4px 8px; font-size: 15px; color: #333333;">&#10004;</td>
                                    <td style="padding: 4px 8px; font-size: 15px; color: #333333;">The button below is visible and properly styled</td>
                                </tr>
                                <tr>
                                    <td style="padding: 4px 8px; font-size: 15px; color: #333333;">&#10004;</td>
                                    <td style="padding: 4px 8px; font-size: 15px; color: #333333;">The overall layout looks clean and professional</td>
                                </tr>
                                <tr>
                                    <td style="padding: 4px 8px; font-size: 15px; color: #333333;">&#10004;</td>
                                    <td style="padding: 4px 8px; font-size: 15px; color: #333333;">Forwarding this email preserves the formatting</td>
                                </tr>
                            </table>

                            <!-- Email-safe button using table for Outlook compatibility -->
                            <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" style="margin: 20px auto;">
                                <tr>
                                    <td align="center" bgcolor="#072A84" style="background-color: #072A84; border-radius: 5px;">
                                        <a href="https://portal.profeds.com" target="_blank" style="display: inline-block; padding: 14px 32px; font-family: Arial, Helvetica, sans-serif; font-size: 16px; font-weight: bold; color: #ffffff; text-decoration: none;">SAMPLE BUTTON</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 16px 0 8px 0; font-size: 13px; color: #888888; text-align: center;">
                                This is a test email. No action is required.
                            </p>

                            <br>
                            <p style="margin: 0 0 4px 0; font-size: 15px; color: #333333;">
                                Thank you,
                            </p>
                            <p style="margin: 0 0 16px 0; font-size: 15px; color: #333333;">
                                <strong>The ProFeds Benefits Team</strong>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

        text_message = (
            "[TEST] ProFeds Advisor Portal - Email Template Test\n\n"
            "This is a TEST email sent from the ProFeds Advisor Portal "
            "to verify that email delivery and template rendering are working correctly.\n\n"
            "Please verify:\n"
            "- The FedImpact logo appears at a reasonable size\n"
            "- The button is visible and properly styled\n"
            "- The overall layout looks clean and professional\n"
            "- Forwarding this email preserves the formatting\n\n"
            "This is a test email. No action is required.\n\n"
            "Thank you,\nThe ProFeds Benefits Team"
        )

        self.stdout.write(f"Sending test email to: {', '.join(recipients)}")
        self.stdout.write(f"From: {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"Backend: {settings.EMAIL_BACKEND}")

        # Find the logo file
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'RevisedCoverPageLogo.png')
        if not os.path.exists(logo_path):
            logo_path = os.path.join(settings.BASE_DIR, 'staticfiles', 'images', 'RevisedCoverPageLogo.png')

        if not os.path.exists(logo_path):
            self.stdout.write(self.style.ERROR(f"Logo file not found at {logo_path}"))
            return

        self.stdout.write(f"Logo file: {logo_path}")

        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipients,
            )
            msg.attach_alternative(html_message, 'text/html')

            # Attach logo as inline image (CID)
            with open(logo_path, 'rb') as f:
                logo_data = f.read()
            logo_image = MIMEImage(logo_data, _subtype='png')
            logo_image.add_header('Content-ID', '<logo>')
            logo_image.add_header('Content-Disposition', 'inline', filename='logo.png')
            msg.attach(logo_image)

            msg.send(fail_silently=False)

            self.stdout.write(self.style.SUCCESS(
                f"Test email sent successfully to {', '.join(recipients)}"
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to send test email: {e}"))
