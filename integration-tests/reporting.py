from typing import Optional

from behave.runner import Context
from environs import Env
from reportportal_behave.behave_integration_service import BehaveIntegrationService

REPORT_PORTAL_URL: Optional[str] = Env().str("REPORT_PORTAL_URL", None)
REPORT_PORTAL_PROJECT: Optional[str] = Env().str("REPORT_PORTAL_PROJECT", None)
REPORT_PORTAL_TOKEN: Optional[str] = Env().str("REPORT_PORTAL_TOKEN", None)
ENVIRONMENT: str = Env().str("ENVIRONMENT", "dev")
RELEASE: str = Env().str("RELEASE", "unknown")


def init_report_portal(context: Context) -> None:
    tags: str = ", ".join([tag for tags in context.config.tags.ands for tag in tags])
    rp_enable: bool = context.config.userdata.getbool("rp_enable", False)
    step_based: bool = context.config.userdata.getbool("step_based", True)
    add_screenshot: bool = context.config.userdata.getbool("add_screenshot", False)
    context.behave_integration_service = BehaveIntegrationService(
        rp_endpoint=REPORT_PORTAL_URL,
        rp_project=REPORT_PORTAL_PROJECT,
        rp_token=REPORT_PORTAL_TOKEN,
        rp_launch_name="Async Adapter",
        rp_launch_description="Async Adapter integration tests",
        rp_enable=rp_enable,
        step_based=step_based,
        add_screenshot=add_screenshot,
        verify_ssl=True,
    )
    attributes = {"environment": ENVIRONMENT, "release": RELEASE}
    context.launch_id = context.behave_integration_service.launch_service(
        attributes=attributes, tags=tags
    )
