# Organizations Subscription Plan Constants

PLAN_FREE = 'Free'
PLAN_STARTER = 'Starter'
PLAN_BUSINESS = 'Business'
PLAN_PREMIUM = 'Premium'

PLAN_LIMITS = {
    PLAN_FREE: {
        'max_staff': 2,
        'max_invoices_per_month': 50,
        'max_products': 20,
        'features': ['billing', 'reports_lite']
    },
    PLAN_STARTER: {
        'max_staff': 5,
        'max_invoices_per_month': 250,
        'max_products': 100,
        'features': ['billing', 'inventory', 'expenses', 'reports_lite']
    },
    PLAN_BUSINESS: {
        'max_staff': 20,
        'max_invoices_per_month': 1500,
        'max_products': 1000,
        'features': ['billing', 'inventory', 'crm', 'expenses', 'reports_advanced', 'notifications']
    },
    PLAN_PREMIUM: {
        'max_staff': 99999,
        'max_invoices_per_month': 999999,
        'max_products': 999999,
        'features': ['billing', 'inventory', 'crm', 'hrm', 'pos', 'expenses', 'reports_advanced', 'notifications', 'api_access', 'ai_forecasting']
    }
}
