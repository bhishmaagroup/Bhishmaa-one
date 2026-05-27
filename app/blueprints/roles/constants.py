# Roles & Permissions Constants

# Roles
ROLE_OWNER = 'Owner'
ROLE_MANAGER = 'Manager'
ROLE_CASHIER = 'Cashier'
ROLE_ACCOUNTANT = 'Accountant'
ROLE_STAFF = 'Staff'

ROLES = [
    ROLE_OWNER,
    ROLE_MANAGER,
    ROLE_CASHIER,
    ROLE_ACCOUNTANT,
    ROLE_STAFF
]

# Permissions
PERM_MANAGE_ORGANIZATION = 'can_manage_organization'
PERM_MANAGE_ROLES = 'can_manage_roles'
PERM_MANAGE_STAFF = 'can_manage_staff'
PERM_VIEW_DASHBOARD = 'can_view_dashboard'
PERM_MANAGE_BILLING = 'can_manage_billing'
PERM_MANAGE_INVENTORY = 'can_manage_inventory'
PERM_MANAGE_CRM = 'can_manage_crm'
PERM_MANAGE_REPORTS = 'can_manage_reports'
PERM_MANAGE_EXPENSES = 'can_manage_expenses'
PERM_MANAGE_HRM = 'can_manage_hrm'
PERM_MANAGE_TENANT = 'manage_tenant'

PERMISSIONS = {
    PERM_MANAGE_ORGANIZATION: 'Manage business profile, subdomain, and subscription billing settings.',
    PERM_MANAGE_ROLES: 'Configure and assign custom user roles and permissions access matrix.',
    PERM_MANAGE_STAFF: 'Add, update, and manage staff users, designations, departments, and payroll.',
    PERM_VIEW_DASHBOARD: 'Access the main business analytics dashboard and metric summary widgets.',
    PERM_MANAGE_BILLING: 'Access billing system, generate invoices, create sales, and process transactions.',
    PERM_MANAGE_INVENTORY: 'Access stock management, manage suppliers, purchase orders, and item variations.',
    PERM_MANAGE_CRM: 'Manage customer listings, capture leads, track customer queries and communications.',
    PERM_MANAGE_REPORTS: 'Access financial, GST, sales, and inventory analytics reports.',
    PERM_MANAGE_EXPENSES: 'Record and manage business expenses, supplier payouts, and outgoing transactions.',
    PERM_MANAGE_HRM: 'Manage attendance rosters, payroll generation, salary slip payouts, and HR records.',
    PERM_MANAGE_TENANT: 'Super Admin permission to view, manage, and suspend all SaaS tenant client organizations.'
}

# Default mappings of Role -> Permissions
DEFAULT_ROLE_PERMISSIONS = {
    ROLE_OWNER: [
        PERM_MANAGE_ORGANIZATION,
        PERM_MANAGE_ROLES,
        PERM_MANAGE_STAFF,
        PERM_VIEW_DASHBOARD,
        PERM_MANAGE_BILLING,
        PERM_MANAGE_INVENTORY,
        PERM_MANAGE_CRM,
        PERM_MANAGE_REPORTS,
        PERM_MANAGE_EXPENSES,
        PERM_MANAGE_HRM,
        PERM_MANAGE_TENANT
    ],
    ROLE_MANAGER: [
        PERM_VIEW_DASHBOARD,
        PERM_MANAGE_STAFF,
        PERM_MANAGE_BILLING,
        PERM_MANAGE_INVENTORY,
        PERM_MANAGE_CRM,
        PERM_MANAGE_REPORTS,
        PERM_MANAGE_EXPENSES,
        PERM_MANAGE_HRM
    ],
    ROLE_ACCOUNTANT: [
        PERM_VIEW_DASHBOARD,
        PERM_MANAGE_BILLING,
        PERM_MANAGE_REPORTS,
        PERM_MANAGE_EXPENSES
    ],
    ROLE_CASHIER: [
        PERM_VIEW_DASHBOARD,
        PERM_MANAGE_BILLING,
        PERM_MANAGE_CRM
    ],
    ROLE_STAFF: [
        PERM_VIEW_DASHBOARD,
        PERM_MANAGE_CRM
    ]
}
