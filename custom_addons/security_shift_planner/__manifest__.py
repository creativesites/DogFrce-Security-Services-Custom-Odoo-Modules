{
    "name": "Security Shift Planner",
    "summary": "Intelligent guard scoring, roster suggestions, and interactive Roster Board",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_attendance", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/security_shift_planner_views.xml",
        "views/security_shift_planner_client_actions.xml",
        "views/security_roster_week_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "security_shift_planner/static/src/css/roster_board.css",
            "security_shift_planner/static/src/js/roster_board.js",
            "security_shift_planner/static/src/xml/roster_board.xml",
            "security_shift_planner/static/src/js/weekly_checkin.js",
            "security_shift_planner/static/src/xml/weekly_checkin.xml",
        ],
    },
    "installable": True,
    "application": False,
}
