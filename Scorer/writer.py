"""
Resume Writer Engine
─────────────────────────────────────────────────────────────────────
Generates placement-specific, copy-paste-ready resume content for every
missing keyword. Voice: 30-year resume writer crafting lines for a
10-year Oracle/IT professional.

Each suggestion tells the candidate:
  WHERE  → Summary / Experience 1 / Experience 2 / Skills
  WHAT   → The exact professional line to add (ready to paste)
  WHY    → One-line rationale from a recruiter's perspective
"""

import re
from typing import Optional

# ── Canonical alias map (normalize keyword variants) ──────────────────────────
ALIASES: dict[str, str] = {
    # Oracle / ERP
    "hdl":           "hcm data loader",
    "hdi":           "hcm spreadsheet loader",
    "fastformula":   "fast formula",
    "plsql":         "pl/sql",
    "pl sql":        "pl/sql",
    "hcm rest":      "hcm rest api",
    "rest api hcm":  "hcm rest api",
    "otbi hcm":      "otbi",
    "bi publisher hcm": "bi publisher",
    "oracle hcm":    "hcm",
    "fusion hcm":    "hcm",
    "hcm cloud":     "hcm",
    "oracle cloud hcm": "hcm",
    "oracle oic":    "oic",
    "oracle integration cloud": "oic",
    "integration cloud service": "oic",
    "oracle integration": "oic",
    "oracle apex":   "apex",
    "application express": "apex",
    "oracle application express": "apex",
    "oracle rest data services": "ords",
    "suitescript 2.0": "suitescript",
    "suitescript 1.0": "suitescript",
    "informatica powercenter": "informatica",
    "ibm datastage": "datastage",
    "apache spark":  "spark",
    "oracle data integrator": "odi",
    "oracle goldengate": "goldengate",
    "azure data factory": "adf pipeline",
    "adf pipeline":  "azure data factory",
    "pl/sql":        "pl/sql",
    "oracle ebs":    "oracle e-business suite",
    "e-business suite": "oracle e-business suite",
    "oracle e business suite": "oracle e-business suite",
    # DevOps
    "k8s":           "kubernetes",
    "cicd":          "ci/cd",
    "ci cd":         "ci/cd",
    "github actions": "ci/cd",
    "gitlab ci":     "ci/cd",
    "jenkins":       "ci/cd",
    "iac":           "infrastructure as code",
    "prom":          "prometheus",
    "grafana":       "prometheus",
    "alertmanager":  "prometheus",
    # AI/ML
    "langGraph":     "langchain",
    "lang chain":    "langchain",
    "retrieval augmented generation": "rag",
    "vector database": "rag",
    "pytorch":       "pytorch",
    "torch":         "pytorch",
    "tensorflow":    "pytorch",
    "hugging face":  "pytorch",
    "experiment tracking": "mlflow",
    "model registry": "mlflow",
    "large language model": "llm",
    "llms":          "llm",
    "openai":        "llm",
    "gpt-4":         "llm",
    "anthropic":     "llm",
    # Security
    "ztna":          "zero trust",
    "zero-trust":    "zero trust",
    "pentest":       "penetration testing",
    "pentesting":    "penetration testing",
    "vulnerability assessment": "penetration testing",
    "splunk":        "siem",
    "sentinel":      "siem",
    "qradar":        "siem",
    "dev sec ops":   "devsecops",
    # Full Stack
    "react.js":      "react",
    "reactjs":       "react",
    "next.js":       "react",
    "vue.js":        "react",
    "angular":       "react",
    "spring":        "spring boot",
    "spring framework": "spring boot",
    "grpc":          "microservices",
    "event-driven":  "microservices",
    # QA
    "selenium webdriver": "selenium",
    "cypress":       "selenium",
    "playwright":    "selenium",
    "junit":         "pytest",
    "testng":        "pytest",
    "bdd":           "pytest",
    "cucumber":      "pytest",
    "rest assured":  "api testing",
    "postman":       "api testing",
    "jmeter":        "performance testing",
    "k6":            "performance testing",
    "gatling":       "performance testing",
    # Modern Data Eng
    "data build tool": "dbt",
    "apache kafka":  "kafka",
    "kafka streams": "kafka",
    "apache airflow": "airflow",
    "cloud composer": "airflow",
    "mwaa":          "airflow",
    "pyspark":       "spark",
}

# ── Phrase bank ───────────────────────────────────────────────────────────────
# Structure per entry:
#   skill_entry : exact text to add to Technical Skills section
#   bullets     : 2 professional bullet points for experience section
#   summary_tag : short phrase to weave into professional summary
#   exp_slot    : "exp1" (core/recent) | "exp2" (secondary/previous)
#   recruiter_why: why a recruiter cares — shown as tip

PHRASE_BANK: dict[str, dict] = {

    # ══ ORACLE HCM ════════════════════════════════════════════════════════════

    "hcm": {
        "skill_entry": "Oracle HCM Cloud | Oracle Fusion HCM | Core HR | Global HR",
        "bullets": [
            "Led end-to-end Oracle Cloud HCM implementations spanning Core HR, payroll, "
            "absence management, and benefits modules for global organizations with 5,000–20,000 employees, "
            "coordinating with HR leadership, IT, and third-party vendors across project lifecycle.",

            "Configured Oracle HCM Cloud organizational structures including legal entities, "
            "business units, departments, grades, job families, and position hierarchies to reflect "
            "client operating models, ensuring alignment with downstream payroll and finance integrations.",
        ],
        "summary_tag": "Oracle Cloud HCM implementations",
        "exp_slot": "exp1",
        "recruiter_why": "Core module — recruiters will scan for 'HCM' immediately; its absence is a red flag.",
    },

    "fast formula": {
        "skill_entry": "Fast Formula (Payroll Rules, Absence Accruals, Time & Labor)",
        "bullets": [
            "Designed and maintained Oracle Fast Formula scripts to automate payroll calculation rules, "
            "absence accrual eligibility criteria, and overtime policies across multiple legislative data "
            "groups (US, UK, Canada), reducing manual payroll exception handling by over 35%.",

            "Developed custom Fast Formula logic for complex payroll scenarios including retroactive pay, "
            "shift differentials, pro-rated salary adjustments, and element skip rules, "
            "collaborating with payroll functional leads to translate policy requirements into formula syntax.",
        ],
        "summary_tag": "Fast Formula scripting",
        "exp_slot": "exp1",
        "recruiter_why": "Fast Formula is a differentiator — many HCM consultants skip it; listing it signals deep payroll expertise.",
    },

    "hcm data loader": {
        "skill_entry": "HCM Data Loader (HDL) | Bulk Data Migration | HR Data Integration",
        "bullets": [
            "Utilized HCM Data Loader (HDL) to execute bulk data migrations of employee records, "
            "positions, assignments, grades, and organizational hierarchies during Oracle Cloud HCM "
            "go-lives and HR restructuring initiatives, achieving 99.7% data accuracy across 50,000+ records.",

            "Developed reusable HDL file templates and automated pre-validation scripts to catch "
            "data quality issues before load, cutting migration rework cycles from 3 days to under 4 hours "
            "and reducing post-go-live data correction tickets by 60%.",
        ],
        "summary_tag": "HCM Data Loader (HDL) migrations",
        "exp_slot": "exp1",
        "recruiter_why": "HDL is a required skill on nearly every HCM implementation JD — omitting it costs you HOT-tier candidates.",
    },

    "hcm spreadsheet loader": {
        "skill_entry": "HCM Spreadsheet Loader (HDI) | Self-Service Data Templates",
        "bullets": [
            "Created and maintained HCM Spreadsheet Loader (HDI) templates enabling HR business users "
            "to perform self-service mass updates for positions, jobs, person records, and "
            "salary data without technical intervention, reducing IT data-change request backlog by 40%.",

            "Trained HR administrators on HDI usage and built validation guides to ensure data "
            "integrity on upload, supporting post-go-live steady-state operations across multiple business units.",
        ],
        "summary_tag": "HCM Spreadsheet Loader (HDI)",
        "exp_slot": "exp2",
        "recruiter_why": "Shows you can hand power to business users — a key indicator of a mature, client-focused consultant.",
    },

    "hcm extracts": {
        "skill_entry": "HCM Extracts | BI Publisher Delivery | SFTP/FTP Integration",
        "bullets": [
            "Designed and delivered 25+ HCM Extracts for outbound integrations to payroll providers, "
            "benefits vendors, pension administrators, and government reporting bodies, using "
            "BI Publisher report templates with SFTP, email, and web service delivery channels.",

            "Optimized HCM Extract run times by restructuring attribute hierarchies and leveraging "
            "fast formula criteria blocks, reducing a nightly benefits file extract from 4 hours "
            "to under 40 minutes for a 15,000-employee client.",
        ],
        "summary_tag": "HCM Extracts design and delivery",
        "exp_slot": "exp1",
        "recruiter_why": "HCM Extracts are in 80% of HCM JDs — shows you can connect HCM to the real world of vendor files.",
    },

    "hcm rest api": {
        "skill_entry": "HCM REST APIs | Oracle Cloud Integration | Real-Time HR Data Sync",
        "bullets": [
            "Integrated Oracle HCM Cloud with third-party HRIS, ATS, and identity management systems "
            "using HCM REST APIs, enabling real-time employee lifecycle event synchronization "
            "including new hire provisioning, termination workflows, and position changes.",

            "Designed REST API-based event-driven integration patterns using Oracle HCM Cloud webhooks "
            "and OIC to trigger downstream actions (Active Directory provisioning, badge system updates) "
            "within minutes of HR transactions, replacing overnight batch file processing.",
        ],
        "summary_tag": "HCM REST API integrations",
        "exp_slot": "exp1",
        "recruiter_why": "REST API experience elevates you from functional to techno-functional — doubles your JD match rate.",
    },

    "core hr": {
        "skill_entry": "Core HR | Global HR | Workforce Structures | Person Management",
        "bullets": [
            "Implemented Oracle Core HR module including legal entity setup, business unit configuration, "
            "grade and grade step structures, job family taxonomy, position management, and "
            "workforce structure hierarchy for a global organization spanning 30+ countries.",

            "Configured worker and assignment data models, employment terms, and person record "
            "management rules to support complex employment arrangements including global assignments, "
            "secondments, and fixed-term contracts alongside permanent workforce.",
        ],
        "summary_tag": "Core HR configuration",
        "exp_slot": "exp1",
        "recruiter_why": "Core HR is the foundation of every HCM project — if you've touched it, say so explicitly.",
    },

    "payroll": {
        "skill_entry": "Oracle Fusion Payroll | Payroll Flows | Legislative Configuration | QuickPay",
        "bullets": [
            "Configured Oracle Fusion Payroll including earnings and deduction elements, "
            "payroll flow patterns, QuickPay runs, pre-payroll validation rules, and "
            "payslip delivery for US, UK, and Canadian legislative groups across multiple legal entities.",

            "Supported payroll parallel run testing and reconciliation activities during go-live, "
            "investigating and resolving payroll discrepancies between legacy system and Oracle Cloud "
            "results, achieving sign-off within planned 3-cycle parallel run window.",
        ],
        "summary_tag": "Oracle Fusion Payroll configuration and support",
        "exp_slot": "exp1",
        "recruiter_why": "Payroll is high-stakes and high-value — mentioning it directly opens senior consultant and lead roles.",
    },

    "absence management": {
        "skill_entry": "Oracle Absence Management | Accrual Plans | Leave Policies | Payroll Integration",
        "bullets": [
            "Configured Oracle Absence Management module including accrual plan definitions, "
            "absence types, entitlement rules, carryover policies, and donation programs, "
            "aligned with HR policy for 5 countries with differing statutory leave requirements.",

            "Designed absence-to-payroll integration ensuring absence costing, encashment, "
            "and unpaid leave deductions were accurately reflected in payroll runs, "
            "collaborating with payroll team to map absence formula outputs to element entries.",
        ],
        "summary_tag": "Absence Management configuration",
        "exp_slot": "exp1",
        "recruiter_why": "Absence Management appears in 70% of HCM JDs — a quick win to move from 'OK' to 'HOT'.",
    },

    "benefits": {
        "skill_entry": "Oracle Benefits Cloud | Benefits Administration | Life Events | Open Enrollment",
        "bullets": [
            "Configured Oracle Benefits module including plan types, benefit options, eligibility "
            "profiles, life event processing rules, and flex credit programs to support medical, "
            "dental, vision, and life insurance offerings for 8,000+ employees across 3 legal entities.",

            "Coordinated open enrollment configuration and user acceptance testing, "
            "partnering with HR and benefits broker to validate plan rates, coverage rules, "
            "and COBRA processing prior to annual enrollment window launch.",
        ],
        "summary_tag": "Benefits module configuration and open enrollment",
        "exp_slot": "exp2",
        "recruiter_why": "Benefits expertise is scarce — mentioning it separates you from 70% of HCM candidates.",
    },

    "compensation": {
        "skill_entry": "Oracle Compensation Cloud | Salary Ranges | Workforce Compensation | Grade Steps",
        "bullets": [
            "Implemented Oracle Compensation module including salary ranges, grade steps, "
            "individual compensation plans, and workforce compensation planning worksheets "
            "to support annual merit review cycles for 6,000 employees across business units.",

            "Configured compensation eligibility rules, budget allocations, and approval "
            "workflows for annual salary review, enabling managers to submit compensation "
            "proposals through guided planning worksheets with real-time budget visualization.",
        ],
        "summary_tag": "Compensation Cloud configuration",
        "exp_slot": "exp2",
        "recruiter_why": "Compensation is a niche HCM skill — listing it differentiates you as a full-suite HCM consultant.",
    },

    "talent management": {
        "skill_entry": "Oracle Talent Management | Goal Management | Performance Reviews | Succession",
        "bullets": [
            "Configured Oracle Talent Management suite including performance goal libraries, "
            "review period templates, rating scales, competency frameworks, and 360-degree "
            "feedback questionnaires supporting annual and mid-year review cycles.",

            "Implemented talent review and succession planning functionality including talent "
            "pool management, box chart configuration, readiness indicators, and succession "
            "plan generation for critical positions in senior leadership pipeline.",
        ],
        "summary_tag": "Talent Management and succession planning",
        "exp_slot": "exp2",
        "recruiter_why": "Talent Suite breadth signals you can engage at CHRO level — not just technical implementation.",
    },

    "absence management": {
        "skill_entry": "Oracle Absence Management | Accrual Plans | Leave Entitlements | Payroll Costing",
        "bullets": [
            "Configured Oracle Absence Management covering accrual plan setup, absence types, "
            "entitlement rules, carryover caps, and donation programs across 5 country-specific "
            "policies with varying statutory leave requirements.",

            "Integrated absence module with Oracle Payroll to ensure accurate absence costing, "
            "leave encashment calculations, and unpaid deduction processing within payroll run sequences.",
        ],
        "summary_tag": "Absence Management",
        "exp_slot": "exp1",
        "recruiter_why": "Listed as required on majority of HCM JDs — a direct ATS filter keyword.",
    },

    "otbi": {
        "skill_entry": "OTBI (Oracle Transactional Business Intelligence) | Custom Reports | HR Analytics",
        "bullets": [
            "Built 30+ OTBI reports and dashboards providing HR leadership with real-time workforce "
            "analytics including headcount trends, attrition analysis, compensation equity, "
            "time-to-hire metrics, and absence utilization — reducing manual Excel reporting by 70%.",

            "Designed OTBI subject area joins across workforce structures, compensation, "
            "and recruiting domains to deliver cross-functional workforce dashboards for "
            "executive and HR business partner audiences with role-based access controls.",
        ],
        "summary_tag": "OTBI reporting and HR analytics",
        "exp_slot": "exp2",
        "recruiter_why": "Self-service reporting is a key deliverable on every HCM project — OTBI skill keeps you client-facing.",
    },

    "bi publisher": {
        "skill_entry": "Oracle BI Publisher | RTF Templates | Payslips | Regulatory Reports",
        "bullets": [
            "Developed BI Publisher report templates for payslips, offer letters, "
            "employment verification letters, and government statutory reports using "
            "RTF-based layout design with multi-language and conditional formatting support.",

            "Configured BI Publisher delivery channels including SFTP, email, and FTP "
            "for automated report distribution to payroll vendors, benefits providers, "
            "and regulatory bodies on scheduled and event-driven basis.",
        ],
        "summary_tag": "BI Publisher report development",
        "exp_slot": "exp2",
        "recruiter_why": "Payslip and statutory reports are on every HCM engagement — BI Publisher is non-negotiable at senior level.",
    },

    "role based access": {
        "skill_entry": "Oracle RBAC | Data Roles | Abstract Roles | HCM Security Profiles",
        "bullets": [
            "Designed Oracle HCM Cloud security architecture including role-based access "
            "control (RBAC) framework with abstract roles, job roles, duty roles, and "
            "data roles aligned to organizational hierarchy and SOX compliance requirements.",

            "Conducted HCM security audit and remediation for 500+ users, resolving "
            "segregation of duty conflicts, redefining person security profiles and "
            "data access policies across legal entities and business units.",
        ],
        "summary_tag": "HCM security and RBAC design",
        "exp_slot": "exp2",
        "recruiter_why": "Security mis-configuration is a top HCM post-go-live risk — showing security expertise raises your seniority signal.",
    },

    "flexfields": {
        "skill_entry": "Oracle Flexfields | DFF | EFF | KFF | Extensible Configuration",
        "bullets": [
            "Configured Oracle Descriptive Flexfields (DFF) and Extensible Flexfields (EFF) "
            "across Person, Assignment, Job, and Position objects to capture "
            "organization-specific HR data requirements without custom development.",

            "Designed Key Flexfield (KFF) segment structures and value sets for "
            "account code combinations, cost center hierarchies, and job code taxonomies, "
            "ensuring downstream GL and payroll costing integration integrity.",
        ],
        "summary_tag": "Flexfield configuration",
        "exp_slot": "exp2",
        "recruiter_why": "Flexfields are everywhere in Oracle Cloud — listing them signals you're hands-on, not just functional.",
    },

    # ══ ORACLE OIC ════════════════════════════════════════════════════════════

    "oic": {
        "skill_entry": "Oracle Integration Cloud (OIC) | REST | SOAP | File Adapters | Orchestration",
        "bullets": [
            "Designed, developed, and deployed 40+ Oracle Integration Cloud (OIC) integrations "
            "connecting Oracle ERP Cloud, HCM Cloud, and on-premise systems using REST, SOAP, "
            "FTP, Database, and ERP Cloud adapters — eliminating point-to-point custom code.",

            "Architected OIC orchestration flows with parallel actions, fault handling, "
            "compensation patterns, and real-time monitoring dashboards, reducing average "
            "integration incident resolution time from 6 hours to under 45 minutes.",
        ],
        "summary_tag": "Oracle Integration Cloud (OIC) development",
        "exp_slot": "exp1",
        "recruiter_why": "OIC is Oracle's primary integration platform — leads on every cloud project specifically ask for it.",
    },

    "rest adapter": {
        "skill_entry": "OIC REST Adapter | RESTful API Integration | JSON Mapping",
        "bullets": [
            "Built OIC REST Adapter integrations to expose Oracle Cloud business objects "
            "as RESTful endpoints and consume third-party REST APIs for real-time bidirectional "
            "data exchange with Salesforce, Workday, ServiceNow, and ADP.",

            "Developed JSON-to-JSON transformation mappings within OIC using XSLT and "
            "expression builder for complex data translation between Oracle Cloud payloads "
            "and partner API schemas, including error handling and retry logic.",
        ],
        "summary_tag": "REST API integrations via OIC",
        "exp_slot": "exp1",
        "recruiter_why": "REST is the integration standard — this signals you can integrate Oracle with anything modern.",
    },

    "soap adapter": {
        "skill_entry": "OIC SOAP Adapter | WSDL-Based Integration | Legacy System Connectivity",
        "bullets": [
            "Implemented SOAP-based OIC integrations using Oracle SOAP Adapter "
            "for legacy ERP, payroll, and banking system connectivity, replacing "
            "custom middleware code with managed, monitored OIC integration flows.",

            "Configured WSDL import, message transformation, and SOAP header "
            "handling in OIC for interoperability with on-premise Oracle EBS "
            "and third-party enterprise systems requiring WS-Security authentication.",
        ],
        "summary_tag": "SOAP/WSDL integrations",
        "exp_slot": "exp2",
        "recruiter_why": "Legacy connectivity is still critical — SOAP adapter experience shows you can bridge old and new systems.",
    },

    "ftp adapter": {
        "skill_entry": "OIC FTP/SFTP Adapter | File-Based Integration | Scheduled Data Exchange",
        "bullets": [
            "Developed file-based OIC integrations using FTP and SFTP Adapters "
            "for scheduled data file exchange with payroll bureaus, pension providers, "
            "benefits administrators, and government agencies — supporting CSV, XML, and fixed-width formats.",

            "Implemented OIC file-polling integration flows that detect, validate, "
            "stage, and process inbound vendor files on arrival, triggering downstream "
            "Oracle Cloud record creation with error quarantine and notification workflows.",
        ],
        "summary_tag": "FTP/SFTP file-based integrations",
        "exp_slot": "exp2",
        "recruiter_why": "File-based integration is still the most common pattern in enterprise Oracle projects.",
    },

    # ══ ORACLE APEX ═══════════════════════════════════════════════════════════

    "apex": {
        "skill_entry": "Oracle APEX | Low-Code Application Development | PL/SQL | JavaScript",
        "bullets": [
            "Developed and deployed 15+ Oracle APEX applications including employee "
            "self-service portals, operational dashboards, workflow management tools, "
            "and internal audit tracking systems — reducing development time by 60% vs traditional coding.",

            "Built complex APEX applications with Dynamic Actions, Interactive Grids, "
            "REST-enabled PL/SQL APIs, custom authentication schemes, and role-based "
            "page authorization to deliver enterprise-grade functionality with low-code approach.",
        ],
        "summary_tag": "Oracle APEX application development",
        "exp_slot": "exp1",
        "recruiter_why": "APEX demand is surging as Oracle pushes low-code — listing it opens a fast-growing JD category.",
    },

    "ords": {
        "skill_entry": "Oracle REST Data Services (ORDS) | RESTful PL/SQL APIs | OAuth2",
        "bullets": [
            "Configured Oracle REST Data Services (ORDS) to expose PL/SQL stored procedures "
            "and Oracle Database views as secure RESTful web services, consumed by "
            "mobile applications, APEX front-ends, and third-party integration platforms.",

            "Implemented OAuth2-based authentication on ORDS endpoints with role-based "
            "privilege assignment and rate limiting, enabling external partner API access "
            "to Oracle data while maintaining enterprise security standards.",
        ],
        "summary_tag": "ORDS REST service development",
        "exp_slot": "exp1",
        "recruiter_why": "ORDS is the bridge between Oracle DB and modern APIs — showing this skill doubles your APEX role match rate.",
    },

    # ══ ORACLE PL/SQL ═════════════════════════════════════════════════════════

    "pl/sql": {
        "skill_entry": "Oracle PL/SQL | Stored Procedures | Packages | Triggers | Performance Tuning",
        "bullets": [
            "Developed complex Oracle PL/SQL packages, stored procedures, functions, "
            "and database triggers to implement business logic, data validation, "
            "and batch processing routines supporting financial and operational systems on Oracle 19c.",

            "Optimized critical PL/SQL batch processes using BULK COLLECT, FORALL, "
            "and parallel query techniques, reducing nightly processing runtime "
            "from 6 hours to 90 minutes for an 80-million-row financial ledger workload.",
        ],
        "summary_tag": "PL/SQL development and optimization",
        "exp_slot": "exp1",
        "recruiter_why": "PL/SQL is Oracle's core language — without it explicitly listed, SQL-only candidates flood in above you.",
    },

    "performance tuning": {
        "skill_entry": "Oracle SQL Tuning | EXPLAIN PLAN | AWR Reports | Index Optimization",
        "bullets": [
            "Performed Oracle SQL and PL/SQL performance tuning using EXPLAIN PLAN, "
            "AWR/ADDM reports, SQL Trace, and TKPROF to diagnose and resolve slow-running "
            "queries, reducing critical report runtimes by 60–80% in production environments.",

            "Implemented index optimization strategies including composite indexes, "
            "function-based indexes, and partition pruning techniques on high-volume "
            "transactional tables, eliminating full-table scans on tables exceeding 100 million rows.",
        ],
        "summary_tag": "Oracle performance tuning",
        "exp_slot": "exp1",
        "recruiter_why": "Performance tuning is always listed under 'required' — it signals hands-on depth that juniors can't fake.",
    },

    "bulk collect": {
        "skill_entry": "PL/SQL Bulk Processing | BULK COLLECT | FORALL | High-Volume Data Operations",
        "bullets": [
            "Optimized high-volume Oracle PL/SQL batch processes using BULK COLLECT "
            "and FORALL constructs to process millions of records with minimal context "
            "switching between SQL and PL/SQL engines, achieving 10x throughput improvement.",

            "Implemented cursor-based bulk processing patterns with dynamic LIMIT clause "
            "tuning for memory-efficient handling of variable-volume data loads "
            "in nightly ETL and financial period-close batch jobs.",
        ],
        "summary_tag": "bulk PL/SQL processing",
        "exp_slot": "exp1",
        "recruiter_why": "BULK COLLECT/FORALL is a litmus test for senior PL/SQL developers — include it to pass technical screening.",
    },

    # ══ ORACLE EBS ════════════════════════════════════════════════════════════

    "oracle e-business suite": {
        "skill_entry": "Oracle E-Business Suite (EBS) R12 | Financials | HRMS | SCM | Technical Consulting",
        "bullets": [
            "Delivered Oracle EBS R12 implementations and upgrades covering Financials (GL, AP, AR, FA), "
            "HRMS, Purchasing, and Order Management modules — leading technical workstreams including "
            "data conversion, interface development, and custom report delivery.",

            "Developed Oracle EBS technical deliverables including PL/SQL packages, "
            "Oracle Reports, XML Publisher templates, Workflow customizations, and "
            "CUSTOM.pll modifications to extend EBS functionality per client requirements.",
        ],
        "summary_tag": "Oracle EBS R12 implementations",
        "exp_slot": "exp1",
        "recruiter_why": "EBS experience is still in high demand for support/upgrade engagements — always list it when you have it.",
    },

    "oracle forms": {
        "skill_entry": "Oracle Forms | CUSTOM.pll | Form Personalization | Form Triggers",
        "bullets": [
            "Customized Oracle Forms using CUSTOM.pll and form-level triggers to implement "
            "client-specific defaulting logic, cross-field validations, and UI enhancements "
            "without modifying seeded code, ensuring upgrade compatibility.",

            "Built Oracle Form personalizations and user-level customizations using "
            "Oracle Applications Personalization framework to add context-sensitive "
            "folders, tabs, and field-level controls aligned with business process requirements.",
        ],
        "summary_tag": "Oracle Forms customization",
        "exp_slot": "exp2",
        "recruiter_why": "Oracle Forms is rare now — if you have it, show it; it's a senior EBS differentiator.",
    },

    "oracle reports": {
        "skill_entry": "Oracle Reports | XML Publisher | RTF Templates | Concurrent Programs",
        "bullets": [
            "Developed Oracle EBS Reports using Oracle Report Builder and XML Publisher, "
            "covering financial statements, AR/AP aging, purchase order prints, and "
            "HR payroll reports with multi-language and multi-currency support.",

            "Registered custom Oracle Reports as concurrent programs with parameter "
            "validation, request groups assignment, and output format configuration "
            "(PDF, Excel, HTML) integrated with Oracle EBS menu structures.",
        ],
        "summary_tag": "Oracle Reports and concurrent program development",
        "exp_slot": "exp2",
        "recruiter_why": "Report development is always in EBS project scope — listing it confirms hands-on delivery experience.",
    },

    "oracle workflow": {
        "skill_entry": "Oracle Workflow | AME | Approval Rules | Notification Mailer",
        "bullets": [
            "Designed and administered Oracle Workflow processes for purchase order approvals, "
            "expense report routing, and HR action notifications — including custom notification "
            "templates, escalation rules, and Notification Mailer configuration.",

            "Implemented Oracle Approvals Management Engine (AME) rules for dynamic approval "
            "hierarchy configuration based on transaction amount, cost center, and job level "
            "attributes, replacing hardcoded approval chains with business-user-maintainable rules.",
        ],
        "summary_tag": "Oracle Workflow and AME configuration",
        "exp_slot": "exp2",
        "recruiter_why": "Workflow and AME are core EBS technical skills — explicitly listed in most EBS technical JDs.",
    },

    # ══ ORACLE ETL / INTEGRATION ══════════════════════════════════════════════

    "informatica": {
        "skill_entry": "Informatica PowerCenter | IICS | ETL Development | Data Integration",
        "bullets": [
            "Designed and developed Informatica PowerCenter ETL workflows to extract, "
            "cleanse, transform, and load data from source systems (ERP, CRM, HR) "
            "into data warehouse environments, supporting financial, sales, and HR reporting.",

            "Built reusable Informatica mappings and mapplets applying data quality rules, "
            "SCD Type 1/2 logic, lookup transformations, and aggregation functions to "
            "process 50M+ rows daily with 99.9% data accuracy and full audit trail.",
        ],
        "summary_tag": "Informatica PowerCenter ETL development",
        "exp_slot": "exp1",
        "recruiter_why": "Informatica is the #1 ETL tool listed on data integration JDs — always make it prominent.",
    },

    "datastage": {
        "skill_entry": "IBM DataStage | Parallel Jobs | CDC | Data Warehouse ETL",
        "bullets": [
            "Developed IBM DataStage parallel jobs for high-volume ETL processing including "
            "change data capture (CDC), slowly changing dimension management, "
            "data quality validation, and real-time streaming pipelines from OLTP to DWH.",

            "Designed DataStage job sequences with dependency management, restart-ability, "
            "and parameter sets for environment portability, supporting daily batch processing "
            "of 100M+ records across financial and customer data domains.",
        ],
        "summary_tag": "IBM DataStage ETL development",
        "exp_slot": "exp1",
        "recruiter_why": "DataStage is listed on most IBM/financial sector ETL JDs — if you have it, it's a strong differentiator.",
    },

    "odi": {
        "skill_entry": "Oracle Data Integrator (ODI) | Knowledge Modules | IKM/LKM | ETL",
        "bullets": [
            "Developed Oracle Data Integrator (ODI) mappings, packages, and load plans "
            "to integrate Oracle EBS, Oracle Cloud, and third-party source systems into "
            "Oracle data warehouse environments using standard and custom Knowledge Modules.",

            "Configured ODI topology, repositories, and agent setup for development "
            "and production environments, implementing ODI-based data quality rules "
            "and error handling through E-LT architecture for high-performance data loads.",
        ],
        "summary_tag": "Oracle Data Integrator (ODI) development",
        "exp_slot": "exp1",
        "recruiter_why": "ODI is Oracle's native ETL — listing it is essential for any Oracle-stack data integration role.",
    },

    "goldengate": {
        "skill_entry": "Oracle GoldenGate | Real-Time CDC | Database Replication | Zero-Downtime Migration",
        "bullets": [
            "Implemented Oracle GoldenGate for real-time change data capture and database "
            "replication between Oracle source and target systems, enabling active-active "
            "configurations for high availability and zero-downtime database migrations.",

            "Configured GoldenGate Extract, Pump, and Replicat processes for cross-platform "
            "database migration from Oracle 12c to 19c with sub-second replication lag, "
            "supporting phased cutover strategy for a 2TB production database.",
        ],
        "summary_tag": "Oracle GoldenGate replication",
        "exp_slot": "exp2",
        "recruiter_why": "GoldenGate is a specialist skill that commands premium rates — always list it when you've used it.",
    },

    # ══ NETSUITE ══════════════════════════════════════════════════════════════

    "netsuite": {
        "skill_entry": "Oracle NetSuite | SuiteScript | NetSuite ERP | Financial Management",
        "bullets": [
            "Led Oracle NetSuite implementations covering Financials, Inventory, "
            "Order Management, and CRM modules — delivering end-to-end configuration, "
            "data migration, and user training for mid-market and enterprise clients.",

            "Configured NetSuite organizational structure including subsidiaries, "
            "accounting periods, chart of accounts, tax codes, and approval routing "
            "workflows aligned to client financial reporting and compliance requirements.",
        ],
        "summary_tag": "Oracle NetSuite ERP implementations",
        "exp_slot": "exp1",
        "recruiter_why": "NetSuite is a growing platform — listing it opens cloud ERP JDs beyond traditional Oracle stack.",
    },

    "suitescript": {
        "skill_entry": "SuiteScript 2.0 | User Event Scripts | Client Scripts | Scheduled Scripts | RESTlets",
        "bullets": [
            "Developed SuiteScript 2.0 customizations including User Event Scripts "
            "for workflow automation, Client Scripts for real-time form validation, "
            "Scheduled Scripts for batch processing, and RESTlets for external API integrations.",

            "Built SuiteScript-based custom modules to extend NetSuite with client-specific "
            "business logic for commission calculations, multi-level approval workflows, "
            "and automated vendor payment scheduling — replacing manual finance team processes.",
        ],
        "summary_tag": "SuiteScript 2.0 development",
        "exp_slot": "exp1",
        "recruiter_why": "SuiteScript is the differentiator between functional and technical NetSuite consultants — always list it.",
    },

    # ══ ORACLE FUSION ═════════════════════════════════════════════════════════

    "oracle fusion": {
        "skill_entry": "Oracle Fusion | ERP Cloud | Financials Cloud | SCM Cloud | Technical Development",
        "bullets": [
            "Delivered Oracle Fusion Cloud technical workstreams covering FBDI data loads, "
            "OTBI/BI Publisher reporting, REST API integrations, and VBCS extensions "
            "across Oracle ERP Cloud Financials, Procurement, and SCM modules.",

            "Developed Oracle Fusion technical deliverables including Application Composer "
            "customizations, Page Composer personalizations, and Groovy scripting for "
            "field defaulting and validation without seeded code modification.",
        ],
        "summary_tag": "Oracle Fusion Cloud technical delivery",
        "exp_slot": "exp1",
        "recruiter_why": "Oracle Fusion is the flagship cloud ERP — it anchors your resume positioning at the top of the market.",
    },

    "vbcs": {
        "skill_entry": "Oracle Visual Builder Cloud Service (VBCS) | UI Extensions | REST Services",
        "bullets": [
            "Built Oracle Visual Builder Cloud Service (VBCS) applications to extend "
            "Oracle ERP Cloud and HCM Cloud UI with custom pages, embedded screens, "
            "and service connections — delivering tailored user experiences without "
            "on-premise development or upgrade risk.",

            "Designed VBCS business object definitions, REST service connections, "
            "and action chains to create responsive, mobile-friendly extensions "
            "for expense approval, purchase requisition, and HR self-service workflows.",
        ],
        "summary_tag": "VBCS application development",
        "exp_slot": "exp2",
        "recruiter_why": "VBCS is Oracle's recommended UI extension approach — listing it signals you're current on Oracle Cloud strategy.",
    },

    "adf": {
        "skill_entry": "Oracle ADF | ADF BC | ADF Faces | JDeveloper | OAF Personalization",
        "bullets": [
            "Developed Oracle ADF-based UI extensions and page-level customizations "
            "using JDeveloper, implementing business component layer (ADF BC) "
            "with entity objects, view objects, and application modules for "
            "data-binding to ADF Faces rich UI components.",

            "Built OAF personalizations and ADF customizations on Oracle EBS and "
            "Fusion pages using MDS sandbox framework, ensuring changes were "
            "upgrade-safe and environment-portable across development, test, and production.",
        ],
        "summary_tag": "Oracle ADF development",
        "exp_slot": "exp2",
        "recruiter_why": "ADF is still in most Oracle technical JDs for Fusion support roles — show it if you have it.",
    },

    # ══ CLOUD / GENERAL ═══════════════════════════════════════════════════════

    "azure data factory": {
        "skill_entry": "Azure Data Factory (ADF) | Pipeline Orchestration | Cloud ETL | Linked Services",
        "bullets": [
            "Designed and deployed Azure Data Factory pipelines to orchestrate data movement "
            "from on-premise SQL Server, Oracle, and flat-file sources into Azure Data Lake "
            "and Synapse Analytics, supporting cloud data warehouse modernization.",

            "Built ADF parameterized pipeline templates with dynamic linked services, "
            "copy activities, data flow transformations, and failure notification logic, "
            "replacing legacy Informatica workflows with cloud-native processing.",
        ],
        "summary_tag": "Azure Data Factory pipeline development",
        "exp_slot": "exp1",
        "recruiter_why": "ADF is the most-listed Microsoft ETL tool — adding it signals cloud platform breadth.",
    },

    "spark": {
        "skill_entry": "Apache Spark | PySpark | Databricks | Distributed Processing",
        "bullets": [
            "Developed PySpark data processing jobs on Databricks to perform distributed "
            "transformation of large-scale datasets (1TB+) from raw data lake zones to "
            "curated analytical layers, replacing sequential ETL with parallel cluster processing.",

            "Built Spark streaming pipelines for near-real-time event processing from "
            "Kafka topics, applying sessionization, deduplication, and enrichment logic "
            "before landing processed data into Delta Lake tables for downstream BI consumption.",
        ],
        "summary_tag": "Apache Spark / PySpark development",
        "exp_slot": "exp1",
        "recruiter_why": "Spark is in 80% of modern data engineering JDs — if you have it, surface it prominently.",
    },

    "data modeling": {
        "skill_entry": "Data Modeling | Dimensional Modeling | Star Schema | Data Vault | ERD",
        "bullets": [
            "Designed dimensional data models including star schema fact and dimension tables, "
            "slowly changing dimension (SCD) Type 1/2/3 strategies, and conformed dimensions "
            "across finance, HR, and sales subject areas for enterprise data warehouse.",

            "Developed logical and physical data models using ER/Studio and SQL Developer "
            "Data Modeler, documenting entity relationships, cardinality, referential integrity "
            "rules, and partitioning strategies for high-volume OLAP environments.",
        ],
        "summary_tag": "dimensional data modeling",
        "exp_slot": "exp2",
        "recruiter_why": "Data modeling separates architects from developers — listing it targets higher-value roles.",
    },

    # ══ DEVOPS / CLOUD ════════════════════════════════════════════════════════

    "kubernetes": {
        "skill_entry": "Kubernetes (K8s) | Helm | Kustomize | Container Orchestration | EKS/AKS/GKE",
        "bullets": [
            "Designed and managed production Kubernetes clusters on AWS EKS, deploying "
            "microservices using Helm charts, HPA auto-scaling, and rolling update strategies, "
            "achieving 99.9% uptime SLA and reducing deployment incidents by 60%.",

            "Implemented Kubernetes RBAC, network policies, and pod security standards "
            "across multi-tenant namespaces, securing workloads per CIS Kubernetes Benchmark "
            "and integrating OPA Gatekeeper for policy enforcement.",
        ],
        "summary_tag": "Kubernetes container orchestration",
        "exp_slot": "exp1",
        "recruiter_why": "Kubernetes is the #1 skill in DevOps JDs — without it, most pipelines auto-screen you out.",
    },

    "terraform": {
        "skill_entry": "Terraform | Infrastructure as Code (IaC) | Terraform Cloud | Atlantis | State Management",
        "bullets": [
            "Authored modular Terraform configurations to provision AWS/Azure cloud infrastructure "
            "(VPC, EKS, RDS, IAM roles, S3, CloudFront) across dev/staging/prod environments, "
            "reducing manual provisioning time from days to under 30 minutes.",

            "Implemented Terraform remote state with S3 backend + DynamoDB locking, "
            "enforced module versioning through private Terraform registry, and integrated "
            "tfsec and Checkov into CI/CD for pre-deploy security scanning.",
        ],
        "summary_tag": "Terraform infrastructure-as-code",
        "exp_slot": "exp1",
        "recruiter_why": "Terraform appears in 75% of DevOps/Cloud JDs — it's the IaC lingua franca employers expect.",
    },

    "ci/cd": {
        "skill_entry": "CI/CD | Jenkins | GitHub Actions | GitLab CI | ArgoCD | GitOps",
        "bullets": [
            "Designed end-to-end CI/CD pipelines using GitHub Actions and ArgoCD to automate "
            "build, test, security scan (SAST/DAST), containerization, and Kubernetes deployment, "
            "cutting release cycle from bi-weekly to on-demand multiple-times-per-day delivery.",

            "Migrated 40+ legacy Jenkins pipelines to declarative Jenkinsfile and GitHub Actions "
            "workflows, standardizing environment variables, secret injection via HashiCorp Vault, "
            "and parallel test execution, reducing average build time by 45%.",
        ],
        "summary_tag": "CI/CD pipeline design and automation",
        "exp_slot": "exp1",
        "recruiter_why": "CI/CD is the core DevOps competency — every job posting lists it; missing it means automatic screen-out.",
    },

    "docker": {
        "skill_entry": "Docker | Containerization | Docker Compose | Multi-stage Builds | Container Registry",
        "bullets": [
            "Containerized 15+ microservices using Docker multi-stage builds, reducing image sizes "
            "by 70% through distroless base images and layer caching optimization, and published "
            "to AWS ECR with automated vulnerability scanning via Trivy.",

            "Authored Docker Compose configurations for local development environments replicating "
            "production topology (app, database, cache, message broker), enabling engineers to "
            "onboard and run full-stack services within minutes.",
        ],
        "summary_tag": "Docker containerization",
        "exp_slot": "exp1",
        "recruiter_why": "Docker is baseline for DevOps/SWE roles — its absence signals limited cloud-native experience.",
    },

    "ansible": {
        "skill_entry": "Ansible | Configuration Management | Playbooks | Ansible Tower/AWX | Automation",
        "bullets": [
            "Developed Ansible playbooks and roles to automate OS hardening, package installation, "
            "user provisioning, and application deployment across 200+ servers, replacing "
            "manual runbooks and eliminating configuration drift.",

            "Integrated Ansible with CI/CD pipelines to enforce idempotent infrastructure "
            "configuration, using Ansible Tower for role-based access, scheduling, and "
            "centralized audit logging of automation runs.",
        ],
        "summary_tag": "Ansible configuration management",
        "exp_slot": "exp2",
        "recruiter_why": "Ansible is the top configuration management tool in enterprise DevOps — shows automation breadth.",
    },

    "prometheus": {
        "skill_entry": "Prometheus | Grafana | Observability | Alertmanager | Metrics | Dashboards",
        "bullets": [
            "Deployed Prometheus + Grafana monitoring stack on Kubernetes using kube-prometheus-stack "
            "Helm chart, creating dashboards for cluster health, service SLOs, and business KPIs; "
            "configured Alertmanager for PagerDuty and Slack escalation routing.",

            "Instrumented Python and Go microservices with Prometheus client libraries, "
            "exposing custom business metrics (request rate, error budget, queue depth) "
            "alongside infrastructure metrics for end-to-end observability.",
        ],
        "summary_tag": "Prometheus/Grafana observability stack",
        "exp_slot": "exp1",
        "recruiter_why": "Observability is mandatory for SRE/Platform roles — Prometheus+Grafana is the standard stack.",
    },

    "infrastructure as code": {
        "skill_entry": "Infrastructure as Code (IaC) | Terraform | CloudFormation | Pulumi | GitOps",
        "bullets": [
            "Implemented IaC strategy across all cloud accounts using Terraform with modular design, "
            "remote state, and policy-as-code guardrails, enabling full environment rebuild "
            "from scratch in under 20 minutes and eliminating snowflake servers.",

            "Established GitOps workflow with IaC: all infrastructure changes went through "
            "pull requests, automated plan reviews, and ArgoCD drift detection, "
            "providing full change audit trail and rollback capability.",
        ],
        "summary_tag": "infrastructure as code strategy",
        "exp_slot": "exp1",
        "recruiter_why": "IaC is the #1 DevOps principle — listing it with concrete tools shows strategic thinking.",
    },

    # ══ AI / ML ═══════════════════════════════════════════════════════════════

    "langchain": {
        "skill_entry": "LangChain | LangGraph | RAG | LLM Orchestration | Agent Pipelines",
        "bullets": [
            "Built production RAG (Retrieval-Augmented Generation) pipeline using LangChain, "
            "OpenAI embeddings, and Pinecone vector store to enable semantic search over 50K+ "
            "enterprise documents, reducing support ticket resolution time by 40%.",

            "Developed multi-agent LangGraph workflows for automated document processing, "
            "integrating tool-calling, memory management, and human-in-the-loop checkpoints, "
            "handling 1,000+ daily requests with sub-3-second P95 latency.",
        ],
        "summary_tag": "LangChain/LLM application development",
        "exp_slot": "exp1",
        "recruiter_why": "LangChain is the most-cited LLM framework in AI engineering JDs — it signals practical GenAI experience.",
    },

    "rag": {
        "skill_entry": "RAG | Vector Databases (Pinecone/ChromaDB/Weaviate) | Embeddings | Semantic Search",
        "bullets": [
            "Designed Retrieval-Augmented Generation (RAG) system using OpenAI text-embedding-3-large, "
            "ChromaDB vector store, and LangChain for document chunking, retrieval, and LLM synthesis, "
            "achieving 85% answer accuracy on domain-specific Q&A evaluation set.",

            "Implemented advanced RAG techniques including hybrid search (dense + sparse), "
            "re-ranking with cross-encoders, and query decomposition, improving precision@5 "
            "retrieval score by 28% over baseline similarity search.",
        ],
        "summary_tag": "RAG pipeline architecture",
        "exp_slot": "exp1",
        "recruiter_why": "RAG is the foundational GenAI pattern — every AI engineer JD now expects it.",
    },

    "pytorch": {
        "skill_entry": "PyTorch | Deep Learning | Neural Networks | Model Training | CUDA",
        "bullets": [
            "Trained transformer-based classification models in PyTorch, implementing custom "
            "dataset loaders, mixed-precision training (AMP), gradient accumulation, and "
            "learning rate scheduling, achieving 94% F1 on production classification task.",

            "Fine-tuned pre-trained Hugging Face models (BERT, RoBERTa, LLaMA) using PEFT/LoRA "
            "for domain-specific NLP tasks, reducing training compute cost by 70% vs. full "
            "fine-tuning while maintaining performance within 2% of full-tuning baseline.",
        ],
        "summary_tag": "PyTorch deep learning model development",
        "exp_slot": "exp1",
        "recruiter_why": "PyTorch is the dominant ML framework — it's in nearly every ML/AI engineer job description.",
    },

    "mlflow": {
        "skill_entry": "MLflow | Experiment Tracking | Model Registry | ML Pipeline Management",
        "bullets": [
            "Implemented MLflow experiment tracking across team ML projects, logging parameters, "
            "metrics, and artifacts for every training run, enabling reproducibility and "
            "systematic hyperparameter comparison across 200+ experiments.",

            "Deployed MLflow Model Registry as central model governance hub, managing model "
            "lifecycle states (Staging → Production → Archived), integrating with CI/CD for "
            "automated model validation before promotion.",
        ],
        "summary_tag": "MLflow experiment tracking and model registry",
        "exp_slot": "exp2",
        "recruiter_why": "MLflow is the standard MLOps tracking tool — shows you work at production ML scale, not just notebooks.",
    },

    "llm": {
        "skill_entry": "LLMs | OpenAI GPT-4 | Anthropic Claude | Prompt Engineering | Fine-tuning",
        "bullets": [
            "Integrated OpenAI GPT-4 and Anthropic Claude APIs into customer-facing applications, "
            "designing structured prompt templates, few-shot examples, and output parsers to deliver "
            "reliable JSON responses at scale with <1% error rate.",

            "Developed LLM evaluation framework using automated benchmarks and human-in-the-loop "
            "review to measure hallucination rate, factuality, and instruction-following, "
            "driving prompt and model selection decisions for production deployment.",
        ],
        "summary_tag": "LLM API integration and prompt engineering",
        "exp_slot": "exp1",
        "recruiter_why": "LLMs are the hottest skill in tech in 2025 — concrete examples of production LLM work stand out.",
    },

    # ══ CYBERSECURITY ════════════════════════════════════════════════════════

    "zero trust": {
        "skill_entry": "Zero Trust Architecture | ZTNA | Identity-Aware Proxy | Microsegmentation",
        "bullets": [
            "Architected Zero Trust network access (ZTNA) model for remote workforce, deploying "
            "Cloudflare Access as identity-aware proxy to replace legacy VPN, reducing attack "
            "surface by eliminating implicit network trust for 3,000+ users.",

            "Implemented zero trust principles across cloud workloads: workload identity via "
            "service accounts, mTLS with Istio service mesh, and OPA policy enforcement "
            "for lateral movement prevention in Kubernetes environments.",
        ],
        "summary_tag": "zero trust security architecture",
        "exp_slot": "exp1",
        "recruiter_why": "Zero trust is the dominant security model in enterprise — listing it shows architectural thinking.",
    },

    "penetration testing": {
        "skill_entry": "Penetration Testing | OWASP | Burp Suite | Kali Linux | Vulnerability Assessment",
        "bullets": [
            "Conducted web application penetration tests following OWASP Testing Guide methodology, "
            "identifying OWASP Top 10 vulnerabilities (SQLi, XSS, IDOR, SSRF) and delivering "
            "risk-rated findings reports with remediation guidance to development teams.",

            "Performed internal network penetration tests using Nmap, Metasploit, BloodHound, "
            "and Impacket to identify misconfigurations, privilege escalation paths, and "
            "lateral movement opportunities, remediating critical findings within 30-day SLA.",
        ],
        "summary_tag": "penetration testing and vulnerability assessment",
        "exp_slot": "exp1",
        "recruiter_why": "Pentest experience is a premium differentiator — fewer than 20% of security candidates have hands-on experience.",
    },

    "siem": {
        "skill_entry": "SIEM | Splunk | Microsoft Sentinel | IBM QRadar | Log Analysis | Threat Detection",
        "bullets": [
            "Deployed and tuned Splunk SIEM for 500+ log sources, developing custom correlation "
            "rules and SPL queries to detect brute force, lateral movement, and data exfiltration "
            "patterns, reducing mean-time-to-detect (MTTD) by 55%.",

            "Integrated cloud security logs (AWS CloudTrail, Azure Activity Log, GCP Audit) "
            "into SIEM platform, creating dashboards for SOC analysts covering identity-based "
            "threats, configuration drift, and anomalous API activity.",
        ],
        "summary_tag": "SIEM implementation and threat detection",
        "exp_slot": "exp1",
        "recruiter_why": "SIEM/Splunk is foundational for SOC and security engineering roles — recruiters expect it by name.",
    },

    "devsecops": {
        "skill_entry": "DevSecOps | SAST/DAST | Snyk | SonarQube | Trivy | Container Security | Policy as Code",
        "bullets": [
            "Implemented DevSecOps pipeline integrating Snyk (SCA), SonarQube (SAST), and "
            "OWASP ZAP (DAST) into GitHub Actions CI/CD, enforcing security quality gates "
            "that blocked 95% of critical vulnerabilities before reaching production.",

            "Deployed OPA Gatekeeper policies on Kubernetes to enforce container security "
            "standards (non-root, read-only filesystems, resource limits), and integrated "
            "Trivy image scanning in ECR push pipeline, achieving 100% compliance.",
        ],
        "summary_tag": "DevSecOps pipeline security integration",
        "exp_slot": "exp1",
        "recruiter_why": "DevSecOps is the fastest-growing security sub-specialty — 'security shift-left' is now standard.",
    },

    # ══ FULL STACK / SOFTWARE DEV ════════════════════════════════════════════

    "react": {
        "skill_entry": "React.js | React Hooks | Redux/Zustand | TypeScript | Next.js",
        "bullets": [
            "Developed responsive single-page applications using React with TypeScript, "
            "implementing reusable component libraries, custom hooks, and Context API for state "
            "management, achieving 98+ Lighthouse performance score.",

            "Migrated legacy AngularJS application to React + Next.js with server-side rendering, "
            "reducing initial page load time by 65% and improving SEO indexing, deploying "
            "with incremental static regeneration on Vercel.",
        ],
        "summary_tag": "React.js / Next.js frontend development",
        "exp_slot": "exp1",
        "recruiter_why": "React is in 70% of frontend JDs — it's the default SPA framework employers expect.",
    },

    "spring boot": {
        "skill_entry": "Spring Boot | Spring MVC | Spring Security | JPA/Hibernate | Microservices",
        "bullets": [
            "Built RESTful microservices using Spring Boot with Spring Security (OAuth2/JWT), "
            "Spring Data JPA for PostgreSQL persistence, and OpenAPI/Swagger documentation, "
            "deployed on AWS ECS with blue-green deployment strategy.",

            "Implemented event-driven communication between Spring Boot microservices using "
            "Apache Kafka for asynchronous messaging and Spring Cloud Gateway as API gateway, "
            "handling 10,000+ TPS at P99 latency under 200ms.",
        ],
        "summary_tag": "Spring Boot microservices development",
        "exp_slot": "exp1",
        "recruiter_why": "Spring Boot is the dominant Java backend framework — Java roles almost universally require it.",
    },

    "microservices": {
        "skill_entry": "Microservices Architecture | REST APIs | gRPC | Event-Driven | Service Mesh",
        "bullets": [
            "Decomposed monolithic e-commerce application into 12 microservices following "
            "Domain-Driven Design principles, enabling independent deployment and scaling, "
            "reducing release cycle from monthly to daily.",

            "Designed microservices communication patterns including synchronous REST/gRPC for "
            "real-time calls and Kafka event streaming for eventual-consistency workflows, "
            "with Istio service mesh for observability and mTLS.",
        ],
        "summary_tag": "microservices architecture design",
        "exp_slot": "exp1",
        "recruiter_why": "Microservices is the architectural standard in cloud-native JDs — shows system design capability.",
    },

    "graphql": {
        "skill_entry": "GraphQL | Apollo Server | REST-to-GraphQL Migration | Schema Design | Resolvers",
        "bullets": [
            "Designed and implemented GraphQL API layer using Apollo Server to replace over-fetching "
            "REST endpoints, reducing mobile client payload size by 60% and improving "
            "app performance through declarative data fetching.",

            "Built schema-first GraphQL service with DataLoader batching to solve N+1 queries, "
            "persisted queries for performance, and depth-limiting + rate limiting for "
            "production security hardening.",
        ],
        "summary_tag": "GraphQL API design",
        "exp_slot": "exp2",
        "recruiter_why": "GraphQL is increasingly expected in modern API roles — shows knowledge beyond REST conventions.",
    },

    # ══ QA / TEST AUTOMATION ════════════════════════════════════════════════

    "selenium": {
        "skill_entry": "Selenium WebDriver | Page Object Model | TestNG/JUnit | Cross-browser Testing | Allure Reports",
        "bullets": [
            "Designed end-to-end test automation framework using Selenium WebDriver with Page "
            "Object Model (POM), TestNG, and Maven, covering 500+ test cases across 12 modules "
            "and reducing regression testing cycle from 3 days to 4 hours.",

            "Integrated Selenium grid into Jenkins CI/CD pipeline for parallel cross-browser "
            "test execution on Chrome, Firefox, and Safari, generating Allure reports with "
            "screenshot capture on failure and Slack test-result notifications.",
        ],
        "summary_tag": "Selenium WebDriver test automation",
        "exp_slot": "exp1",
        "recruiter_why": "Selenium is still the #1 UI automation tool listed in QA JDs — presence is table-stakes.",
    },

    "pytest": {
        "skill_entry": "pytest | Python Test Automation | Fixtures | Mocking | Test Coverage | pytest-bdd",
        "bullets": [
            "Built pytest-based API and unit test suite with fixtures, parameterized tests, "
            "and monkeypatching, achieving 85% code coverage across core business logic modules, "
            "integrated into GitHub Actions CI with coverage gate enforcement.",

            "Developed pytest-bdd BDD framework with Gherkin feature files and step definitions "
            "for acceptance testing, enabling product owners to review test scenarios in "
            "plain English and reducing ambiguity in acceptance criteria.",
        ],
        "summary_tag": "pytest Python test automation",
        "exp_slot": "exp1",
        "recruiter_why": "pytest is the dominant Python testing framework — Python-heavy shops list it explicitly.",
    },

    "api testing": {
        "skill_entry": "API Testing | Postman | REST Assured | Newman | Contract Testing | Pact",
        "bullets": [
            "Developed comprehensive API test collections in Postman covering happy-path, "
            "boundary, negative, and security test scenarios for REST and GraphQL APIs, "
            "automated with Newman in CI pipeline running on every pull request.",

            "Implemented consumer-driven contract testing using Pact to prevent integration "
            "regressions between microservices, catching breaking changes before deployment "
            "and reducing production incidents by 40% in service-to-service communication.",
        ],
        "summary_tag": "API test automation",
        "exp_slot": "exp1",
        "recruiter_why": "API testing is now its own specialty — SDET JDs list Postman/REST Assured as required tools.",
    },

    "performance testing": {
        "skill_entry": "Performance Testing | JMeter | k6 | Gatling | Load Testing | Stress Testing",
        "bullets": [
            "Designed JMeter performance test plans simulating 10,000 concurrent users for "
            "e-commerce checkout flow, identifying database connection pool exhaustion and "
            "N+1 query patterns that caused 8-second P95 latency under load.",

            "Implemented k6 load testing as GitHub Actions CI stage for API performance "
            "regression detection, failing builds when P95 latency exceeded SLO thresholds, "
            "preventing 3 performance regressions from reaching production.",
        ],
        "summary_tag": "performance and load testing",
        "exp_slot": "exp2",
        "recruiter_why": "Performance testing expertise is scarce and highly valued — few QA engineers have it.",
    },

    # ══ MODERN DATA ENGINEERING ══════════════════════════════════════════════

    "dbt": {
        "skill_entry": "dbt (data build tool) | dbt Cloud | SQL Transformations | Data Lineage | Tests",
        "bullets": [
            "Implemented dbt project with 100+ models across staging, intermediate, and mart "
            "layers, enforcing schema tests, referential integrity checks, and source freshness "
            "assertions, reducing data quality incidents by 70%.",

            "Migrated legacy stored procedure-based transformations to dbt models with full "
            "lineage documentation, column-level tests, and CI/CD integration via dbt Cloud "
            "slim CI, enabling data engineers to iterate without breaking downstream consumers.",
        ],
        "summary_tag": "dbt data transformation development",
        "exp_slot": "exp1",
        "recruiter_why": "dbt is the hottest data transformation tool — Analytics Engineering roles now require it.",
    },

    "kafka": {
        "skill_entry": "Apache Kafka | Kafka Streams | Confluent | Event Streaming | Producer/Consumer",
        "bullets": [
            "Designed Kafka-based event streaming architecture to decouple microservices, "
            "implementing topic partitioning strategy, consumer group management, and "
            "exactly-once semantics for financial transaction processing.",

            "Built Kafka Streams applications for real-time ETL processing, performing "
            "stateful aggregations, windowed joins, and anomaly detection on 500K+ events/minute "
            "with under 100ms end-to-end latency.",
        ],
        "summary_tag": "Apache Kafka event streaming",
        "exp_slot": "exp1",
        "recruiter_why": "Kafka appears in 60% of Data Engineering and Backend JDs — real-time streaming is now baseline.",
    },

    "snowflake": {
        "skill_entry": "Snowflake | Snowpark | Dynamic Tables | Time Travel | Data Sharing | Streams",
        "bullets": [
            "Migrated on-premise Oracle data warehouse to Snowflake, designing multi-cluster "
            "virtual warehouses, row access policies, and column masking for PII compliance, "
            "reducing query costs by 45% through automated suspension and result caching.",

            "Developed Snowflake Streams and Tasks for change data capture (CDC) pipelines, "
            "processing incremental updates from transactional systems into analytical tables "
            "with sub-hourly freshness, replacing daily batch ETL jobs.",
        ],
        "summary_tag": "Snowflake cloud data warehouse",
        "exp_slot": "exp1",
        "recruiter_why": "Snowflake is the most-listed modern data warehouse tool — its absence is noticed by data engineering recruiters.",
    },

    "airflow": {
        "skill_entry": "Apache Airflow | DAGs | Cloud Composer | MWAA | Pipeline Orchestration",
        "bullets": [
            "Developed Airflow DAGs to orchestrate multi-step ETL pipelines spanning "
            "Snowflake, S3, dbt, and Spark, implementing retry logic, SLA monitoring, "
            "and Slack alerting for failed tasks in production.",

            "Migrated Airflow deployment to Kubernetes using KubernetesExecutor for dynamic "
            "worker scaling, reducing infrastructure cost by 60% vs. fixed CeleryExecutor cluster "
            "while enabling per-task resource isolation.",
        ],
        "summary_tag": "Apache Airflow pipeline orchestration",
        "exp_slot": "exp1",
        "recruiter_why": "Airflow is the de facto orchestration standard — over 80% of data engineering roles list it.",
    },
}

# ── Experience block detector ─────────────────────────────────────────────────

_YEAR_RANGE_RE = re.compile(
    r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)?\.?\s*'
    r'(19|20)\d{2}\s*[-–to]+\s*((19|20)\d{2}|present|current|till\s*date|date)',
    re.I
)

def _count_experience_blocks(resume_text: str) -> int:
    matches = _YEAR_RANGE_RE.findall(resume_text)
    return max(len(matches), 1)


# ── Summary generator ─────────────────────────────────────────────────────────

_DOMAIN_SUMMARY_TEMPLATES: dict[str, tuple[str, str, str]] = {
    # domain_hint → (default_role_fallback, platform_phrase, value_phrase)
    "devops": (
        "DevOps Engineer",
        "cloud-native infrastructure and CI/CD automation",
        "delivering scalable, secure, and automated infrastructure solutions",
    ),
    "cloud": (
        "Cloud Engineer",
        "cloud infrastructure and platform automation",
        "building reliable, cost-efficient cloud architectures",
    ),
    "kubernetes": (
        "Platform Engineer",
        "Kubernetes and container orchestration",
        "enabling high-availability microservices platforms",
    ),
    "sre": (
        "Site Reliability Engineer",
        "reliability engineering and observability",
        "driving SLO compliance and incident-response excellence",
    ),
    "ai": (
        "AI/ML Engineer",
        "LLM applications and machine learning systems",
        "delivering production-grade GenAI solutions",
    ),
    "machine learning": (
        "Machine Learning Engineer",
        "machine learning and data science",
        "translating data into predictive models and intelligent systems",
    ),
    "data engineer": (
        "Data Engineer",
        "data pipeline and analytics platform development",
        "building reliable, scalable data infrastructure",
    ),
    "security": (
        "Cybersecurity Engineer",
        "security engineering and threat mitigation",
        "hardening systems against evolving threat landscapes",
    ),
    "qa": (
        "QA Automation Engineer",
        "test automation and quality engineering",
        "delivering high-quality software through comprehensive test coverage",
    ),
    "salesforce": (
        "Salesforce Developer",
        "Salesforce platform customization and development",
        "enabling business processes through Salesforce solutions",
    ),
    "sap": (
        "SAP Consultant",
        "SAP implementation and customization",
        "translating business requirements into SAP technical solutions",
    ),
    "servicenow": (
        "ServiceNow Developer",
        "ServiceNow platform development and ITSM automation",
        "streamlining IT service management workflows",
    ),
    "workday": (
        "Workday Consultant",
        "Workday HCM and Finance configuration",
        "delivering end-to-end Workday implementations",
    ),
    "oracle": (
        "Oracle Technical Consultant",
        "Oracle Cloud implementations and technical solutions",
        "translating complex business requirements into scalable Oracle configurations and integrations",
    ),
}


def _infer_domain_summary(jd_title: str) -> tuple[str, str, str]:
    """Detect summary template from JD title keywords."""
    title_l = jd_title.lower()
    for kw, tmpl in _DOMAIN_SUMMARY_TEMPLATES.items():
        if kw in title_l:
            return tmpl
    # Default to Oracle for backward compat
    return _DOMAIN_SUMMARY_TEMPLATES["oracle"]


def _build_summary(
    jd_title: str,
    max_years: int,
    matched: list[str],
    missing: list[str],
    gap_breakdown: dict,
) -> str:
    """Generate a tailored professional summary for this specific JD."""
    role_fallback, platform_phrase, value_phrase = _infer_domain_summary(jd_title)
    role = jd_title.strip() if jd_title.strip() else role_fallback
    years_str = f"{max_years}+" if max_years >= 3 else "several"

    # Pick top skills from matched for summary body
    top_matched = [k for k in matched if len(k) > 4][:5]
    # Add the most critical missing skills that should be in summary
    top_missing  = gap_breakdown.get("critical", [])[:2] + gap_breakdown.get("required", [])[:2]
    skills_mentioned = list(dict.fromkeys(top_matched + top_missing))[:6]
    skills_str = ", ".join(skills_mentioned) if skills_mentioned else platform_phrase

    return (
        f"{role} with {years_str} years of hands-on experience in {platform_phrase}. "
        f"Expertise spans {skills_str}. "
        f"Proven track record of {value_phrase}, working across cross-functional teams "
        f"from requirements through delivery."
    )


# ── Main entry ────────────────────────────────────────────────────────────────

def generate_resume_content(
    missing: list[str],
    matched: list[str],
    jd_title: str,
    signals: dict,
    gap_breakdown: dict,
    resume_text: str,
) -> dict:
    """
    Returns placement-grouped, copy-paste-ready resume content for all missing keywords.

    Output structure:
        summary       : str  — full replacement summary paragraph
        skills_to_add : list[str]  — exact entries for Technical Skills section
        exp1_bullets  : list[dict] — {keyword, bullet, recruiter_why} for most-recent role
        exp2_bullets  : list[dict] — same for previous role
        unmatched_kws : list[str]  — missing keywords with no specific template
    """
    num_exp = _count_experience_blocks(resume_text)
    max_years = signals.get("max_years", 0)

    summary = _build_summary(jd_title, max_years, matched, missing, gap_breakdown)

    skills_to_add: list[str]  = []
    exp1_bullets:  list[dict] = []
    exp2_bullets:  list[dict] = []
    unmatched_kws: list[str]  = []

    seen_templates: set[str] = set()  # avoid duplicate bullets from aliases

    for raw_kw in missing:
        kw = ALIASES.get(raw_kw.lower(), raw_kw.lower())
        entry = PHRASE_BANK.get(kw)
        if not entry or kw in seen_templates:
            if not entry:
                unmatched_kws.append(raw_kw)
            continue
        seen_templates.add(kw)

        # Skills line
        if entry.get("skill_entry"):
            skills_to_add.append(entry["skill_entry"])

        # Bullet placement
        slot = entry.get("exp_slot", "exp1")
        bullet_obj = {
            "keyword":       raw_kw,
            "bullet":        entry["bullets"][0],
            "alt_bullet":    entry["bullets"][1] if len(entry["bullets"]) > 1 else "",
            "recruiter_why": entry.get("recruiter_why", ""),
        }
        if slot == "exp1" or num_exp < 2:
            exp1_bullets.append(bullet_obj)
        else:
            exp2_bullets.append(bullet_obj)

    return {
        "summary":       summary,
        "skills_to_add": skills_to_add,
        "exp1_bullets":  exp1_bullets,
        "exp2_bullets":  exp2_bullets,
        "unmatched_kws": unmatched_kws,
        "exp_blocks_detected": num_exp,
    }
