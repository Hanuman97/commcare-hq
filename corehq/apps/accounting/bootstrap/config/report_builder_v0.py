from decimal import Decimal

from corehq.apps.accounting.models import (
    FeatureType,
    SoftwarePlanEdition,
)

BOOTSTRAP_CONFIG = {
    (SoftwarePlanEdition.REPORT_BUILDER_STANDARD, False): {
        'role': 'standard_plan_report_builder_v0',
        'product_rate': dict(monthly_fee=Decimal('100.00')),
        'feature_rates': {
            FeatureType.USER: dict(monthly_limit=100, per_excess_fee=Decimal('2.00')),
            FeatureType.SMS: dict(monthly_limit=100),
        }
    },
    (SoftwarePlanEdition.REPORT_BUILDER_PRO, False): {
        'role': 'pro_plan_report_builder_v0',
        'product_rate': dict(monthly_fee=Decimal('500.00')),
        'feature_rates': {
            FeatureType.USER: dict(monthly_limit=500, per_excess_fee=Decimal('2.00')),
            FeatureType.SMS: dict(monthly_limit=500),
        }
    },
    (SoftwarePlanEdition.REPORT_BUILDER_ADVANCED, False): {
        'role': 'advanced_plan_report_builder_v0',
        'product_rate': dict(monthly_fee=Decimal('1000.00')),
        'feature_rates': {
            FeatureType.USER: dict(monthly_limit=1000, per_excess_fee=Decimal('2.00')),
            FeatureType.SMS: dict(monthly_limit=1000),
        }
    },
}
