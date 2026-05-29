{
    "name": "Security Mobile API",
    "summary": "Secure REST JSON controllers for the DogForce mobile attendance app",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "DogForce Security Services",
    "license": "LGPL-3",
    "depends": [
        "security_base",
        "security_attendance",
        "security_operations",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/security_mobile_views.xml",
    ],
    "installable": True,
    "application": False,
}
