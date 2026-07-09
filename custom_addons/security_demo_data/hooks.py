from datetime import date, datetime, time, timedelta


MODULE = "security_demo_data"


def post_init_hook(env):
    DemoBuilder(env).run()


class DemoBuilder:
    def __init__(self, env):
        self.env = env

    def run(self):
        nad = self.env.ref("base.NAD", raise_if_not_found=False) or self.env.company.currency_id
        self._create_payroll_rules(nad)
        self._create_master_data()
        self._create_clients_sites_and_posts()
        self._create_guards()
        self._create_documents_and_leave()
        self._create_rosters_and_attendance()
        self._create_loans_and_incidents()
        self._create_equipment()
        self._create_fleet()
        self._create_payroll_and_billing(nad)
        self._create_client_report()
        self._create_june_september_rosters()

    def ref(self, name):
        return self.env.ref(f"{MODULE}.{name}", raise_if_not_found=False)

    def get_or_create(self, name, model, vals):
        existing = self.ref(name)
        if existing and existing.exists():
            return existing
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

    # ------------------------------------------------------------------
    # 1. PAYROLL RULES & PUBLIC HOLIDAYS
    # ------------------------------------------------------------------

    def _create_payroll_rules(self, nad):
        rule_set = self.get_or_create(
            "rule_set_na_2026",
            "security.payroll.rule.set",
            {
                "name": "Namibia Security Payroll Rules 2026",
                "country_code": "NA",
                "currency_id": nad.id,
                "effective_from": "2026-01-01",
                "employee_ssc_rate": 0.009,
                "employer_ssc_rate": 0.009,
                "ssc_salary_cap": 9000.0,
                "sunday_multiplier": 1.5,
                "public_holiday_multiplier": 1.5,
                "saturday_multiplier": 1.25,
                "night_shift_multiplier": 1.1,
                "overtime_multiplier": 1.0,
                "vat_rate": 15.0,
                "legal_invoice_text": (
                    "Prices are in Namibian Dollars (NAD). "
                    "VAT is charged at the standard Namibia rate of 15%."
                ),
            },
        )

        brackets = [
            ("tax_0_100k", "0 - 100,000", 0.0, 100000.0, 0.0, 0.0),
            ("tax_100k_150k", "100,001 - 150,000", 100000.0, 150000.0, 0.0, 0.18),
            ("tax_150k_350k", "150,001 - 350,000", 150000.0, 350000.0, 9000.0, 0.25),
            ("tax_350k_plus", "350,001 and Above", 350000.0, 0.0, 59000.0, 0.37),
        ]
        for xmlid, label, lower, upper, fixed, rate in brackets:
            self.get_or_create(
                xmlid,
                "security.tax.bracket",
                {
                    "rule_set_id": rule_set.id,
                    "lower_bound": lower,
                    "upper_bound": upper,
                    "fixed_amount": fixed,
                    "rate": rate,
                },
            )

        # Full 2026 Namibia public holiday calendar (expanded)
        holidays = [
            ("holiday_new_year_2026", "New Year's Day", "2026-01-01"),
            ("holiday_new_year_obs_2026", "New Year's Day (Observed)", "2026-01-02"),
            ("holiday_independence_day_2026", "Independence Day", "2026-03-21"),
            ("holiday_good_friday_2026", "Good Friday", "2026-04-03"),
            ("holiday_easter_saturday_2026", "Easter Saturday", "2026-04-04"),
            ("holiday_easter_monday_2026", "Easter Monday", "2026-04-06"),
            ("holiday_workers_day_2026", "Workers' Day", "2026-05-01"),
            ("holiday_cassinga_day_2026", "Cassinga Day", "2026-05-04"),
            ("holiday_ascension_day_2026", "Ascension Day", "2026-05-14"),
            ("holiday_africa_day_2026", "Africa Day", "2026-05-25"),
            ("holiday_heroes_day_2026", "Heroes' Day", "2026-08-26"),
            ("holiday_womens_day_2026", "Women's Day (Informal)", "2026-09-10"),
            ("holiday_human_rights_day_2026", "Human Rights Day", "2026-12-10"),
            ("holiday_christmas_2026", "Christmas Day", "2026-12-25"),
            ("holiday_family_day_2026", "Family Day", "2026-12-26"),
        ]
        for xmlid, name, holiday_date in holidays:
            self.get_or_create(
                xmlid,
                "security.public.holiday",
                {
                    "name": name,
                    "country_code": "NA",
                    "holiday_date": holiday_date,
                },
            )

    # ------------------------------------------------------------------
    # 2. MASTER DATA — grades, certs, languages, attributes, post types, shifts
    # ------------------------------------------------------------------

    def _create_master_data(self):
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

        # Document types (required before employee documents can be created)
        doc_type_model = self.env.get("security.document.type")
        if doc_type_model is not None:
            self.get_or_create("doctype_firearm", "security.document.type", {"name": "Firearm Competency Certificate", "code": "FIREARM", "expiry_required": True, "is_firearm_cert": True})
            self.get_or_create("doctype_id", "security.document.type", {"name": "National ID Document", "code": "NAT_ID", "expiry_required": False})
            self.get_or_create("doctype_cctv", "security.document.type", {"name": "CCTV Operations Certificate", "code": "CCTV_CERT", "expiry_required": True})
            self.get_or_create("doctype_first_aid", "security.document.type", {"name": "First Aid Certificate", "code": "FIRST_AID_CERT", "expiry_required": True})

        # Certifications
        self.get_or_create("cert_firearm", "security.certification", {"name": "Firearm Competency", "code": "FIREARM", "expiry_required": True})
        self.get_or_create("cert_driver", "security.certification", {"name": "Professional Driver", "code": "DRIVER"})
        self.get_or_create("cert_first_aid", "security.certification", {"name": "First Aid Certificate", "code": "FIRST_AID", "expiry_required": True})
        self.get_or_create("cert_cctv", "security.certification", {"name": "CCTV Operations", "code": "CCTV"})

        # Languages
        self.get_or_create("lang_english", "security.language", {"name": "English", "code": "EN"})
        self.get_or_create("lang_afrikaans", "security.language", {"name": "Afrikaans", "code": "AF"})
        self.get_or_create("lang_oshiwambo", "security.language", {"name": "Oshiwambo", "code": "OSH"})
        self.get_or_create("lang_herero", "security.language", {"name": "Herero", "code": "HER"})
        self.get_or_create("lang_damara_nama", "security.language", {"name": "Damara/Nama", "code": "DAM"})

        # Attributes
        self.get_or_create("attr_night_ready", "security.attribute", {"name": "Night Shift Ready", "category": "other"})
        self.get_or_create("attr_control_room", "security.attribute", {"name": "Control Room Experience", "category": "training"})
        self.get_or_create("attr_crowd_control", "security.attribute", {"name": "Crowd Control", "category": "training"})
        self.get_or_create("attr_vip_protection", "security.attribute", {"name": "VIP Protection", "category": "training"})

        # Post types
        grade_c = self.ref("grade_c")
        english = self.ref("lang_english")
        firearm = self.ref("cert_firearm")
        cctv = self.ref("cert_cctv")

        self.get_or_create(
            "post_type_gate",
            "security.post.type",
            {
                "name": "Gate Guard",
                "code": "GATE",
                "min_grade_id": grade_c.id,
                "required_language_ids": [(6, 0, [english.id])],
                "minimum_reliability_score": 70,
            },
        )
        self.get_or_create(
            "post_type_control_room",
            "security.post.type",
            {
                "name": "Control Room",
                "code": "CTRL",
                "min_grade_id": self.ref("grade_b").id,
                "required_language_ids": [(6, 0, [english.id])],
                "required_attribute_ids": [(6, 0, [self.ref("attr_control_room").id])],
                "minimum_reliability_score": 80,
            },
        )
        self.get_or_create(
            "post_type_armed_response",
            "security.post.type",
            {
                "name": "Armed Guard",
                "code": "ARMED",
                "min_grade_id": self.ref("grade_a").id,
                "required_certification_ids": [(6, 0, [firearm.id])],
                "required_language_ids": [(6, 0, [english.id])],
                "minimum_reliability_score": 90,
            },
        )
        self.get_or_create(
            "post_type_vip_escort",
            "security.post.type",
            {
                "name": "VIP Escort",
                "code": "VIP",
                "min_grade_id": self.ref("grade_a").id,
                "required_certification_ids": [(6, 0, [firearm.id])],
                "required_attribute_ids": [(6, 0, [self.ref("attr_vip_protection").id])],
                "required_language_ids": [(6, 0, [english.id])],
                "minimum_reliability_score": 92,
            },
        )
        self.get_or_create(
            "post_type_cctv_operator",
            "security.post.type",
            {
                "name": "CCTV Operator",
                "code": "CCTV",
                "min_grade_id": self.ref("grade_b").id,
                "required_certification_ids": [(6, 0, [cctv.id])],
                "required_attribute_ids": [(6, 0, [self.ref("attr_control_room").id])],
                "minimum_reliability_score": 80,
            },
        )

        # Shift templates
        self.get_or_create("shift_day", "security.shift.template", {"name": "Day Shift 06:00-18:00", "start_hour": 6.0, "end_hour": 18.0})
        self.get_or_create("shift_night", "security.shift.template", {"name": "Night Shift 18:00-06:00", "start_hour": 18.0, "end_hour": 6.0})
        self.get_or_create("shift_business", "security.shift.template", {"name": "Business Hours 08:00-17:00", "start_hour": 8.0, "end_hour": 17.0})
        self.get_or_create("shift_afternoon", "security.shift.template", {"name": "Afternoon Shift 14:00-22:00", "start_hour": 14.0, "end_hour": 22.0})

    # ------------------------------------------------------------------
    # 3. CLIENTS, SITES, POSTS  (10 clients, 30 sites)
    # ------------------------------------------------------------------

    def _create_clients_sites_and_posts(self):
        na_id = self.env.ref("base.na").id

        # ---- 10 clients ----
        clients = [
            ("client_bank_windhoek", "Bank Windhoek", "Independence Avenue", "Windhoek", "banking@bankwindhoek.com.na"),
            ("client_namibia_breweries", "Namibia Breweries Limited", "Iscor Street", "Windhoek", "security@nbl.com.na"),
            ("client_nwr", "Namibia Wildlife Resorts", "Independence Avenue 1", "Windhoek", "security@nwr.com.na"),
            ("client_mtc", "MTC Namibia", "Telecommunications Avenue", "Windhoek", "security@mtc.com.na"),
            ("client_old_mutual", "Old Mutual Namibia", "Grove Mall, Chasie Street", "Windhoek", "security@oldmutual.com.na"),
            ("client_standard_bank", "Standard Bank Namibia", "267 Independence Avenue", "Windhoek", "security@standardbank.com.na"),
            ("client_city_windhoek", "City of Windhoek", "Municipal Offices, Independence Avenue", "Windhoek", "security@cityofwindhoek.org.na"),
            ("client_nampower", "NamPower Corporation", "15 Luther Street", "Windhoek", "security@nampower.com.na"),
            ("client_shoprite", "ShopRite Namibia", "Wernhil Park, Tal Street", "Windhoek", "security@shoprite.com.na"),
            ("client_game_city", "Game City Mall Windhoek", "Western Bypass, Brakwater", "Windhoek", "security@gamecity.com.na"),
        ]
        for xmlid, name, street, city, email in clients:
            self.get_or_create(
                xmlid,
                "res.partner",
                {
                    "name": name,
                    "company_type": "company",
                    "street": street,
                    "city": city,
                    "country_id": na_id,
                    "phone": "+264 61 000 000",
                    "email": email,
                },
            )

        # Backward-compat alias — old xmlid used in fleet/documents sections
        # (client_nam_breweries → client_namibia_breweries)
        # We keep the old xmlid pointing at the same record if already in DB
        nbl = self.ref("client_namibia_breweries")
        if nbl and not self.ref("client_nam_breweries"):
            self.env["ir.model.data"].create({
                "module": MODULE,
                "name": "client_nam_breweries",
                "model": "res.partner",
                "res_id": nbl.id,
                "noupdate": True,
            })

        # ---- 30 sites (3 per client) ----
        # fmt: off
        sites = [
            # Bank Windhoek
            ("site_bw_hq",        "BW Head Office - CBD",              "BW-HQ",      "client_bank_windhoek",    "Independence Avenue, Windhoek"),
            ("site_bw_maerua",    "BW Maerua Mall Branch",             "BW-MAE",     "client_bank_windhoek",    "Maerua Mall, Windhoek"),
            ("site_bw_katutura",  "BW Katutura Branch",                "BW-KAT",     "client_bank_windhoek",    "Katutura, Windhoek"),
            # NBL
            ("site_nbl_brewery",  "NBL Brewery Plant - Northern Industrial", "NBL-PLT", "client_namibia_breweries", "Northern Industrial, Windhoek"),
            ("site_nbl_depot",    "NBL Distribution Depot - Khomasdal","NBL-DEP",    "client_namibia_breweries", "Khomasdal, Windhoek"),
            ("site_nbl_office",   "NBL Head Office",                   "NBL-HQ",     "client_namibia_breweries", "Southern Industrial, Windhoek"),
            # NWR
            ("site_nwr_hq",       "NWR Head Office - Windhoek",        "NWR-HQ",     "client_nwr",              "Aviator Street, Windhoek"),
            ("site_nwr_swakop",   "NWR Swakopmund Resort",             "NWR-SWK",    "client_nwr",              "Strand Street, Swakopmund"),
            ("site_nwr_etosha",   "NWR Etosha Office",                 "NWR-ETO",    "client_nwr",              "Namutoni, Etosha"),
            # MTC
            ("site_mtc_hq",       "MTC Head Office - Windhoek",        "MTC-HQ",     "client_mtc",              "Telecommunications Street, Windhoek"),
            ("site_mtc_oshakati", "MTC Oshakati Branch",               "MTC-OSH",    "client_mtc",              "Oshakati, Namibia"),
            ("site_mtc_walvis",   "MTC Walvis Bay Branch",             "MTC-WAL",    "client_mtc",              "Walvis Bay, Namibia"),
            # Old Mutual
            ("site_om_hq",        "Old Mutual HQ - Grove Mall",        "OM-HQ",      "client_old_mutual",       "Grove Mall, Windhoek"),
            ("site_om_grove",     "Old Mutual Grove Mall Branch",      "OM-GRV",     "client_old_mutual",       "Grove Mall, Windhoek"),
            ("site_om_khomasdal", "Old Mutual Khomasdal Office",       "OM-KHO",     "client_old_mutual",       "Khomasdal, Windhoek"),
            # Standard Bank
            ("site_sb_hq",        "Standard Bank HQ - Independence Avenue", "SB-HQ", "client_standard_bank",   "267 Independence Avenue, Windhoek"),
            ("site_sb_wernhil",   "Standard Bank Wernhil Park",        "SB-WER",     "client_standard_bank",    "Wernhil Park, Windhoek"),
            ("site_sb_maerua",    "Standard Bank Maerua Mall",         "SB-MAE",     "client_standard_bank",    "Maerua Mall, Windhoek"),
            # City of Windhoek
            ("site_cow_municipal","Municipal Offices - CBD",           "COW-MUN",    "client_city_windhoek",    "Independence Avenue, Windhoek"),
            ("site_cow_sewage",   "Gammams Sewage Plant",              "COW-SEW",    "client_city_windhoek",    "Gammams, Windhoek"),
            ("site_cow_workshop", "Municipal Workshop - Khomasdal",    "COW-WRK",    "client_city_windhoek",    "Khomasdal, Windhoek"),
            # NamPower
            ("site_np_hq",        "NamPower HQ - Windhoek",           "NP-HQ",      "client_nampower",         "15 Luther Street, Windhoek"),
            ("site_np_substation","Van Eck Power Station",             "NP-VEC",     "client_nampower",         "Northern Industrial, Windhoek"),
            ("site_np_north",     "Northern Operations Centre - Oshakati", "NP-OSH", "client_nampower",        "Oshakati, Namibia"),
            # ShopRite
            ("site_sr_wernhil",   "ShopRite Wernhil Park",            "SR-WER",     "client_shoprite",         "Wernhil Park, Windhoek"),
            ("site_sr_maerua",    "ShopRite Maerua Mall",             "SR-MAE",     "client_shoprite",         "Maerua Mall, Windhoek"),
            ("site_sr_katutura",  "ShopRite Katutura",                "SR-KAT",     "client_shoprite",         "Katutura, Windhoek"),
            # Game City
            ("site_gc_mall",      "Game City Mall - Main Entrance",   "GC-MAIN",    "client_game_city",        "Western Bypass, Windhoek"),
            ("site_gc_parking",   "Game City Mall - Parking Deck",    "GC-PARK",    "client_game_city",        "Western Bypass, Windhoek"),
            ("site_gc_food_court","Game City Mall - Food Court",      "GC-FOOD",    "client_game_city",        "Western Bypass, Windhoek"),
        ]
        # fmt: on
        for xmlid, name, code, partner_xmlid, location in sites:
            self.get_or_create(
                xmlid,
                "security.client.site",
                {
                    "name": name,
                    "code": code,
                    "partner_id": self.ref(partner_xmlid).id,
                    "location": location,
                },
            )

        # Backward-compat aliases used in fleet/roster sections
        alias_map = {
            "site_bank_hq": "site_bw_hq",
            "site_bank_cash": "site_bw_hq",          # reuse HQ as placeholder
            "site_breweries": "site_nbl_brewery",
            "site_walvis_port": "site_nbl_depot",     # closest Walvis analog
            "site_nwr_windhoek": "site_nwr_hq",
            "site_nwr_swakopmund": "site_nwr_swakop",
        }
        for old_xmlid, new_xmlid in alias_map.items():
            if not self.ref(old_xmlid):
                target = self.ref(new_xmlid)
                if target:
                    self.env["ir.model.data"].create({
                        "module": MODULE,
                        "name": old_xmlid,
                        "model": "security.client.site",
                        "res_id": target.id,
                        "noupdate": True,
                    })

        # ---- Posts: 2-3 per site ----
        post_specs = [
            # Bank Windhoek
            ("post_bw_hq_gate",        "Main Gate",           "site_bw_hq",        "post_type_gate",          2),
            ("post_bw_hq_control",     "Control Room",        "site_bw_hq",        "post_type_control_room",  1),
            ("post_bw_hq_armed",       "Armed Reception",     "site_bw_hq",        "post_type_armed_response",1),
            ("post_bw_maerua_gate",    "Branch Gate",         "site_bw_maerua",    "post_type_gate",          1),
            ("post_bw_maerua_cctv",    "CCTV Room",           "site_bw_maerua",    "post_type_cctv_operator", 1),
            ("post_bw_katutura_gate",  "Branch Gate",         "site_bw_katutura",  "post_type_gate",          2),
            # NBL
            ("post_nbl_brewery_gate",  "Plant Gate",          "site_nbl_brewery",  "post_type_gate",          2),
            ("post_nbl_brewery_armed", "Plant Armed Post",    "site_nbl_brewery",  "post_type_armed_response",1),
            ("post_nbl_depot_gate",    "Depot Gate",          "site_nbl_depot",    "post_type_gate",          1),
            ("post_nbl_depot_cctv",    "Depot CCTV",          "site_nbl_depot",    "post_type_cctv_operator", 1),
            ("post_nbl_office_gate",   "Head Office Gate",    "site_nbl_office",   "post_type_gate",          1),
            # NWR
            ("post_nwr_hq_gate",       "HQ Main Entrance",    "site_nwr_hq",       "post_type_gate",          2),
            ("post_nwr_hq_cctv",       "HQ CCTV Room",        "site_nwr_hq",       "post_type_cctv_operator", 1),
            ("post_nwr_swakop_gate",   "Resort Main Gate",    "site_nwr_swakop",   "post_type_gate",          2),
            ("post_nwr_etosha_gate",   "Office Gate",         "site_nwr_etosha",   "post_type_gate",          1),
            # MTC
            ("post_mtc_hq_gate",       "Head Office Gate",    "site_mtc_hq",       "post_type_gate",          2),
            ("post_mtc_hq_vip",        "VIP Escort",          "site_mtc_hq",       "post_type_vip_escort",    1),
            ("post_mtc_oshakati_gate", "Branch Gate",         "site_mtc_oshakati", "post_type_gate",          1),
            ("post_mtc_walvis_gate",   "Branch Gate",         "site_mtc_walvis",   "post_type_gate",          1),
            # Old Mutual
            ("post_om_hq_gate",        "HQ Gate",             "site_om_hq",        "post_type_gate",          2),
            ("post_om_hq_control",     "Control Room",        "site_om_hq",        "post_type_control_room",  1),
            ("post_om_grove_gate",     "Branch Gate",         "site_om_grove",     "post_type_gate",          1),
            ("post_om_khomasdal_gate", "Branch Gate",         "site_om_khomasdal", "post_type_gate",          1),
            # Standard Bank
            ("post_sb_hq_gate",        "HQ Gate",             "site_sb_hq",        "post_type_gate",          2),
            ("post_sb_hq_armed",       "HQ Armed Post",       "site_sb_hq",        "post_type_armed_response",1),
            ("post_sb_wernhil_gate",   "Branch Gate",         "site_sb_wernhil",   "post_type_gate",          1),
            ("post_sb_maerua_gate",    "Branch Gate",         "site_sb_maerua",    "post_type_gate",          1),
            # City of Windhoek
            ("post_cow_municipal_gate","Municipal Gate",      "site_cow_municipal","post_type_gate",          2),
            ("post_cow_sewage_gate",   "Sewage Plant Gate",   "site_cow_sewage",   "post_type_gate",          1),
            ("post_cow_workshop_gate", "Workshop Gate",       "site_cow_workshop", "post_type_gate",          1),
            # NamPower
            ("post_np_hq_gate",        "HQ Gate",             "site_np_hq",        "post_type_gate",          2),
            ("post_np_hq_control",     "HQ Control Room",     "site_np_hq",        "post_type_control_room",  1),
            ("post_np_substation_gate","Station Gate",        "site_np_substation","post_type_armed_response",1),
            ("post_np_north_gate",     "North Ops Gate",      "site_np_north",     "post_type_gate",          1),
            # ShopRite
            ("post_sr_wernhil_gate",   "Store Gate",          "site_sr_wernhil",   "post_type_gate",          2),
            ("post_sr_wernhil_cctv",   "CCTV Room",           "site_sr_wernhil",   "post_type_cctv_operator", 1),
            ("post_sr_maerua_gate",    "Store Gate",          "site_sr_maerua",    "post_type_gate",          1),
            ("post_sr_katutura_gate",  "Store Gate",          "site_sr_katutura",  "post_type_gate",          1),
            # Game City
            ("post_gc_mall_gate",      "Main Entrance Gate",  "site_gc_mall",      "post_type_gate",          3),
            ("post_gc_parking_gate",   "Parking Deck Access", "site_gc_parking",   "post_type_gate",          2),
            ("post_gc_food_cctv",      "Food Court CCTV",     "site_gc_food_court","post_type_cctv_operator", 1),
        ]
        for xmlid, name, site_xmlid, post_type_xmlid, guard_count in post_specs:
            site = self.ref(site_xmlid)
            self.get_or_create(
                xmlid,
                "security.post",
                {
                    "name": name,
                    "code": xmlid.upper(),
                    "site_id": site.id,
                    "partner_id": site.partner_id.id,
                    "post_type_id": self.ref(post_type_xmlid).id,
                    "required_guard_count": guard_count,
                },
            )

        # ---- Shift requirements (day + night per key site) ----
        requirements = [
            # Bank Windhoek HQ
            ("req_bw_hq_gate_day",    "post_bw_hq_gate",      "shift_day",      2, 540.0, 15.0, 1.0),
            ("req_bw_hq_gate_night",  "post_bw_hq_gate",      "shift_night",    2, 620.0, 15.0, 1.2),
            ("req_bw_hq_control_day", "post_bw_hq_control",   "shift_day",      1, 680.0, 13.5, 1.0),
            ("req_bw_armed_day",      "post_bw_hq_armed",     "shift_day",      1, 850.0, 15.0, 1.4),
            # NBL Brewery
            ("req_nbl_brewery_gate_day",   "post_nbl_brewery_gate",  "shift_day",  2, 520.0, 13.5, 1.0),
            ("req_nbl_brewery_gate_night", "post_nbl_brewery_gate",  "shift_night",2, 600.0, 13.5, 1.2),
            ("req_nbl_armed_day",          "post_nbl_brewery_armed", "shift_day",  1, 800.0, 15.0, 1.4),
            # NWR HQ
            ("req_nwr_hq_gate_day",   "post_nwr_hq_gate",     "shift_day",      2, 510.0, 13.5, 1.0),
            ("req_nwr_hq_gate_night", "post_nwr_hq_gate",     "shift_night",    2, 590.0, 13.5, 1.2),
            ("req_nwr_hq_cctv_day",   "post_nwr_hq_cctv",     "shift_day",      1, 640.0, 13.5, 1.0),
            # NWR Swakop
            ("req_nwr_swakop_gate_day",  "post_nwr_swakop_gate",  "shift_day",   2, 490.0, 12.0, 1.0),
            ("req_nwr_swakop_gate_night","post_nwr_swakop_gate",  "shift_night",  1, 560.0, 12.0, 1.2),
            # MTC HQ
            ("req_mtc_hq_gate_day",   "post_mtc_hq_gate",     "shift_day",      2, 530.0, 13.5, 1.0),
            ("req_mtc_hq_gate_night", "post_mtc_hq_gate",     "shift_night",    1, 610.0, 13.5, 1.2),
            ("req_mtc_vip_business",  "post_mtc_hq_vip",      "shift_business", 1, 950.0, 15.0, 1.5),
            # Old Mutual
            ("req_om_hq_gate_day",    "post_om_hq_gate",      "shift_day",      2, 520.0, 13.5, 1.0),
            ("req_om_hq_control_day", "post_om_hq_control",   "shift_day",      1, 660.0, 13.5, 1.0),
            # Standard Bank HQ
            ("req_sb_hq_gate_day",    "post_sb_hq_gate",      "shift_day",      2, 540.0, 13.5, 1.0),
            ("req_sb_hq_gate_night",  "post_sb_hq_gate",      "shift_night",    2, 620.0, 13.5, 1.2),
            ("req_sb_armed_day",      "post_sb_hq_armed",     "shift_day",      1, 840.0, 15.0, 1.4),
            # City of Windhoek
            ("req_cow_municipal_day",  "post_cow_municipal_gate","shift_day",    2, 500.0, 12.0, 1.0),
            ("req_cow_sewage_day",     "post_cow_sewage_gate",   "shift_day",    1, 480.0, 12.0, 1.0),
            # NamPower
            ("req_np_hq_gate_day",     "post_np_hq_gate",      "shift_day",     2, 530.0, 13.5, 1.0),
            ("req_np_hq_gate_night",   "post_np_hq_gate",      "shift_night",   2, 610.0, 13.5, 1.2),
            ("req_np_substation_day",  "post_np_substation_gate","shift_day",   1, 820.0, 15.0, 1.4),
            # ShopRite
            ("req_sr_wernhil_day",    "post_sr_wernhil_gate",  "shift_day",     2, 490.0, 12.0, 1.0),
            ("req_sr_wernhil_night",  "post_sr_wernhil_gate",  "shift_night",   1, 560.0, 12.0, 1.2),
            # Game City
            ("req_gc_mall_day",       "post_gc_mall_gate",     "shift_day",     3, 510.0, 12.0, 1.0),
            ("req_gc_mall_night",     "post_gc_mall_gate",     "shift_night",   2, 590.0, 12.0, 1.2),
            ("req_gc_parking_day",    "post_gc_parking_gate",  "shift_day",     2, 480.0, 12.0, 1.0),
        ]
        for xmlid, post_xmlid, shift_xmlid, guards, bill_rate, pay_rate, fairness in requirements:
            post = self.ref(post_xmlid)
            values = {
                "site_id": post.site_id.id,
                "post_id": post.id,
                "shift_template_id": self.ref(shift_xmlid).id,
                "guard_count": guards,
                "bill_rate": bill_rate,
                "pay_rate": pay_rate,
                "fairness_weight": fairness,
                "minimum_reliability_score": 70,
            }
            if shift_xmlid == "shift_business":
                values.update({"saturday": False, "sunday": False})
            self.get_or_create(xmlid, "security.shift.requirement", values)

        # Backward-compat requirement aliases used in original roster code
        req_alias_map = {
            "req_bank_gate_day":              "req_bw_hq_gate_day",
            "req_bank_gate_night":            "req_bw_hq_gate_night",
            "req_bank_control_day":           "req_bw_hq_control_day",
            "req_breweries_gate_day":         "req_nbl_brewery_gate_day",
            "req_nwr_windhoek_gate_day":      "req_nwr_hq_gate_day",
            "req_nwr_windhoek_cctv_afternoon":"req_nwr_hq_cctv_day",
        }
        for old_xmlid, new_xmlid in req_alias_map.items():
            if not self.ref(old_xmlid):
                target = self.ref(new_xmlid)
                if target:
                    self.env["ir.model.data"].create({
                        "module": MODULE,
                        "name": old_xmlid,
                        "model": "security.shift.requirement",
                        "res_id": target.id,
                        "noupdate": True,
                    })

    # ------------------------------------------------------------------
    # 4. GUARDS — 60 guards with varied grades, scores, certs
    # ------------------------------------------------------------------

    def _create_guards(self):
        # Helper: build guard vals dict
        def gv(name, grade_xmlid, score, hourly_rate, ssc, tax,
               ec_name, ec_phone, ec_rel, bank, account,
               disqualified=False):
            vals = {
                "name": name,
                "work_email": f"{ssc.lower()}@dogforce-demo.na",
                "mobile_phone": ec_phone,
                "security_guard": True,
                "security_grade_id": self.ref(grade_xmlid).id,
                "security_hourly_rate": hourly_rate,
                "security_reliability_score": score,
                "security_home_location": "Windhoek, Namibia",
                "security_ssc_number": ssc,
                "security_tax_number": tax,
                "security_emergency_contact_name": ec_name,
                "security_emergency_contact_phone": ec_phone,
                "security_emergency_contact_relationship": ec_rel,
                "security_bank_name": bank,
                "security_bank_account_number": account,
                "security_language_ids": [(6, 0, [self.ref("lang_english").id])],
                "security_certification_ids": [(6, 0, [])],
                "security_attribute_ids": [(6, 0, [])],
            }
            if disqualified and "security_disqualified" in self.env["hr.employee"]._fields:
                vals["security_disqualified"] = True
            elif "security_disqualified" in self.env["hr.employee"]._fields:
                vals["security_disqualified"] = False
            return vals

        # fmt: off

        # ---- Grade A (8 guards, rate 15.00) ----
        grade_a_guards = [
            ("guard_a01", "Tobias Nghipandulwa",  95, "SSCA0126", "TAXA0126", "Ndapewa Nghipandulwa", "+264 81 234 5678", "Spouse",  "Bank Windhoek",        "4512378901"),
            ("guard_a02", "Frieda Hamutenya",      93, "SSCA0226", "TAXA0226", "Johannes Hamutenya",  "+264 81 345 6789", "Spouse",  "FNB Namibia",          "3628475910"),
            ("guard_a03", "Willem Petrus",         91, "SSCA0326", "TAXA0326", "Anna Petrus",         "+264 81 456 7890", "Spouse",  "Standard Bank Namibia","2734561820"),
            ("guard_a04", "Ndapewa Iipinge",       89, "SSCA0426", "TAXA0426", "Simon Iipinge",       "+264 81 567 8901", "Spouse",  "Bank Windhoek",        "1840652730"),
            ("guard_a05", "Festus Shilongo",       94, "SSCA0526", "TAXA0526", "Maria Shilongo",      "+264 81 678 9012", "Spouse",  "FNB Namibia",          "0956743640"),
            ("guard_a06", "Johanna Namhila",       90, "SSCA0626", "TAXA0626", "David Namhila",       "+264 81 789 0123", "Spouse",  "Standard Bank Namibia","9062834550"),
            ("guard_a07", "Toivo Nekwaya",         88, "SSCA0726", "TAXA0726", "Helena Nekwaya",      "+264 81 890 1234", "Spouse",  "Bank Windhoek",        "8178925460"),
            ("guard_a08", "Samuel Katjivena",      92, "SSCA0826", "TAXA0826", "Frieda Katjivena",    "+264 81 901 2345", "Spouse",  "FNB Namibia",          "7284016370"),
        ]
        for xmlid, name, score, ssc, tax, ec_name, ec_phone, ec_rel, bank, account in grade_a_guards:
            self.get_or_create(
                xmlid, "hr.employee",
                gv(name, "grade_a", score, 15.0, ssc, tax, ec_name, ec_phone, ec_rel, bank, account),
            )

        # ---- Grade B (12 guards, rate 13.50) ----
        grade_b_guards = [
            ("guard_b01", "Maria Ndilula",     85, "SSCB0126", "TAXB0126", "Petrus Ndilula",     "+264 81 112 3456", "Spouse",  "Bank Windhoek",        "6390107280"),
            ("guard_b02", "Petrus Kambonde",   83, "SSCB0226", "TAXB0226", "Hilma Kambonde",     "+264 81 223 4567", "Spouse",  "FNB Namibia",          "5486198190"),
            ("guard_b03", "Hilma Amutenya",    87, "SSCB0326", "TAXB0326", "Thomas Amutenya",    "+264 81 334 5678", "Spouse",  "Standard Bank Namibia","4572289100"),
            ("guard_b04", "David Paulus",      82, "SSCB0426", "TAXB0426", "Grace Paulus",       "+264 81 445 6789", "Spouse",  "Bank Windhoek",        "3668370010"),
            ("guard_b05", "Grace Beukes",      84, "SSCB0526", "TAXB0526", "Jacobus Beukes",     "+264 81 556 7890", "Spouse",  "FNB Namibia",          "2754460920"),
            ("guard_b06", "Thomas Fillemon",   81, "SSCB0626", "TAXB0626", "Selma Fillemon",     "+264 81 667 8901", "Spouse",  "Standard Bank Namibia","1840551830"),
            ("guard_b07", "Emma Hoebeb",       86, "SSCB0726", "TAXB0726", "Absalom Hoebeb",     "+264 81 778 9012", "Spouse",  "Bank Windhoek",        "0936642740"),
            ("guard_b08", "Benjamin Simon",    80, "SSCB0826", "TAXB0826", "Frieda Simon",       "+264 81 889 0123", "Spouse",  "FNB Namibia",          "9022733650"),
            ("guard_b09", "Francina Gariseb",  85, "SSCB0926", "TAXB0926", "David Gariseb",      "+264 81 990 1234", "Sibling", "Standard Bank Namibia","8118824560"),
            ("guard_b10", "Hendrik Uanivi",    83, "SSCB1026", "TAXB1026", "Anna Uanivi",        "+264 81 101 2345", "Spouse",  "Bank Windhoek",        "7204915470"),
            ("guard_b11", "Rebecca Goagoseb",  82, "SSCB1126", "TAXB1126", "Paulus Goagoseb",    "+264 81 202 3456", "Spouse",  "FNB Namibia",          "6390006380"),
            ("guard_b12", "Magano Veii",       88, "SSCB1226", "TAXB1226", "Maria Veii",         "+264 81 303 4567", "Parent",  "Standard Bank Namibia","5486197290"),
        ]
        for xmlid, name, score, ssc, tax, ec_name, ec_phone, ec_rel, bank, account in grade_b_guards:
            self.get_or_create(
                xmlid, "hr.employee",
                gv(name, "grade_b", score, 13.5, ssc, tax, ec_name, ec_phone, ec_rel, bank, account),
            )

        # ---- Grade C (18 guards, rate 12.00) ----
        grade_c_guards = [
            ("guard_c01", "Abraham Nekwaya",     78, "SSCC0126", "TAXC0126", "Selma Nekwaya",       "+264 81 404 5678", "Spouse",  "Bank Windhoek",        "4572348200"),
            ("guard_c02", "Susanna Khaxas",      76, "SSCC0226", "TAXC0226", "Simon Khaxas",        "+264 81 505 6789", "Spouse",  "FNB Namibia",          "3668439110"),
            ("guard_c03", "Johannes Tjikuua",    80, "SSCC0326", "TAXC0326", "Maria Tjikuua",       "+264 81 606 7890", "Spouse",  "Standard Bank Namibia","2754530020"),
            ("guard_c04", "Rachel Muniombara",   75, "SSCC0426", "TAXC0426", "Paulus Muniombara",   "+264 81 707 8901", "Spouse",  "Bank Windhoek",        "1840620930"),
            ("guard_c05", "Elias Nghipandulwa",  79, "SSCC0526", "TAXC0526", "Anna Nghipandulwa",   "+264 81 818 9012", "Parent",  "FNB Namibia",          "0936711840"),
            ("guard_c06", "Anna Shilongo",       74, "SSCC0626", "TAXC0626", "Thomas Shilongo",     "+264 81 929 0123", "Spouse",  "Standard Bank Namibia","9022802750"),
            ("guard_c07", "Petrus Hamutenya",    77, "SSCC0726", "TAXC0726", "Frieda Hamutenya",    "+264 81 131 2345", "Sibling", "Bank Windhoek",        "8118893660"),
            ("guard_c08", "Martha Iipinge",      73, "SSCC0826", "TAXC0826", "David Iipinge",       "+264 81 242 3456", "Spouse",  "FNB Namibia",          "7204984570"),
            ("guard_c09", "Simon Ndilula",       78, "SSCC0926", "TAXC0926", "Grace Ndilula",       "+264 81 353 4567", "Spouse",  "Standard Bank Namibia","6390075480"),
            ("guard_c10", "Frieda Kambonde",     76, "SSCC1026", "TAXC1026", "Petrus Kambonde",     "+264 81 464 5678", "Spouse",  "Bank Windhoek",        "5486166390"),
            ("guard_c11", "Daniel Namhila",      81, "SSCC1126", "TAXC1126", "Selma Namhila",       "+264 81 575 6789", "Spouse",  "FNB Namibia",          "4572257300"),
            ("guard_c12", "Selma Nekwaya",       75, "SSCC1226", "TAXC1226", "Johannes Nekwaya",    "+264 81 686 7890", "Spouse",  "Standard Bank Namibia","3668348210"),
            ("guard_c13", "Immanuel Amutenya",   79, "SSCC1326", "TAXC1326", "Hilma Amutenya",      "+264 81 797 8901", "Sibling", "Bank Windhoek",        "2754439120"),
            ("guard_c14", "Hilde Paulus",        74, "SSCC1426", "TAXC1426", "David Paulus",        "+264 81 808 9012", "Spouse",  "FNB Namibia",          "1840530030"),
            ("guard_c15", "Ndapewa Beukes",      77, "SSCC1526", "TAXC1526", "Simon Beukes",        "+264 81 919 0123", "Spouse",  "Standard Bank Namibia","0936620940"),
            ("guard_c16", "Timoteus Hoebeb",     80, "SSCC1626", "TAXC1626", "Emma Hoebeb",         "+264 81 121 2345", "Parent",  "Bank Windhoek",        "9022711850"),
            ("guard_c17", "Albertina Gariseb",   73, "SSCC1726", "TAXC1726", "Johannes Gariseb",    "+264 81 232 3456", "Spouse",  "FNB Namibia",          "8118802760"),
            ("guard_c18", "Festus Katjivena",    76, "SSCC1826", "TAXC1826", "Maria Katjivena",     "+264 81 343 4567", "Spouse",  "Standard Bank Namibia","7204893670"),
        ]
        for xmlid, name, score, ssc, tax, ec_name, ec_phone, ec_rel, bank, account in grade_c_guards:
            self.get_or_create(
                xmlid, "hr.employee",
                gv(name, "grade_c", score, 12.0, ssc, tax, ec_name, ec_phone, ec_rel, bank, account),
            )

        # ---- Grade D (15 guards, rate 11.00) ----
        grade_d_guards = [
            ("guard_d01", "Joseph Fillemon",     70, "SSCD0126", "TAXD0126", "Maria Fillemon",      "+264 81 454 5678", "Spouse",  "Bank Windhoek",        "6390157580"),
            ("guard_d02", "Maria Simon",         68, "SSCD0226", "TAXD0226", "Petrus Simon",        "+264 81 565 6789", "Spouse",  "FNB Namibia",          "5486248490"),
            ("guard_d03", "Gottlieb Veii",       72, "SSCD0326", "TAXD0326", "Selma Veii",          "+264 81 676 7890", "Sibling", "Standard Bank Namibia","4572339400"),
            ("guard_d04", "Helvi Uanivi",        69, "SSCD0426", "TAXD0426", "Johannes Uanivi",     "+264 81 787 8901", "Spouse",  "Bank Windhoek",        "3668430310"),
            ("guard_d05", "Paulus Tjikuua",      71, "SSCD0526", "TAXD0526", "Maria Tjikuua",       "+264 81 898 9012", "Spouse",  "FNB Namibia",          "2754521220"),
            ("guard_d06", "Selina Goagoseb",     67, "SSCD0626", "TAXD0626", "Absalom Goagoseb",    "+264 81 909 0123", "Spouse",  "Standard Bank Namibia","1840612130"),
            ("guard_d07", "Absalom Khaxas",      70, "SSCD0726", "TAXD0726", "Susanna Khaxas",      "+264 81 020 1234", "Spouse",  "Bank Windhoek",        "0936703040"),
            ("guard_d08", "Frieda Nekwaya",      68, "SSCD0826", "TAXD0826", "Abraham Nekwaya",     "+264 81 131 2345", "Spouse",  "FNB Namibia",          "9022793950"),
            ("guard_d09", "Johannes Muniombara", 72, "SSCD0926", "TAXD0926", "Rachel Muniombara",   "+264 81 242 3456", "Sibling", "Standard Bank Namibia","8118884860"),
            ("guard_d10", "Anna Nghipandulwa",   69, "SSCD1026", "TAXD1026", "Tobias Nghipandulwa", "+264 81 353 4567", "Spouse",  "Bank Windhoek",        "7204975770"),
            ("guard_d11", "Simon Iipinge",       71, "SSCD1126", "TAXD1126", "Ndapewa Iipinge",     "+264 81 464 5678", "Spouse",  "FNB Namibia",          "6390066680"),
            ("guard_d12", "Martha Shilongo",     67, "SSCD1226", "TAXD1226", "Festus Shilongo",     "+264 81 575 6789", "Spouse",  "Standard Bank Namibia","5486157590"),
            ("guard_d13", "Elias Namhila",       70, "SSCD1326", "TAXD1326", "Daniel Namhila",      "+264 81 686 7890", "Sibling", "Bank Windhoek",        "4572248500"),
            ("guard_d14", "Rebecca Ndilula",     68, "SSCD1426", "TAXD1426", "Simon Ndilula",       "+264 81 797 8901", "Spouse",  "FNB Namibia",          "3668339410"),
            ("guard_d15", "Daniel Kambonde",     73, "SSCD1526", "TAXD1526", "Petrus Kambonde",     "+264 81 808 9012", "Spouse",  "Standard Bank Namibia","2754430320"),
        ]
        for xmlid, name, score, ssc, tax, ec_name, ec_phone, ec_rel, bank, account in grade_d_guards:
            self.get_or_create(
                xmlid, "hr.employee",
                gv(name, "grade_d", score, 11.0, ssc, tax, ec_name, ec_phone, ec_rel, bank, account),
            )

        # ---- Grade E (7 guards, rate 10.00, 2 disqualified) ----
        grade_e_guards = [
            ("guard_e01", "Petrus Amutenya",  65, "SSCE0126", "TAXE0126", "Hilma Amutenya",    "+264 81 919 0123", "Spouse",  "Bank Windhoek",        "1840521230", False),
            ("guard_e02", "Maria Paulus",     67, "SSCE0226", "TAXE0226", "David Paulus",      "+264 81 020 1234", "Spouse",  "FNB Namibia",          "0936612140", False),
            ("guard_e03", "Johannes Beukes",  66, "SSCE0326", "TAXE0326", "Grace Beukes",      "+264 81 131 2345", "Parent",  "Standard Bank Namibia","9022703050", False),
            ("guard_e04", "Hilma Hoebeb",     65, "SSCE0426", "TAXE0426", "Emma Hoebeb",       "+264 81 242 3456", "Sibling", "Bank Windhoek",        "8118793960", False),
            ("guard_e05", "David Gariseb",    68, "SSCE0526", "TAXE0526", "Francina Gariseb",  "+264 81 353 4567", "Spouse",  "FNB Namibia",          "7204884870", False),
            ("guard_e06", "Emma Katjivena",   40, "SSCE0626", "TAXE0626", "Thomas Katjivena",  "+264 81 464 5678", "Spouse",  "Standard Bank Namibia","6390975780", True),
            ("guard_e07", "Thomas Veii",      38, "SSCE0726", "TAXE0726", "Maria Veii",        "+264 81 575 6789", "Spouse",  "Bank Windhoek",        "5486066690", True),
        ]
        for xmlid, name, score, ssc, tax, ec_name, ec_phone, ec_rel, bank, account, dq in grade_e_guards:
            self.get_or_create(
                xmlid, "hr.employee",
                gv(name, "grade_e", score, 10.0, ssc, tax, ec_name, ec_phone, ec_rel, bank, account, disqualified=dq),
            )

        # fmt: on

        # ---- Backward-compat aliases for original guard xmlids still used elsewhere ----
        old_to_new = {
            # Original Grade A
            "guard_johannes":   "guard_a05",   # Festus/Johannes both Grade A armed
            "guard_festus":     "guard_a05",
            "guard_albertina":  "guard_a06",
            # Original Grade B
            "guard_selma":      "guard_b01",
            "guard_ester":      "guard_b03",
            "guard_david":      "guard_b04",
            # Original Grade C
            "guard_petrus":     "guard_c01",
            "guard_maria":      "guard_c04",
            "guard_hilma":      "guard_c03",
            "guard_joseph":     "guard_c09",
            # Original Grade D
            "guard_tomas":      "guard_d01",
            "guard_anna":       "guard_d04",
            "guard_paulus":     "guard_d05",
            # Original Grade E
            "guard_simon":      "guard_e01",
            "guard_rachel_dq":  "guard_e06",
        }
        for old_xmlid, new_xmlid in old_to_new.items():
            if not self.ref(old_xmlid):
                target = self.ref(new_xmlid)
                if target:
                    self.env["ir.model.data"].create({
                        "module": MODULE,
                        "name": old_xmlid,
                        "model": "hr.employee",
                        "res_id": target.id,
                        "noupdate": True,
                    })

        # Assign post-type-required attributes to guards that will be placed
        # on attributed posts in the demo rosters.
        ctrl = self.ref("attr_control_room")
        vip  = self.ref("attr_vip_protection")
        if ctrl:
            for xmlid in ["guard_b01", "guard_b03", "guard_b07", "guard_b12"]:
                g = self.ref(xmlid)
                if g:
                    g.write({"security_attribute_ids": [(4, ctrl.id)]})
        if vip:
            for xmlid in ["guard_a01", "guard_a02", "guard_a03", "guard_a04"]:
                g = self.ref(xmlid)
                if g:
                    g.write({"security_attribute_ids": [(4, vip.id)]})

    # ------------------------------------------------------------------
    # 5. DOCUMENTS AND LEAVE
    # ------------------------------------------------------------------

    def _create_documents_and_leave(self):
        # Employee documents (firearm certs, ID docs)
        doc_model = self.env.get("security.employee.document")
        if doc_model is not None:
            # Map doc_name → document_type xmlid
            _dtype = {
                "Firearm Competency Certificate": "doctype_firearm",
                "Namibian ID Document":           "doctype_id",
                "CCTV Operations Certificate":    "doctype_cctv",
                "First Aid Certificate":          "doctype_first_aid",
            }
            doc_records = [
                ("doc_a05_firearm",   "guard_a05", "Firearm Competency Certificate", "2026-04-15", "2028-04-14"),
                ("doc_a01_firearm",   "guard_a01", "Firearm Competency Certificate", "2026-03-10", "2028-03-09"),
                ("doc_a06_firearm",   "guard_a06", "Firearm Competency Certificate", "2025-11-20", "2027-11-19"),
                ("doc_c01_id",        "guard_c01", "Namibian ID Document",           "2020-06-01", False),
                ("doc_b01_cctv",      "guard_b01", "CCTV Operations Certificate",    "2025-09-05", "2027-09-04"),
                ("doc_c03_first_aid", "guard_c03", "First Aid Certificate",          "2025-08-12", "2027-08-11"),
                ("doc_a08_firearm",   "guard_a08", "Firearm Competency Certificate", "2026-02-01", "2028-01-31"),
                ("doc_b12_cctv",      "guard_b12", "CCTV Operations Certificate",    "2025-10-12", "2027-10-11"),
            ]
            for xmlid, guard_xmlid, doc_name, issue_date, expiry_date in doc_records:
                dtype_xmlid = _dtype.get(doc_name, "doctype_id")
                dtype_rec = self.env.ref(f"security_demo_data.{dtype_xmlid}", raise_if_not_found=False)
                if not dtype_rec:
                    continue
                vals = {
                    "employee_id": self.ref(guard_xmlid).id,
                    "document_type_id": dtype_rec.id,
                    "name": doc_name,
                    "issue_date": issue_date,
                }
                if expiry_date:
                    vals["expiry_date"] = expiry_date
                self.get_or_create(xmlid, "security.employee.document", vals)

        # Leave requests
        leave_model = self.env.get("security.leave.request")
        leave_type_model = self.env.get("security.leave.type")
        if leave_model is not None and leave_type_model is not None:
            # Ensure leave types exist
            lt_annual = leave_type_model.search([("name", "ilike", "Annual")], limit=1) or \
                        leave_type_model.create({"name": "Annual Leave", "code": "AL"})
            lt_sick = leave_type_model.search([("name", "ilike", "Sick")], limit=1) or \
                      leave_type_model.create({"name": "Sick Leave", "code": "SL"})
            lt_family = leave_type_model.search([("name", "ilike", "Family")], limit=1) or \
                        leave_type_model.create({"name": "Family Responsibility Leave", "code": "FRL"})
            _lt_map = {
                "Annual Leave": lt_annual.id,
                "Sick Leave": lt_sick.id,
                "Family Responsibility Leave": lt_family.id,
            }
            leave_records = [
                ("leave_c01_annual",  "guard_c01", "2026-05-11", "2026-05-15", "Annual Leave",               "draft"),
                ("leave_c04_sick",    "guard_c04", "2026-05-06", "2026-05-07", "Sick Leave",                 "draft"),
                ("leave_d01_family",  "guard_d01", "2026-05-20", "2026-05-22", "Family Responsibility Leave", "draft"),
                ("leave_d04_annual",  "guard_d04", "2026-06-01", "2026-06-05", "Annual Leave",               "refused"),
                ("leave_b02_sick",    "guard_b02", "2026-05-13", "2026-05-14", "Sick Leave",                 "draft"),
                ("leave_a07_annual",  "guard_a07", "2026-06-10", "2026-06-14", "Annual Leave",               "draft"),
            ]
            for xmlid, guard_xmlid, date_from, date_to, leave_type_name, state in leave_records:
                lt_id = _lt_map.get(leave_type_name)
                if not lt_id:
                    continue
                self.get_or_create(
                    xmlid,
                    "security.leave.request",
                    {
                        "employee_id": self.ref(guard_xmlid).id,
                        "date_from": date_from,
                        "date_to": date_to,
                        "leave_type_id": lt_id,
                        "state": state,
                    },
                )

    # ------------------------------------------------------------------
    # 6. ROSTERS AND ATTENDANCE — 3 batches
    # ------------------------------------------------------------------

    def _create_rosters_and_attendance(self):
        # Batch 1 — Bank Windhoek HQ — 14 days — 5 guards from grades A-C
        batch1 = self.get_or_create(
            "roster_may_2026_bank_hq",
            "security.roster.batch",
            {
                "date_from": "2026-05-01",
                "date_to": "2026-05-14",
                "partner_id": self.ref("client_bank_windhoek").id,
                "site_id": self.ref("site_bw_hq").id,
                "note": "Demo two-week roster — Bank Windhoek HQ, May 2026.",
            },
        )
        bank_guards = [
            self.ref("guard_a01"),
            self.ref("guard_b01"),
            self.ref("guard_b03"),
            self.ref("guard_c01"),
            self.ref("guard_c03"),
        ]
        slot_index = 0
        for day_offset in range(14):
            shift_date = date(2026, 5, 1) + timedelta(days=day_offset)
            for requirement_xmlid in ["req_bw_hq_gate_day", "req_bw_hq_gate_night", "req_bw_hq_control_day"]:
                requirement = self.ref(requirement_xmlid)
                for slot_number in range(1, requirement.guard_count + 1):
                    guard = bank_guards[slot_index % len(bank_guards)]
                    if requirement_xmlid == "req_bw_hq_control_day":
                        guard = self.ref("guard_b01") if day_offset % 2 == 0 else self.ref("guard_b03")
                    slot = self.get_or_create(
                        f"slot_b1_{requirement_xmlid}_{shift_date.isoformat()}_{slot_number}",
                        "security.roster.slot",
                        {
                            "batch_id": batch1.id,
                            "slot_number": slot_number,
                            "shift_date": shift_date.isoformat(),
                            "shift_requirement_id": requirement.id,
                            "post_id": requirement.post_id.id,
                            "shift_template_id": requirement.shift_template_id.id,
                            "employee_id": guard.id,
                            "state": "confirmed",
                        },
                    )
                    self._create_attendance_for_slot(slot, day_offset, slot_index, batch_tag="b1")
                    slot_index += 1
        batch1.state = "confirmed"

        # Batch 2 — NBL Brewery Plant — 14 days — 5 guards from grades B-C
        batch2 = self.get_or_create(
            "roster_may_2026_nbl_brewery",
            "security.roster.batch",
            {
                "date_from": "2026-05-01",
                "date_to": "2026-05-14",
                "partner_id": self.ref("client_namibia_breweries").id,
                "site_id": self.ref("site_nbl_brewery").id,
                "note": "Demo two-week roster — NBL Brewery Plant, May 2026.",
            },
        )
        brew_guards = [
            self.ref("guard_b05"),
            self.ref("guard_b06"),
            self.ref("guard_c05"),
            self.ref("guard_c06"),
            self.ref("guard_c07"),
        ]
        slot_index2 = 0
        for day_offset in range(14):
            shift_date = date(2026, 5, 1) + timedelta(days=day_offset)
            for requirement_xmlid in ["req_nbl_brewery_gate_day", "req_nbl_brewery_gate_night"]:
                requirement = self.ref(requirement_xmlid)
                for slot_number in range(1, requirement.guard_count + 1):
                    guard = brew_guards[slot_index2 % len(brew_guards)]
                    slot = self.get_or_create(
                        f"slot_b2_{requirement_xmlid}_{shift_date.isoformat()}_{slot_number}",
                        "security.roster.slot",
                        {
                            "batch_id": batch2.id,
                            "slot_number": slot_number,
                            "shift_date": shift_date.isoformat(),
                            "shift_requirement_id": requirement.id,
                            "post_id": requirement.post_id.id,
                            "shift_template_id": requirement.shift_template_id.id,
                            "employee_id": guard.id,
                            "state": "confirmed",
                        },
                    )
                    self._create_attendance_for_slot(slot, day_offset, slot_index2, batch_tag="b2")
                    slot_index2 += 1
        batch2.state = "confirmed"

        # Batch 3 — NWR Swakopmund — 7 days — 3 guards
        batch3 = self.get_or_create(
            "roster_may_2026_nwr_swakop",
            "security.roster.batch",
            {
                "date_from": "2026-05-01",
                "date_to": "2026-05-07",
                "partner_id": self.ref("client_nwr").id,
                "site_id": self.ref("site_nwr_swakop").id,
                "note": "Demo roster — NWR Swakopmund Resort, May 2026.",
            },
        )
        nwr_guards = [
            self.ref("guard_b07"),
            self.ref("guard_c08"),
            self.ref("guard_c09"),
        ]
        slot_index3 = 0
        for day_offset in range(7):
            shift_date = date(2026, 5, 1) + timedelta(days=day_offset)
            for requirement_xmlid in ["req_nwr_swakop_gate_day", "req_nwr_swakop_gate_night"]:
                requirement = self.ref(requirement_xmlid)
                for slot_number in range(1, requirement.guard_count + 1):
                    guard = nwr_guards[slot_index3 % len(nwr_guards)]
                    slot = self.get_or_create(
                        f"slot_b3_{requirement_xmlid}_{shift_date.isoformat()}_{slot_number}",
                        "security.roster.slot",
                        {
                            "batch_id": batch3.id,
                            "slot_number": slot_number,
                            "shift_date": shift_date.isoformat(),
                            "shift_requirement_id": requirement.id,
                            "post_id": requirement.post_id.id,
                            "shift_template_id": requirement.shift_template_id.id,
                            "employee_id": guard.id,
                            "state": "confirmed",
                        },
                    )
                    self._create_attendance_for_slot(slot, day_offset, slot_index3, batch_tag="b3")
                    slot_index3 += 1
        batch3.state = "confirmed"

    def _create_attendance_for_slot(self, slot, day_offset, slot_index, batch_tag=""):
        batch = self.get_or_create(
            f"attendance_batch_{batch_tag}_{slot.shift_date.isoformat()}",
            "security.attendance.batch",
            {
                "attendance_date": slot.shift_date.isoformat(),
                "partner_id": slot.partner_id.id,
                "site_id": slot.site_id.id,
                "roster_batch_id": slot.batch_id.id,
                "state": "reviewed",
            },
        )
        # 80% present, 10% late, 5% absent, 5% awol
        is_awol = day_offset == 3 and slot_index % 20 < 1          # ~5%
        is_absent = not is_awol and day_offset == 6 and slot_index % 20 < 1  # ~5%
        is_late = not is_awol and not is_absent and slot_index % 10 == 0     # ~10%
        is_early_departure = not is_awol and not is_absent and not is_late and day_offset == 6 and slot_index % 15 == 0
        is_overtime = day_offset in (5, 12) and slot_index % 4 == 0

        start = self._shift_datetime(slot.shift_date, slot.shift_template_id.start_hour)
        end = self._shift_datetime(slot.shift_date, slot.shift_template_id.end_hour)
        if end <= start:
            end += timedelta(days=1)

        if is_awol:
            manual_presence = "awol"
        elif is_absent:
            manual_presence = "absent"
        else:
            manual_presence = "present"

        vals = {
            "attendance_batch_id": batch.id,
            "roster_slot_id": slot.id,
            "manual_presence": manual_presence,
            "absence_type": "awol" if manual_presence == "awol" else ("no_show" if manual_presence == "absent" else "none"),
            "overtime_approved": is_overtime,
            "overtime_approval_note": "Demo approved operational handover overtime." if is_overtime else "",
        }
        if manual_presence == "present":
            check_in = start + timedelta(minutes=15 if is_late else 0)
            check_out = (
                end - timedelta(minutes=30) if is_early_departure
                else end + (timedelta(hours=2) if is_overtime else timedelta())
            )
            vals.update({"check_in": check_in, "check_out": check_out})
        self.get_or_create(f"attendance_{batch_tag}_{slot.id}", "security.attendance.record", vals)

    def _shift_datetime(self, shift_date, hour_float):
        hour = int(hour_float)
        minute = int(round((hour_float - hour) * 60))
        return datetime.combine(shift_date, time(hour=hour, minute=minute))

    # ------------------------------------------------------------------
    # 7. LOANS AND INCIDENTS
    # ------------------------------------------------------------------

    def _create_loans_and_incidents(self):
        # Loans
        loans = [
            ("loan_c01_uniform",   "guard_c01", "2026-05-01", 1200.0, 4,  "Uniform advance demo",              "active"),
            ("loan_c03_tools",     "guard_c03", "2026-05-01",  800.0, 3,  "Utility equipment loan demo",       "active"),
            ("loan_d01_transport", "guard_d01", "2026-04-01", 2400.0, 6,  "Transport arrangement loan demo",   "active"),
            ("loan_c09_emergency", "guard_c09", "2026-03-15", 5000.0, 12, "Emergency personal loan demo",      "active"),
            ("loan_b02_equipment", "guard_b02", "2026-04-15", 1800.0, 6,  "Radio equipment deposit loan demo", "active"),
            ("loan_d04_medical",   "guard_d04", "2026-05-05", 3200.0, 8,  "Medical emergency loan demo",       "active"),
            ("loan_a07_uniform",   "guard_a07", "2026-03-01",  900.0, 3,  "Protective gear advance demo",      "active"),
        ]
        for xmlid, guard_xmlid, start_date, amount, months, note, state in loans:
            self.get_or_create(
                xmlid,
                "security.employee.loan",
                {
                    "employee_id": self.ref(guard_xmlid).id,
                    "start_date": start_date,
                    "principal_amount": amount,
                    "repayment_months": months,
                    "note": note,
                    "state": state,
                },
            )

        # Incident types
        incident_types = [
            ("incident_type_late_posting",   "Late Posting / Parade Discipline", "LATE_POST",  75.0,  -3),
            ("incident_type_awol_first",     "AWOL First Offence",               "AWOL_1",    250.0, -10),
            ("incident_type_uniform",        "Uniform Non-Compliance",           "UNIFORM_NC",  50.0,  -2),
            ("incident_type_property_damage","Property Damage",                  "PROP_DMG",  500.0,  -8),
        ]
        for xmlid, name, code, deduction, delta in incident_types:
            self.get_or_create(
                xmlid,
                "security.incident.type",
                {
                    "name": name,
                    "code": code,
                    "deduction_amount": deduction,
                    "reliability_score_delta": delta,
                },
            )

        # Incident records
        incidents = [
            ("incident_c04_late",     "guard_c04",     "incident_type_late_posting",    "2026-05-06", "Demo record: late arrival at parade posting sheet.",                    "approved"),
            ("incident_e01_awol",     "guard_e01",     "incident_type_awol_first",      "2026-05-08", "Demo: guard absent without leave — first offence formal warning issued.", "approved"),
            ("incident_d05_uniform",  "guard_d05",     "incident_type_uniform",         "2026-05-12", "Demo: guard on duty without correct uniform — written warning.",          "approved"),
            ("incident_d01_late",     "guard_d01",     "incident_type_late_posting",    "2026-05-14", "Demo: late to post — verbal warning recorded.",                          "draft"),
            ("incident_d04_late",     "guard_d04",     "incident_type_late_posting",    "2026-05-03", "Demo: late posting at Breweries plant gate.",                            "draft"),
            ("incident_c09_damage",   "guard_c09",     "incident_type_property_damage", "2026-05-07", "Demo: guard damaged vehicle barrier at plant entrance.",                  "approved"),
            ("incident_c03_uniform",  "guard_c03",     "incident_type_uniform",         "2026-05-10", "Demo: incomplete uniform at morning parade — boots missing.",             "approved"),
            ("incident_e06_awol",     "guard_e06",     "incident_type_awol_first",      "2026-04-20", "Demo: repeated AWOL — escalation to disqualification review.",            "approved"),
            ("incident_b06_late",     "guard_b06",     "incident_type_late_posting",    "2026-05-18", "Demo: late posting at NBL Brewery gate — second incident.",              "draft"),
            ("incident_d09_uniform",  "guard_d09",     "incident_type_uniform",         "2026-05-22", "Demo: uniform non-compliance at City of Windhoek post.",                 "approved"),
            ("incident_e07_awol",     "guard_e07",     "incident_type_awol_first",      "2026-04-25", "Demo: guard absent without leave — disqualification triggered.",          "approved"),
        ]
        for xmlid, guard_xmlid, type_xmlid, incident_date, note, state in incidents:
            self.get_or_create(
                xmlid,
                "security.incident",
                {
                    "employee_id": self.ref(guard_xmlid).id,
                    "incident_type_id": self.ref(type_xmlid).id,
                    "incident_date": incident_date,
                    "note": note,
                    "state": state,
                },
            )

    # ------------------------------------------------------------------
    # 8. EQUIPMENT
    # ------------------------------------------------------------------

    def _create_equipment(self):
        uniform = self.get_or_create("equipment_cat_uniform", "security.equipment.category", {"name": "Uniforms", "code": "UNIFORM"})
        comms = self.get_or_create("equipment_cat_comms", "security.equipment.category", {"name": "Communications", "code": "COMMS"})
        firearms = self.get_or_create("equipment_cat_firearms", "security.equipment.category", {"name": "Firearms", "code": "FIREARM"})
        protective = self.get_or_create("equipment_cat_protective", "security.equipment.category", {"name": "Protective Equipment", "code": "PROTECT"})

        # Equipment types
        boots = self.get_or_create("equipment_type_boots", "security.equipment.type", {"name": "Combat Boots", "category_id": uniform.id, "qty_total": 40, "unit_cost": 650.0})
        radio = self.get_or_create("equipment_type_radio", "security.equipment.type", {"name": "Motorola Guard Radio", "category_id": comms.id, "is_serialized": True, "unit_cost": 2200.0})
        pistol = self.get_or_create("equipment_type_pistol", "security.equipment.type", {"name": "Licensed 9mm Pistol", "category_id": firearms.id, "is_serialized": True, "requires_license": True, "unit_cost": 9500.0})
        vest = self.get_or_create("equipment_type_vest", "security.equipment.type", {"name": "Bulletproof Vest", "category_id": protective.id, "is_serialized": True, "unit_cost": 5800.0})
        handcuffs = self.get_or_create("equipment_type_handcuffs", "security.equipment.type", {"name": "Handcuffs", "category_id": protective.id, "qty_total": 20, "unit_cost": 320.0})
        torch = self.get_or_create("equipment_type_torch", "security.equipment.type", {"name": "Torch/Flashlight", "category_id": protective.id, "qty_total": 50, "unit_cost": 180.0})

        # Serialized items
        radio_item = self.get_or_create("equipment_item_radio_001", "security.equipment.item", {"type_id": radio.id, "serial_number": "DF-RAD-NA-001", "condition": "good", "status": "available"})
        radio_item2 = self.get_or_create("equipment_item_radio_002", "security.equipment.item", {"type_id": radio.id, "serial_number": "DF-RAD-NA-002", "condition": "good", "status": "available"})
        pistol_item = self.get_or_create("equipment_item_pistol_001", "security.equipment.item", {"type_id": pistol.id, "serial_number": "DF-FIR-NA-001", "license_number": "NA-FAL-2026-001", "condition": "excellent", "status": "available"})
        vest_item = self.get_or_create("equipment_item_vest_001", "security.equipment.item", {"type_id": vest.id, "serial_number": "DF-VES-NA-001", "condition": "excellent", "status": "available"})
        vest_item2 = self.get_or_create("equipment_item_vest_002", "security.equipment.item", {"type_id": vest.id, "serial_number": "DF-VES-NA-002", "condition": "good", "status": "available"})

        # Allocations
        self.get_or_create("allocation_boots_c01", "security.equipment.allocation", {"employee_id": self.ref("guard_c01").id, "equipment_type_id": boots.id, "quantity": 1.0, "issue_date": "2026-05-01", "state": "issued"})
        self.get_or_create("allocation_boots_c03", "security.equipment.allocation", {"employee_id": self.ref("guard_c03").id, "equipment_type_id": boots.id, "quantity": 1.0, "issue_date": "2026-05-01", "state": "issued"})
        self.get_or_create("allocation_torch_d01", "security.equipment.allocation", {"employee_id": self.ref("guard_d01").id, "equipment_type_id": torch.id, "quantity": 1.0, "issue_date": "2026-05-01", "state": "issued"})
        self.get_or_create("allocation_handcuffs_a05", "security.equipment.allocation", {"employee_id": self.ref("guard_a05").id, "equipment_type_id": handcuffs.id, "quantity": 1.0, "issue_date": "2026-04-01", "state": "issued"})

        alloc_radio = self.get_or_create("allocation_radio_c04", "security.equipment.allocation", {"employee_id": self.ref("guard_c04").id, "equipment_type_id": radio.id, "equipment_item_id": radio_item.id, "quantity": 1.0, "issue_date": "2026-05-01"})
        if alloc_radio.state == "draft":
            alloc_radio.action_issue()

        alloc_radio2 = self.get_or_create("allocation_radio_b04", "security.equipment.allocation", {"employee_id": self.ref("guard_b04").id, "equipment_type_id": radio.id, "equipment_item_id": radio_item2.id, "quantity": 1.0, "issue_date": "2026-05-01"})
        if alloc_radio2.state == "draft":
            alloc_radio2.action_issue()

        alloc_vest = self.get_or_create("allocation_vest_a01", "security.equipment.allocation", {"employee_id": self.ref("guard_a01").id, "equipment_type_id": vest.id, "equipment_item_id": vest_item.id, "quantity": 1.0, "issue_date": "2026-04-01"})
        if alloc_vest.state == "draft":
            alloc_vest.action_issue()

        alloc_vest2 = self.get_or_create("allocation_vest_a05", "security.equipment.allocation", {"employee_id": self.ref("guard_a05").id, "equipment_type_id": vest.id, "equipment_item_id": vest_item2.id, "quantity": 1.0, "issue_date": "2026-04-01"})
        if alloc_vest2.state == "draft":
            alloc_vest2.action_issue()

        # Damage record for radio
        damage = self.get_or_create(
            "damage_radio_c04",
            "security.equipment.damage",
            {
                "allocation_id": alloc_radio.id,
                "occurrence_date": "2026-05-07",
                "incident_type": "damage",
                "description": "Demo: cracked radio casing after shift return.",
                "cost_repair_replace": 450.0,
                "deduction_amount": 150.0,
                "state": "investigation",
            },
        )
        if damage.state == "investigation":
            damage.action_approve()

    # ------------------------------------------------------------------
    # 9. FLEET
    # ------------------------------------------------------------------

    def _create_fleet(self):
        vehicle1 = self.get_or_create("vehicle_quantum_001", "security.vehicle", {"plate_number": "N 12345 W", "make": "Toyota", "model": "Quantum", "year": 2022, "capacity": 14, "odometer": 86200.0})
        vehicle2 = self.get_or_create("vehicle_hiace_001", "security.vehicle", {"plate_number": "N 54321 W", "make": "Toyota", "model": "Hiace", "year": 2021, "capacity": 12, "odometer": 112500.0})
        vehicle3 = self.get_or_create("vehicle_vw_transporter_001", "security.vehicle", {"plate_number": "N 67890 W", "make": "Volkswagen", "model": "Transporter", "year": 2023, "capacity": 9, "odometer": 34800.0})

        # Routes
        route1 = self.get_or_create("route_northern_pickup", "security.shuttle.route", {"name": "Windhoek Northern Pick-Up Circuit", "route_type": "pickup"})
        route2 = self.get_or_create("route_southern_pickup", "security.shuttle.route", {"name": "Southern Windhoek Circuit", "route_type": "pickup"})
        route3 = self.get_or_create("route_walvis_industrial", "security.shuttle.route", {"name": "Walvis Bay Industrial Route", "route_type": "pickup"})

        # Route 1 stops
        stops_r1 = [
            ("route_stop_depot",    1, "DogForce Depot - Windhoek",        "depot",  False,                        0),
            ("route_stop_katutura", 2, "Katutura Pick-Up Point",           "pickup", False,                       18),
            ("route_stop_bank_hq",  3, "Bank Windhoek HQ Drop-Off",        "site",   self.ref("site_bw_hq"),      35),
        ]
        for xmlid, sequence, label, stop_type, site, eta in stops_r1:
            self.get_or_create(xmlid, "security.shuttle.route.stop", {"route_id": route1.id, "sequence": sequence, "stop_label": label, "stop_type": stop_type, "site_id": site.id if site else False, "cumulative_duration_mins": eta})

        # Route 2 stops
        stops_r2 = [
            ("route_stop_depot_r2",  1, "DogForce Depot - Windhoek",       "depot",  False,                        0),
            ("route_stop_khomasdal", 2, "Khomasdal Pick-Up Point",         "pickup", False,                       20),
            ("route_stop_breweries", 3, "Namibia Breweries Drop-Off",       "site",   self.ref("site_nbl_brewery"),40),
        ]
        for xmlid, sequence, label, stop_type, site, eta in stops_r2:
            self.get_or_create(xmlid, "security.shuttle.route.stop", {"route_id": route2.id, "sequence": sequence, "stop_label": label, "stop_type": stop_type, "site_id": site.id if site else False, "cumulative_duration_mins": eta})

        # Route 3 stops
        stops_r3 = [
            ("route_stop_depot_r3",   1, "Walvis Bay Depot",                   "depot",  False,                        0),
            ("route_stop_lagoon",     2, "Lagoon Township Pick-Up",            "pickup", False,                       15),
            ("route_stop_walvis_port",3, "Walvis Bay Logistics Yard Drop-Off", "site",   self.ref("site_nbl_depot"),   30),
        ]
        for xmlid, sequence, label, stop_type, site, eta in stops_r3:
            self.get_or_create(xmlid, "security.shuttle.route.stop", {"route_id": route3.id, "sequence": sequence, "stop_label": label, "stop_type": stop_type, "site_id": site.id if site else False, "cumulative_duration_mins": eta})

        # Shuttle runs
        run1 = self.get_or_create("shuttle_run_2026_05_01", "security.shuttle.run", {"vehicle_id": vehicle1.id, "driver_id": self.ref("guard_a01").id, "route_id": route1.id, "shift_date": "2026-05-01", "scheduled_departure": "2026-05-01 04:45:00", "odometer_start": 86200.0, "odometer_end": 86238.0})
        for idx, guard_xmlid in enumerate(["guard_c01", "guard_c04", "guard_b01"], start=1):
            self.get_or_create(f"shuttle_passenger_r1_{guard_xmlid}", "security.shuttle.run.passenger", {"run_id": run1.id, "sequence": idx, "employee_id": self.ref(guard_xmlid).id, "boarding_stop_id": self.ref("route_stop_katutura").id, "status": "boarded"})

        run2 = self.get_or_create("shuttle_run_2026_05_01_r2", "security.shuttle.run", {"vehicle_id": vehicle2.id, "driver_id": self.ref("guard_a05").id, "route_id": route2.id, "shift_date": "2026-05-01", "scheduled_departure": "2026-05-01 04:30:00", "odometer_start": 112500.0, "odometer_end": 112544.0})
        for idx, guard_xmlid in enumerate(["guard_c05", "guard_c06", "guard_c07", "guard_d01"], start=1):
            self.get_or_create(f"shuttle_passenger_r2_{guard_xmlid}", "security.shuttle.run.passenger", {"run_id": run2.id, "sequence": idx, "employee_id": self.ref(guard_xmlid).id, "boarding_stop_id": self.ref("route_stop_khomasdal").id, "status": "boarded"})

        # Fuel logs
        self.get_or_create("fuel_quantum_may", "security.vehicle.fuel.log", {"vehicle_id": vehicle1.id, "fuel_date": "2026-05-02", "fueled_by_id": self.ref("guard_a01").id, "odometer_reading": 86290.0, "liters": 62.0, "cost_per_liter": 22.15, "fuel_station": "Engen Windhoek"})
        self.get_or_create("fuel_hiace_may", "security.vehicle.fuel.log", {"vehicle_id": vehicle2.id, "fuel_date": "2026-05-03", "fueled_by_id": self.ref("guard_a05").id, "odometer_reading": 112600.0, "liters": 55.0, "cost_per_liter": 22.15, "fuel_station": "Puma Windhoek North"})
        self.get_or_create("fuel_vw_may", "security.vehicle.fuel.log", {"vehicle_id": vehicle3.id, "fuel_date": "2026-05-04", "fueled_by_id": self.ref("guard_b04").id, "odometer_reading": 34900.0, "liters": 40.0, "cost_per_liter": 22.80, "fuel_station": "Engen Windhoek South"})

    # ------------------------------------------------------------------
    # 10. PAYROLL AND BILLING — all 10 clients
    # ------------------------------------------------------------------

    def _create_payroll_and_billing(self, nad):
        period = self.get_or_create(
            "payroll_period_may_2026",
            "security.payroll.period",
            {
                "date_from": "2026-05-01",
                "date_to": "2026-05-31",
                "rule_set_id": self.ref("rule_set_na_2026").id,
            },
        )
        period.action_generate_payslips()
        period.action_confirm_payslips()

        # ---- Billing plans for all 10 clients ----
        billing_plans = [
            ("billing_plan_bank_windhoek",   "client_bank_windhoek",    "Bank Windhoek Guarding Contract Demo"),
            ("billing_plan_nbl",             "client_namibia_breweries","NBL Brewery Guarding Contract Demo"),
            ("billing_plan_nwr",             "client_nwr",              "NWR Guarding Contract Demo"),
            ("billing_plan_mtc",             "client_mtc",              "MTC Namibia Guarding Contract Demo"),
            ("billing_plan_old_mutual",      "client_old_mutual",       "Old Mutual Guarding Contract Demo"),
            ("billing_plan_standard_bank",   "client_standard_bank",    "Standard Bank Guarding Contract Demo"),
            ("billing_plan_city_windhoek",   "client_city_windhoek",    "City of Windhoek Guarding Contract Demo"),
            ("billing_plan_nampower",        "client_nampower",         "NamPower Guarding Contract Demo"),
            ("billing_plan_shoprite",        "client_shoprite",         "ShopRite Namibia Guarding Contract Demo"),
            ("billing_plan_game_city",       "client_game_city",        "Game City Mall Guarding Contract Demo"),
        ]
        for xmlid, client_xmlid, name in billing_plans:
            self.get_or_create(
                xmlid,
                "security.billing.plan",
                {
                    "name": name,
                    "partner_id": self.ref(client_xmlid).id,
                    "currency_id": nad.id,
                    "billing_mode": "shift",
                    "date_start": "2026-05-01",
                    "payment_term_days": 30,
                    "vat_rate": 15.0,
                },
            )

        # ---- Plan lines ----
        plan_lines = [
            # Bank Windhoek
            ("bpl_bw_gate",     "billing_plan_bank_windhoek", "BW HQ gate guard per shift",        "post_bw_hq_gate",        540.0, 1, "shift_day"),
            ("bpl_bw_control",  "billing_plan_bank_windhoek", "BW HQ control room per shift",      "post_bw_hq_control",     680.0, 1, "shift_day"),
            # NBL
            ("bpl_nbl_gate",    "billing_plan_nbl",           "NBL brewery gate guard per shift",  "post_nbl_brewery_gate",  520.0, 2, "shift_day"),
            ("bpl_nbl_armed",   "billing_plan_nbl",           "NBL brewery armed post per shift",  "post_nbl_brewery_armed", 800.0, 1, "shift_day"),
            # NWR
            ("bpl_nwr_gate",    "billing_plan_nwr",           "NWR HQ gate guard per shift",       "post_nwr_hq_gate",       510.0, 2, "shift_day"),
            ("bpl_nwr_cctv",    "billing_plan_nwr",           "NWR HQ CCTV operator per shift",    "post_nwr_hq_cctv",       640.0, 1, "shift_day"),
            # MTC
            ("bpl_mtc_gate",    "billing_plan_mtc",           "MTC HQ gate guard per shift",       "post_mtc_hq_gate",       530.0, 2, "shift_day"),
            ("bpl_mtc_vip",     "billing_plan_mtc",           "MTC VIP escort per shift",          "post_mtc_hq_vip",        950.0, 1, "shift_business"),
            # Old Mutual
            ("bpl_om_gate",     "billing_plan_old_mutual",    "OM HQ gate guard per shift",        "post_om_hq_gate",        520.0, 2, "shift_day"),
            # Standard Bank
            ("bpl_sb_gate",     "billing_plan_standard_bank", "SB HQ gate guard per shift",        "post_sb_hq_gate",        540.0, 2, "shift_day"),
            ("bpl_sb_armed",    "billing_plan_standard_bank", "SB HQ armed post per shift",        "post_sb_hq_armed",       840.0, 1, "shift_day"),
            # City of Windhoek
            ("bpl_cow_mun",     "billing_plan_city_windhoek", "Municipal offices gate per shift",  "post_cow_municipal_gate",500.0, 2, "shift_day"),
            # NamPower
            ("bpl_np_gate",     "billing_plan_nampower",      "NamPower HQ gate per shift",        "post_np_hq_gate",        530.0, 2, "shift_day"),
            ("bpl_np_sub",      "billing_plan_nampower",      "Van Eck substation armed per shift","post_np_substation_gate",820.0, 1, "shift_day"),
            # ShopRite
            ("bpl_sr_gate",     "billing_plan_shoprite",      "ShopRite Wernhil gate per shift",   "post_sr_wernhil_gate",   490.0, 2, "shift_day"),
            # Game City
            ("bpl_gc_main",     "billing_plan_game_city",     "Game City main gate per shift",     "post_gc_mall_gate",      510.0, 3, "shift_day"),
            ("bpl_gc_parking",  "billing_plan_game_city",     "Game City parking deck per shift",  "post_gc_parking_gate",   480.0, 2, "shift_day"),
        ]
        for xmlid, plan_xmlid, name, post_xmlid, unit_price, guard_count, shift_xmlid in plan_lines:
            plan = self.ref(plan_xmlid)
            self.get_or_create(
                xmlid,
                "security.billing.plan.line",
                {
                    "billing_plan_id": plan.id,
                    "name": name,
                    "post_id": self.ref(post_xmlid).id,
                    "billing_basis": "guard_shift",
                    "quantity": 1.0,
                    "unit_price": unit_price,
                    "guard_count": guard_count,
                    "shift_template_id": self.ref(shift_xmlid).id,
                },
            )

        # ---- Invoices for first 5 clients ----
        # Monthly billing rates: BW 65000, NBL 80000, NWR 45000, MTC 70000, OM 50000
        invoices = [
            ("invoice_bw_may_2026",  "client_bank_windhoek",    "billing_plan_bank_windhoek", "site_bw_hq",      "BW-DEMO-PO-0526",  65000.0),
            ("invoice_nbl_may_2026", "client_namibia_breweries","billing_plan_nbl",           "site_nbl_brewery","NBL-DEMO-PO-0526", 80000.0),
            ("invoice_nwr_may_2026", "client_nwr",              "billing_plan_nwr",           "site_nwr_hq",     "NWR-DEMO-PO-0526", 45000.0),
            ("invoice_mtc_may_2026", "client_mtc",              "billing_plan_mtc",           "site_mtc_hq",     "MTC-DEMO-PO-0526", 70000.0),
            ("invoice_om_may_2026",  "client_old_mutual",       "billing_plan_old_mutual",    "site_om_hq",      "OM-DEMO-PO-0526",  50000.0),
        ]
        for xmlid, client_xmlid, plan_xmlid, site_xmlid, po_number, monthly_amount in invoices:
            invoice = self.get_or_create(
                xmlid,
                "security.billing.invoice",
                {
                    "name": "New",
                    "partner_id": self.ref(client_xmlid).id,
                    "billing_plan_id": self.ref(plan_xmlid).id,
                    "currency_id": nad.id,
                    "invoice_date": "2026-05-31",
                    "due_date": "2026-06-30",
                    "service_date_from": "2026-05-01",
                    "service_date_to": "2026-05-31",
                    "site_id": self.ref(site_xmlid).id,
                    "po_number": po_number,
                    "vat_rate": 15.0,
                },
            )
            if not invoice.line_ids:
                self.env["security.billing.invoice.line"].create({
                    "invoice_id": invoice.id,
                    "name": f"Security services — May 2026",
                    "quantity": 1.0,
                    "unit_price": monthly_amount,
                    "service_date_from": "2026-05-01",
                    "service_date_to": "2026-05-31",
                    "site_id": self.ref(site_xmlid).id,
                })

    # ------------------------------------------------------------------
    # 11. CLIENT REPORT
    # ------------------------------------------------------------------

    def _create_client_report(self):
        report = self.get_or_create(
            "client_report_bw_may",
            "security.client.service.report",
            {
                "partner_id": self.ref("client_bank_windhoek").id,
                "site_id": self.ref("site_bw_hq").id,
                "date_from": "2026-05-01",
                "date_to": "2026-05-14",
                "note": "Demo client-facing service report for attendance verification — Bank Windhoek HQ, May 2026 (2 weeks).",
            },
        )
        if hasattr(report, "action_generate") and not report.attendance_record_ids:
            report.action_generate()

        report2 = self.get_or_create(
            "client_report_nbl_may",
            "security.client.service.report",
            {
                "partner_id": self.ref("client_namibia_breweries").id,
                "site_id": self.ref("site_nbl_brewery").id,
                "date_from": "2026-05-01",
                "date_to": "2026-05-14",
                "note": "Demo client-facing service report — NBL Brewery Plant, May 2026.",
            },
        )
        if hasattr(report2, "action_generate") and not report2.attendance_record_ids:
            report2.action_generate()

        report3 = self.get_or_create(
            "client_report_nwr_may",
            "security.client.service.report",
            {
                "partner_id": self.ref("client_nwr").id,
                "site_id": self.ref("site_nwr_swakop").id,
                "date_from": "2026-05-01",
                "date_to": "2026-05-07",
                "note": "Demo client-facing service report — NWR Swakopmund Resort, May 2026.",
            },
        )
        if hasattr(report3, "action_generate") and not report3.attendance_record_ids:
            report3.action_generate()

    # ------------------------------------------------------------------
    # 12. JUNE–SEPTEMBER 2026 ROSTERS AND ATTENDANCE
    # ------------------------------------------------------------------

    def _create_june_september_rosters(self):
        """Generate full June–September 2026 rosters and attendance across 4 key sites.

        Coverage:
          June 2026        → locked attendance (historical)
          July 2026        → locked attendance (historical)
          August 1–15      → reviewed attendance (active month)
          August 16–31     → roster only, no attendance (upcoming)
          September 2026   → draft roster only (planning)
        """
        LOCKED_UNTIL   = date(2026, 7, 31)
        REVIEWED_UNTIL = date(2026, 8, 15)

        # 4 sites with their shift requirements and assigned guard pools
        site_configs = [
            {
                "site_tag":     "bw_hq",
                "site_xmlid":   "site_bw_hq",
                "partner_xmlid":"client_bank_windhoek",
                "requirements": [
                    ("req_bw_hq_gate_day",    ["guard_a01", "guard_a02"]),
                    ("req_bw_hq_gate_night",  ["guard_b01", "guard_b02"]),
                    ("req_bw_hq_control_day", ["guard_b03"]),
                ],
            },
            {
                "site_tag":     "nbl_brewery",
                "site_xmlid":   "site_nbl_brewery",
                "partner_xmlid":"client_namibia_breweries",
                "requirements": [
                    ("req_nbl_brewery_gate_day",   ["guard_b05", "guard_b06"]),
                    ("req_nbl_brewery_gate_night", ["guard_c05", "guard_c06"]),
                ],
            },
            {
                "site_tag":     "sr_wernhil",
                "site_xmlid":   "site_sr_wernhil",
                "partner_xmlid":"client_shoprite",
                "requirements": [
                    ("req_sr_wernhil_day",   ["guard_c07", "guard_c08"]),
                    ("req_sr_wernhil_night", ["guard_c09"]),
                ],
            },
            {
                "site_tag":     "nwr_hq",
                "site_xmlid":   "site_nwr_hq",
                "partner_xmlid":"client_nwr",
                "requirements": [
                    ("req_nwr_hq_gate_day",   ["guard_a05", "guard_a06"]),
                    ("req_nwr_hq_gate_night", ["guard_b07", "guard_b08"]),
                    ("req_nwr_hq_cctv_day",   ["guard_c11"]),
                ],
            },
        ]

        months = [
            (date(2026, 6, 1), date(2026, 6, 30), "jun_2026"),
            (date(2026, 7, 1), date(2026, 7, 31), "jul_2026"),
            (date(2026, 8, 1), date(2026, 8, 31), "aug_2026"),
            (date(2026, 9, 1), date(2026, 9, 30), "sep_2026"),
        ]

        for cfg in site_configs:
            site    = self.ref(cfg["site_xmlid"])
            partner = self.ref(cfg["partner_xmlid"])
            if not site or not partner:
                continue
            site_tag = cfg["site_tag"]

            # Pre-resolve requirements + guard records
            req_guard_specs = []
            for req_xmlid, guard_xmlids in cfg["requirements"]:
                req = self.ref(req_xmlid)
                if not req:
                    continue
                guards = [g for g in (self.ref(gx) for gx in guard_xmlids) if g]
                if guards:
                    req_guard_specs.append((req_xmlid, req, guards))

            for month_start, month_end, month_tag in months:
                roster_state = "draft" if month_start.month >= 9 else "confirmed"

                batch = self.get_or_create(
                    f"roster_{month_tag}_{site_tag}",
                    "security.roster.batch",
                    {
                        "date_from": month_start.isoformat(),
                        "date_to":   month_end.isoformat(),
                        "partner_id": partner.id,
                        "site_id":    site.id,
                        "state":      "draft",
                        "note":       f"Demo roster — {site.name}, {month_start.strftime('%B %Y')}.",
                    },
                )

                current = month_start
                while current <= month_end:
                    weekday = current.weekday()
                    for req_xmlid, req, guards in req_guard_specs:
                        if not self._req_on_day(req, weekday):
                            continue
                        for slot_num, guard in enumerate(guards, start=1):
                            slot_state = (
                                "confirmed" if current <= REVIEWED_UNTIL else "assigned"
                            )
                            slot = self.get_or_create(
                                f"slot_{month_tag}_{site_tag}_{req_xmlid}_{current.isoformat()}_{slot_num}",
                                "security.roster.slot",
                                {
                                    "batch_id":             batch.id,
                                    "slot_number":          slot_num,
                                    "shift_date":           current.isoformat(),
                                    "shift_requirement_id": req.id,
                                    "post_id":              req.post_id.id,
                                    "shift_template_id":    req.shift_template_id.id,
                                    "employee_id":          guard.id,
                                    "state":                slot_state,
                                },
                            )
                            if current <= REVIEWED_UNTIL:
                                self._make_attendance_record(
                                    slot, site, partner, batch, site_tag,
                                    "locked" if current <= LOCKED_UNTIL else "reviewed",
                                )
                    current += timedelta(days=1)

                if batch.state == "draft" and roster_state != "draft":
                    batch.write({"state": roster_state})

        # ── Additional leave requests (June–September) ────────────────────
        lt_annual = self.env["security.leave.type"].search([("code", "=", "AL")], limit=1)
        lt_sick   = self.env["security.leave.type"].search([("code", "=", "SL")], limit=1)
        if lt_annual and lt_sick:
            for xmlid, gx, d1, d2, lt, state in [
                ("leave_a01_annual_jul", "guard_a01", "2026-07-14", "2026-07-18", lt_annual, "approved"),
                ("leave_b05_sick_jun",   "guard_b05", "2026-06-22", "2026-06-23", lt_sick,   "approved"),
                ("leave_c07_annual_aug", "guard_c07", "2026-08-04", "2026-08-08", lt_annual, "approved"),
                ("leave_b08_annual_aug", "guard_b08", "2026-08-18", "2026-08-22", lt_annual, "draft"),
                ("leave_c11_annual_sep", "guard_c11", "2026-09-01", "2026-09-05", lt_annual, "refused"),
            ]:
                g = self.ref(gx)
                if g:
                    self.get_or_create(xmlid, "security.leave.request", {
                        "employee_id":   g.id,
                        "date_from":     d1,
                        "date_to":       d2,
                        "leave_type_id": lt.id,
                        "state":         state,
                    })

        # ── Additional incidents (June–September) ────────────────────────
        for xmlid, gx, type_xid, d, note, state in [
            ("incident_jun_late_sr",  "guard_c09", "incident_type_late_posting", "2026-06-12",
             "Late reporting at ShopRite Wernhil — verbal warning.", "approved"),
            ("incident_jul_awol_nbl", "guard_c05", "incident_type_awol_first",   "2026-07-08",
             "AWOL at NBL Brewery night shift — formal warning issued.", "approved"),
            ("incident_aug_uniform",  "guard_b08", "incident_type_uniform",      "2026-08-02",
             "Incomplete uniform at BW HQ morning parade — written warning.", "draft"),
        ]:
            g     = self.ref(gx)
            itype = self.ref(type_xid)
            if g and itype:
                self.get_or_create(xmlid, "security.incident", {
                    "employee_id":      g.id,
                    "incident_type_id": itype.id,
                    "incident_date":    d,
                    "note":             note,
                    "state":            state,
                })

        # ── Payroll periods for June and July ─────────────────────────────
        rule_set = self.ref("rule_set_na_2026")
        if rule_set:
            for p_xmlid, d_from, d_to in [
                ("payroll_period_jun_2026", "2026-06-01", "2026-06-30"),
                ("payroll_period_jul_2026", "2026-07-01", "2026-07-31"),
            ]:
                period = self.get_or_create(p_xmlid, "security.payroll.period", {
                    "date_from":    d_from,
                    "date_to":      d_to,
                    "rule_set_id":  rule_set.id,
                })
                try:
                    if not period.payslip_ids:
                        period.action_generate_payslips()
                        period.action_confirm_payslips()
                except Exception:
                    pass

        # ── Billing invoices for June–August ─────────────────────────────
        nad = self.env.ref("base.NAD", raise_if_not_found=False) or self.env.company.currency_id
        for xmlid, cx, px, sx, po, amount, inv_date, due_date in [
            ("invoice_bw_jun_2026",  "client_bank_windhoek",    "billing_plan_bank_windhoek", "site_bw_hq",       "BW-0626",  65000.0, "2026-06-30", "2026-07-30"),
            ("invoice_nbl_jun_2026", "client_namibia_breweries","billing_plan_nbl",            "site_nbl_brewery", "NBL-0626", 80000.0, "2026-06-30", "2026-07-30"),
            ("invoice_sr_jun_2026",  "client_shoprite",         "billing_plan_shoprite",       "site_sr_wernhil",  "SR-0626",  35000.0, "2026-06-30", "2026-07-30"),
            ("invoice_nwr_jun_2026", "client_nwr",              "billing_plan_nwr",            "site_nwr_hq",      "NWR-0626", 45000.0, "2026-06-30", "2026-07-30"),
            ("invoice_bw_jul_2026",  "client_bank_windhoek",    "billing_plan_bank_windhoek", "site_bw_hq",       "BW-0726",  65000.0, "2026-07-31", "2026-08-31"),
            ("invoice_nbl_jul_2026", "client_namibia_breweries","billing_plan_nbl",            "site_nbl_brewery", "NBL-0726", 80000.0, "2026-07-31", "2026-08-31"),
            ("invoice_sr_jul_2026",  "client_shoprite",         "billing_plan_shoprite",       "site_sr_wernhil",  "SR-0726",  35000.0, "2026-07-31", "2026-08-31"),
            ("invoice_nwr_jul_2026", "client_nwr",              "billing_plan_nwr",            "site_nwr_hq",      "NWR-0726", 45000.0, "2026-07-31", "2026-08-31"),
            ("invoice_bw_aug_2026",  "client_bank_windhoek",    "billing_plan_bank_windhoek", "site_bw_hq",       "BW-0826",  32500.0, "2026-08-15", "2026-09-15"),
        ]:
            plan = self.ref(px)
            if not plan:
                continue
            invoice = self.get_or_create(xmlid, "security.billing.invoice", {
                "name":             "New",
                "partner_id":       self.ref(cx).id,
                "billing_plan_id":  plan.id,
                "currency_id":      nad.id,
                "invoice_date":     inv_date,
                "due_date":         due_date,
                "service_date_from":inv_date[:8] + "01",
                "service_date_to":  inv_date,
                "site_id":          self.ref(sx).id,
                "po_number":        po,
                "vat_rate":         15.0,
            })
            if not invoice.line_ids:
                month_label = {"06": "June", "07": "July", "08": "August"}.get(inv_date[5:7], "")
                self.env["security.billing.invoice.line"].create({
                    "invoice_id":       invoice.id,
                    "name":             f"Security services — {month_label} 2026",
                    "quantity":         1.0,
                    "unit_price":       amount,
                    "service_date_from":inv_date[:8] + "01",
                    "service_date_to":  inv_date,
                    "site_id":          self.ref(sx).id,
                })

    def _req_on_day(self, req, weekday):
        """Return True if the shift requirement runs on this weekday (0=Mon..6=Sun)."""
        field = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][weekday]
        return bool(getattr(req, field, True))

    def _make_attendance_record(self, slot, site, partner, roster_batch, site_tag, batch_state):
        """Create one realistic attendance record for a roster slot.

        Attendance pattern (deterministic, seeded by employee+date):
          94% — present on time
           3% — late (check_in +20 min)
           2% — authorised absence
           1% — AWOL
        """
        seed = (slot.employee_id.id or 0) + slot.shift_date.toordinal()
        rnd  = ((seed * 1664525 + 1013904223) & 0xFFFFFFFF) % 100

        if rnd == 0:
            presence = "awol";   absence = "awol"
        elif rnd <= 2:
            presence = "absent"; absence = "authorised"
        else:
            presence = "present"; absence = "none"

        is_late = (rnd >= 94 and presence == "present")

        start_h = slot.shift_template_id.start_hour
        end_h   = slot.shift_template_id.end_hour
        start_dt = datetime.combine(
            slot.shift_date,
            time(hour=int(start_h), minute=int(round((start_h % 1) * 60))),
        )
        end_dt = datetime.combine(
            slot.shift_date,
            time(hour=int(end_h), minute=int(round((end_h % 1) * 60))),
        )
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)

        att_batch = self.get_or_create(
            f"att_batch_{site_tag}_{slot.shift_date.isoformat()}",
            "security.attendance.batch",
            {
                "attendance_date": slot.shift_date.isoformat(),
                "partner_id":      partner.id,
                "site_id":         site.id,
                "roster_batch_id": roster_batch.id,
                "state":           batch_state,
            },
        )

        vals = {
            "attendance_batch_id": att_batch.id,
            "roster_slot_id":      slot.id,
            "manual_presence":     presence,
            "absence_type":        absence,
        }
        if presence == "present":
            vals["check_in"]  = start_dt + timedelta(minutes=20 if is_late else 2)
            vals["check_out"] = end_dt

        self.get_or_create(f"att_record_{slot.id}", "security.attendance.record", vals)
