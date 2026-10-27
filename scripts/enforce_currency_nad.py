#!/usr/bin/env python3
"""
DogForce Namibia - Enforce Single Currency (NAD) Throughout System
===================================================================
1. Sets NAD attributes: symbol = 'N$', position = 'before', active = True
2. Deactivates all foreign currencies (USD, ZMW, EUR, etc.)
3. Enforces NAD on res_company
4. Updates all billing plans, invoices, account moves, and move lines to NAD
"""

SQL_ENFORCE_NAD = """
BEGIN;

-- 1. Enforce NAD currency attributes
UPDATE res_currency 
SET symbol = 'N$', 
    position = 'before', 
    active = true,
    currency_unit_label = '{"en_US": "Dollars"}',
    currency_subunit_label = '{"en_US": "Cents"}'
WHERE name = 'NAD';

-- 2. Deactivate all foreign currencies
UPDATE res_currency 
SET active = false 
WHERE name != 'NAD' AND active = true;

-- 3. Ensure company currency is NAD
UPDATE res_company 
SET currency_id = (SELECT id FROM res_currency WHERE name = 'NAD')
WHERE currency_id != (SELECT id FROM res_currency WHERE name = 'NAD');

-- 4. Fix billing plans
UPDATE security_billing_plan 
SET currency_id = (SELECT id FROM res_currency WHERE name = 'NAD')
WHERE currency_id != (SELECT id FROM res_currency WHERE name = 'NAD');

-- 5. Fix billing invoices
UPDATE security_billing_invoice 
SET currency_id = (SELECT id FROM res_currency WHERE name = 'NAD')
WHERE currency_id != (SELECT id FROM res_currency WHERE name = 'NAD');

-- 6. Fix account moves
UPDATE account_move 
SET currency_id = (SELECT id FROM res_currency WHERE name = 'NAD')
WHERE currency_id != (SELECT id FROM res_currency WHERE name = 'NAD');

-- 7. Fix account move lines
UPDATE account_move_line 
SET currency_id = (SELECT id FROM res_currency WHERE name = 'NAD')
WHERE currency_id != (SELECT id FROM res_currency WHERE name = 'NAD');

UPDATE account_move_line 
SET company_currency_id = (SELECT id FROM res_currency WHERE name = 'NAD')
WHERE company_currency_id != (SELECT id FROM res_currency WHERE name = 'NAD');

COMMIT;
"""

if __name__ == "__main__":
    print(SQL_ENFORCE_NAD)
