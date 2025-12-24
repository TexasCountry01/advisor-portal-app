"""
External API integration services for cases app.
Handles communication with benefits-software API.
"""
import requests
import logging
from typing import Dict, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from cases.models import Case, APICallLog

logger = logging.getLogger(__name__)


class BenefitsSoftwareAPI:
    """Client for benefits-software API integration"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'BENEFITS_SOFTWARE_API_URL', 'https://benefits-software.example.com/api')
        self.api_key = getattr(settings, 'BENEFITS_SOFTWARE_API_KEY', 'placeholder-api-key')
        self.timeout = getattr(settings, 'BENEFITS_SOFTWARE_API_TIMEOUT', 30)
        self.max_retries = getattr(settings, 'BENEFITS_SOFTWARE_API_MAX_RETRIES', 3)
    
    def submit_case(self, case: Case) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Submit a case to benefits-software API.
        
        Args:
            case: Case instance to submit
        
        Returns:
            Tuple of (success: bool, case_id: str, error_message: str)
        """
        endpoint = f"{self.base_url}/cases/submit"
        
        # Build payload from case data
        payload = {
            'workshop_code': case.workshop_code,
            'member_email': case.member.email,
            'member_first_name': case.member.first_name,
            'member_last_name': case.member.last_name,
            'employee_first_name': case.employee_first_name,
            'employee_last_name': case.employee_last_name,
            'client_email': case.client_email,
            'num_reports_requested': case.num_reports_requested,
            'urgency': case.urgency,
            'fact_finder_data': case.fact_finder_data,
            'submitted_at': case.created_at.isoformat() if case.created_at else timezone.now().isoformat(),
        }
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-Portal-Version': '1.0',
        }
        
        # Log the API call attempt
        api_log = APICallLog.objects.create(
            case=case,
            endpoint=endpoint,
            request_payload=payload,
            attempt_number=1
        )
        
        try:
            logger.info(f"Submitting case {case.id} to benefits-software API: {endpoint}")
            
            # Make API request
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            # Update log with response
            api_log.response_status_code = response.status_code
            api_log.response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {'raw': response.text}
            api_log.completed_at = timezone.now()
            
            if response.status_code == 200 or response.status_code == 201:
                # Success
                response_data = response.json()
                case_id = response_data.get('case_id')
                
                if not case_id:
                    error_msg = "API response missing case_id"
                    logger.error(f"Case {case.id}: {error_msg}")
                    api_log.success = False
                    api_log.error_message = error_msg
                    api_log.save()
                    return False, None, error_msg
                
                logger.info(f"Case {case.id} submitted successfully. Benefits-software case ID: {case_id}")
                api_log.success = True
                api_log.save()
                return True, case_id, None
            
            else:
                # API returned error
                error_msg = f"API returned status {response.status_code}: {response.text}"
                logger.error(f"Case {case.id}: {error_msg}")
                api_log.success = False
                api_log.error_message = error_msg
                api_log.save()
                return False, None, error_msg
        
        except requests.exceptions.Timeout:
            error_msg = f"API request timed out after {self.timeout} seconds"
            logger.error(f"Case {case.id}: {error_msg}")
            api_log.success = False
            api_log.error_message = error_msg
            api_log.completed_at = timezone.now()
            api_log.save()
            return False, None, error_msg
        
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(f"Case {case.id}: {error_msg}")
            api_log.success = False
            api_log.error_message = error_msg
            api_log.completed_at = timezone.now()
            api_log.save()
            return False, None, error_msg
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.exception(f"Case {case.id}: {error_msg}")
            api_log.success = False
            api_log.error_message = error_msg
            api_log.completed_at = timezone.now()
            api_log.save()
            return False, None, error_msg
    
    def retry_failed_submission(self, case: Case, attempt_number: int = 1) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Retry a failed case submission.
        
        Args:
            case: Case instance to retry
            attempt_number: Current retry attempt number
        
        Returns:
            Tuple of (success: bool, case_id: str, error_message: str)
        """
        if attempt_number > self.max_retries:
            error_msg = f"Maximum retry attempts ({self.max_retries}) exceeded"
            logger.error(f"Case {case.id}: {error_msg}")
            return False, None, error_msg
        
        logger.info(f"Retrying case {case.id} submission (attempt {attempt_number}/{self.max_retries})")
        
        # Call submit_case which handles logging
        success, case_id, error = self.submit_case(case)
        
        if not success and attempt_number < self.max_retries:
            # Update the most recent API log with retry info
            api_log = APICallLog.objects.filter(case=case).order_by('-created_at').first()
            if api_log:
                api_log.attempt_number = attempt_number
                api_log.save()
        
        return success, case_id, error


# Singleton instance
benefits_api = BenefitsSoftwareAPI()


def submit_case_to_benefits_software(case: Case) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Submit a case to benefits-software and update the case record.
    
    Args:
        case: Case instance to submit
    
    Returns:
        Tuple of (success: bool, case_id: str, error_message: str)
    """
    # Call the API
    success, case_id, error = benefits_api.submit_case(case)
    
    if success and case_id:
        # Update case with external case ID
        case.external_case_id = case_id
        case.api_sync_status = 'synced'
        case.api_synced_at = timezone.now()
        case.save(update_fields=['external_case_id', 'api_sync_status', 'api_synced_at'])
        logger.info(f"Case {case.id} updated with external_case_id: {case_id}")
    else:
        # Mark as failed
        case.api_sync_status = 'failed'
        case.save(update_fields=['api_sync_status'])
        logger.error(f"Case {case.id} API submission failed: {error}")
    
    return success, case_id, error


def retry_failed_cases():
    """
    Background task to retry failed case submissions.
    Can be called by management command or scheduled task.
    """
    failed_cases = Case.objects.filter(
        status='submitted',
        api_sync_status='failed',
        external_case_id__isnull=True
    ).order_by('created_at')
    
    logger.info(f"Found {failed_cases.count()} failed cases to retry")
    
    retry_count = 0
    success_count = 0
    
    for case in failed_cases:
        # Get number of previous attempts
        previous_attempts = APICallLog.objects.filter(case=case).count()
        
        if previous_attempts >= benefits_api.max_retries:
            logger.warning(f"Case {case.id} has exceeded max retries ({previous_attempts} attempts)")
            continue
        
        retry_count += 1
        success, case_id, error = benefits_api.retry_failed_submission(case, previous_attempts + 1)
        
        if success:
            success_count += 1
            case.external_case_id = case_id
            case.api_sync_status = 'synced'
            case.api_synced_at = timezone.now()
            case.save(update_fields=['external_case_id', 'api_sync_status', 'api_synced_at'])
    
    logger.info(f"Retry complete: {success_count}/{retry_count} cases successfully synced")
    return success_count, retry_count - success_count
