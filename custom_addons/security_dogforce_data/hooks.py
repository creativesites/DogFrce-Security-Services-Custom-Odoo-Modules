# -*- coding: utf-8 -*-
import logging
import re
from odoo import api, fields, models, SUPERUSER_ID

_logger = logging.getLogger(__name__)

MODULE = "security_dogforce_data"


def post_init_hook(env):
    """Post-install hook to load real DogForce company data."""
    _logger.info("Starting post-init hook for security_dogforce_data...")
    try:
        from .dogforce_extracted_data import DOGFORCE_DATA
        loader = DogForceDataLoader(env, DOGFORCE_DATA)
        loader.run()
        _logger.info("Successfully completed security_dogforce_data post-init hook.")
    except ImportError:
        _logger.error("dogforce_extracted_data.py not found or has syntax errors. Real data NOT loaded.")
    except Exception as e:
        _logger.exception("Failed to execute security_dogforce_data hook: %s", str(e))


def clean_xml_id(name):
    if not name:
        return ""
    # Strip any non-alphanumeric/non-underscore characters, replace spaces with underscores, and limit length
    return re.sub(r'[^a-zA-Z0-9_]', '', str(name).replace(' ', '_').lower())[:60]


class DogForceDataLoader:
    def __init__(self, env, data):
        self.env = env
        self.data = data

    def ref(self, name):
        return self.env.ref(f"{MODULE}.{name}", raise_if_not_found=False)

    def get_or_create(self, name, model, vals):
        existing = self.ref(name)
        if existing and existing.exists():
            return existing
        try:
            rec = self.env[model].create(vals)
            self.env["ir.model.data"].create(
                {
                    "module": MODULE,
                    "name": name,
                    "model": model,
                    "res_id": rec.id,
                    "noupdate": True,
                }
            )
            return rec
        except Exception as e:
            _logger.warning("Could not create record %s in %s: %s", name, model, str(e))
            return False

    def run(self):
        self._create_master_data()
        self._create_departments()
        self._create_jobs()
        self._create_calendars()
        self._create_work_locations()
        self._create_skill_types_and_skills()
        self._create_partners()
        self._create_employees()
        self._create_products()
        self._create_sales_teams()
        self._create_sales_orders()
        self._create_departure_reasons()
        self._create_applicants()
        self._create_refuse_reasons()
        self._create_attendances_batch()

    def _create_master_data(self):
        _logger.info("Creating security grades...")
        grades = [
            ("grade_a", "Grade A", "A", 1, 38.0, "critical"),
            ("grade_b", "Grade B", "B", 2, 34.0, "high"),
            ("grade_c", "Grade C", "C", 3, 30.0, "medium"),
            ("grade_d", "Grade D", "D", 4, 27.0, "medium"),
            ("grade_e", "Grade E", "E", 5, 24.0, "low"),
        ]
        for xmlid, name, code, sequence, rate, level in grades:
            self.get_or_create(
                xmlid,
                "security.grade",
                {
                    "name": name,
                    "code": code,
                    "sequence": sequence,
                    "hourly_rate": rate,
                    "responsibility_level": level,
                },
            )

    def _create_departments(self):
        _logger.info("Creating departments...")
        for row in self.data.get("hr_department", []):
            name = row.get("Department Name")
            if not name:
                continue
            xmlid = f"dept_{clean_xml_id(name)}"
            self.get_or_create(xmlid, "hr.department", {
                "name": name,
                "active": row.get("Active", True),
                "color": row.get("Color Index", 0),
            })

    def _create_jobs(self):
        _logger.info("Creating job positions...")
        for row in self.data.get("hr_job", []):
            name = row.get("Job Position")
            if not name:
                continue
            xmlid = f"job_{clean_xml_id(name)}"
            self.get_or_create(xmlid, "hr.job", {
                "name": name,
                "sequence": row.get("Sequence", 10),
                "no_of_recruitment": row.get("Target", 1),
            })

    def _create_calendars(self):
        _logger.info("Creating resource calendars...")
        for row in self.data.get("resource_calendar", []):
            name = row.get("Name")
            if not name:
                continue
            xmlid = f"cal_{clean_xml_id(name)}"
            self.get_or_create(xmlid, "resource.calendar", {
                "name": name,
                "active": True,
            })

    def _create_work_locations(self):
        _logger.info("Creating work locations...")
        company_partner_id = self.env.company.partner_id.id
        for row in self.data.get("hr_work_location", []):
            name = row.get("Work Location")
            if not name:
                continue
            xmlid = f"loc_{clean_xml_id(name)}"
            self.get_or_create(xmlid, "hr.work.location", {
                "name": name,
                "address_id": company_partner_id,
            })

    def _create_skill_types_and_skills(self):
        _logger.info("Creating skill types and skills...")
        for row in self.data.get("hr_skill_type", []):
            name = row.get("Display Name")
            if not name:
                continue
            xmlid = f"skill_type_{clean_xml_id(name)}"
            try:
                skill_type = self.get_or_create(xmlid, "hr.skill.type", {
                    "name": name,
                })
                skills_str = row.get("Skills")
                if skills_str and skill_type:
                    for s_name in [s.strip() for s in skills_str.split(",") if s.strip()]:
                        s_xmlid = f"skill_{clean_xml_id(name)}_{clean_xml_id(s_name)}"
                        self.get_or_create(s_xmlid, "hr.skill", {
                            "name": s_name,
                            "skill_type_id": skill_type.id,
                        })
            except Exception:
                pass

    def _create_partners(self):
        _logger.info("Creating res.partners...")
        partners = self.data.get("res_partner", [])
        for i, row in enumerate(partners):
            name = row.get("Complete Name") or row.get("Name")
            if not name:
                continue
            xmlid = f"partner_{clean_xml_id(name)}"
            if not xmlid or xmlid == "partner_":
                xmlid = f"partner_idx_{i}"
            self.get_or_create(xmlid, "res.partner", {
                "name": name,
                "company_type": "company",
                "email": row.get("Email"),
                "phone": row.get("Phone"),
            })

    def _create_employees(self):
        _logger.info("Creating employees...")
        for i, row in enumerate(self.data.get("hr_employee", [])):
            name = row.get("Employee Name")
            if not name:
                continue
            xmlid = f"emp_{clean_xml_id(name)}"
            if not xmlid or xmlid == "emp_":
                xmlid = f"emp_idx_{i}"

            phone = row.get("Work Phone")
            if phone:
                phone = str(phone).strip()
                if len(phone) > 4:
                    phone = phone[:-4] + "XXXX"

            clean_name_parts = re.sub(r'[^a-zA-Z0-9\s]', '', name).lower().split()
            if len(clean_name_parts) >= 2:
                email = f"{clean_name_parts[0]}.{clean_name_parts[-1]}@dogforce.na"
            else:
                email = f"{clean_name_parts[0]}@dogforce.na" if clean_name_parts else "guard@dogforce.na"

            dept_id = False
            dept_name = row.get("Department") or "Operations"
            if dept_name:
                dept_rec = self.ref(f"dept_{clean_xml_id(dept_name)}")
                if dept_rec:
                    dept_id = dept_rec.id

            job_id = False
            job_name = row.get("Job Title")
            if job_name:
                job_rec = self.ref(f"job_{clean_xml_id(job_name)}")
                if job_rec:
                    job_id = job_rec.id

            loc_id = False
            loc_name = row.get("Work Location")
            if loc_name:
                loc_rec = self.ref(f"loc_{clean_xml_id(loc_name)}")
                if loc_rec:
                    loc_id = loc_rec.id

            cal_id = False
            cal_name = row.get("Resource Calendar") or "Standard 38 hours/week"
            if cal_name:
                cal_rec = self.ref(f"cal_{clean_xml_id(cal_name)}")
                if cal_rec:
                    cal_id = cal_rec.id

            # Deterministic grades
            grade_xmlid = "grade_c"
            rate = 12.0
            if "Senior" in (job_name or ""):
                grade_xmlid = "grade_a"
                rate = 15.0
            elif "Driver" in (job_name or ""):
                grade_xmlid = "grade_b"
                rate = 13.5
            else:
                h = sum(ord(c) for c in name)
                if h % 3 == 0:
                    grade_xmlid = "grade_c"
                    rate = 12.0
                elif h % 3 == 1:
                    grade_xmlid = "grade_d"
                    rate = 11.0
                else:
                    grade_xmlid = "grade_e"
                    rate = 10.0

            grade_rec = self.ref(grade_xmlid)
            grade_id = grade_rec.id if grade_rec else False

            vals = {
                "name": name,
                "work_email": email,
                "work_phone": phone,
                "department_id": dept_id,
                "job_id": job_id,
                "work_location_id": loc_id,
                "resource_calendar_id": cal_id,
                "security_guard": True,
                "security_grade_id": grade_id,
                "security_hourly_rate": rate,
                "security_reliability_score": 100,
            }
            self.get_or_create(xmlid, "hr.employee", vals)

    def _create_products(self):
        _logger.info("Creating products...")
        for i, row in enumerate(self.data.get("product_template", [])):
            name = row.get("Name")
            if not name:
                continue
            xmlid = f"product_{clean_xml_id(name)}"
            if not xmlid or xmlid == "product_":
                xmlid = f"product_idx_{i}"
            
            self.get_or_create(xmlid, "product.template", {
                "name": name,
                "list_price": row.get("Sales Price", 0.0),
                "type": "service",
            })

    def _create_sales_teams(self):
        _logger.info("Creating sales teams...")
        for row in self.data.get("crm_team", []):
            name = row.get("Sales Team")
            if not name:
                continue
            xmlid = f"team_{clean_xml_id(name)}"
            self.get_or_create(xmlid, "crm.team", {
                "name": name,
            })

    def _create_sales_orders(self):
        _logger.info("Creating sales orders...")
        for i, row in enumerate(self.data.get("sale_order", [])):
            ref = row.get("Order Reference")
            if not ref:
                continue
            xmlid = f"sale_order_{clean_xml_id(ref)}"
            partner_name = row.get("Customer")
            partner_id = False
            if partner_name:
                partner_rec = self.ref(f"partner_{clean_xml_id(partner_name)}")
                if partner_rec:
                    partner_id = partner_rec.id
            
            vals = {
                "name": ref,
                "partner_id": partner_id,
                "date_order": row.get("Creation Date") or fields.Datetime.now(),
            }
            try:
                self.get_or_create(xmlid, "sale.order", vals)
            except Exception:
                pass

    def _create_departure_reasons(self):
        _logger.info("Creating departure reasons...")
        for row in self.data.get("hr_departure_reason", []):
            name = row.get("Reason")
            if not name:
                continue
            xmlid = f"departure_reason_{clean_xml_id(name)}"
            self.get_or_create(xmlid, "hr.departure.reason", {
                "name": name,
                "sequence": row.get("Sequence", 10),
            })

    def _create_applicants(self):
        _logger.info("Creating recruitment applicants...")
        for i, row in enumerate(self.data.get("hr_applicant", [])):
            name = row.get("Applicant's Name")
            if not name:
                continue
            xmlid = f"applicant_{clean_xml_id(name)}"
            
            job_name = row.get("Job Position")
            job_id = False
            if job_name:
                job_rec = self.ref(f"job_{clean_xml_id(job_name)}")
                if job_rec:
                    job_id = job_rec.id

            self.get_or_create(xmlid, "hr.applicant", {
                "name": f"Application - {name}",
                "partner_name": name,
                "job_id": job_id,
            })

    def _create_refuse_reasons(self):
        _logger.info("Creating refuse reasons...")
        for row in self.data.get("hr_applicant_refuse_reason", []):
            name = row.get("Description")
            if not name:
                continue
            xmlid = f"refuse_reason_{clean_xml_id(name)}"
            try:
                self.get_or_create(xmlid, "hr.applicant.refuse.reason", {
                    "name": name,
                })
            except Exception:
                pass

    def _create_attendances_batch(self):
        _logger.info("Batch importing attendance records...")
        attendances = self.data.get("hr_attendance", [])
        if self.env["hr.attendance"].search_count([]) > 0:
            _logger.info("Attendances already populated. Skipping batch attendance creation.")
            return

        employees = self.env["hr.employee"].search([])
        emp_by_name = {emp.name: emp.id for emp in employees}

        batch = []
        for i, row in enumerate(attendances):
            check_in = row.get("Check In")
            check_out = row.get("Check Out")
            emp_name = row.get("Employee")
            if not check_in or not check_out or not emp_name:
                continue # Skip group summary headers
            
            emp_id = emp_by_name.get(emp_name)
            if not emp_id:
                continue
            
            batch.append({
                "employee_id": emp_id,
                "check_in": check_in,
                "check_out": check_out,
            })

            if len(batch) >= 500:
                try:
                    self.env["hr.attendance"].create(batch)
                    batch = []
                    self.env.cr.commit()
                except Exception as e:
                    _logger.warning("Error creating attendance batch chunk: %s", str(e))
                    batch = []
                    self.env.cr.rollback()

        if batch:
            try:
                self.env["hr.attendance"].create(batch)
                self.env.cr.commit()
            except Exception as e:
                _logger.warning("Error creating final attendance batch chunk: %s", str(e))
                self.env.cr.rollback()
