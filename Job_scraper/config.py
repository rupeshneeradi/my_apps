"""Central configuration — v1.0.8"""
import os
from dotenv import load_dotenv

load_dotenv()

VERSION = "1.0.8"

# ── Job types and their keyword sets ─────────────────────────────────────────
# These keywords are matched against the full job description text for ATS scoring.
# Expanded to cover all terms staffing agencies include in C2C postings.
JOB_TYPES = {
    "Oracle PL/SQL Developer": [
        # Core Oracle / SQL
        "oracle", "pl/sql", "plsql", "pl sql",
        "stored procedures", "stored procedure",
        "triggers", "packages", "functions",
        "oracle database", "oracle db",
        "oracle 19c", "oracle 21c", "oracle 12c", "oracle 11g",
        # SQL / tuning
        "performance tuning", "query optimization", "sql tuning",
        "execution plan", "explain plan", "index tuning",
        "partitioning", "indexing", "hints",
        # PL/SQL constructs
        "bulk collect", "forall", "dynamic sql", "ref cursor",
        "cursor", "exception handling",
        "materialized views", "sequences", "synonyms",
        "dbms_scheduler", "dbms_output", "utl_file",
        "dbms_sql", "dbms_metadata",
        # Analytical / reporting
        "analytical functions", "window functions",
        "oracle forms", "oracle reports",
        "xml publisher", "bi publisher",
        # Supporting tech
        "sql*plus", "toad", "sql developer",
        "oracle rac", "oracle exadata",
        "data pump", "exp imp",
    ],
    "Oracle HCM Developer": [
        # Cloud HCM modules
        "oracle hcm", "oracle fusion hcm", "hcm",
        "human capital management",
        "oracle cloud hcm", "fusion hcm", "hcm cloud",
        "core hr", "global hr", "oracle hr",
        # Payroll & benefits
        "payroll", "oracle payroll", "fusion payroll",
        "benefits administration", "benefits", "compensation",
        # Talent & workforce
        "talent management", "workforce management",
        "absence management", "performance management",
        "oracle recruiting", "recruiting cloud",
        "succession planning", "learning management",
        # Technical HCM tools
        "fast formula", "fastformula",
        "hcm extracts", "hcm data loader", "hdl",
        "hdi", "otl", "oracle time labor",
        "hcm spreadsheet loader",
        "rest api hcm", "hcm rest",
        "bi publisher hcm", "otbi hcm",
        # Security & config
        "role based access", "data roles",
        "sandbox", "flexfields",
        "people management", "organization management",
    ],
    "Oracle OIC Developer": [
        # OIC core
        "oracle oic", "oracle integration cloud", "oic",
        "oracle integration", "integration cloud",
        "oracle cloud integration", "ics",
        "integration cloud service",
        "oracle ipaas",
        # Protocols
        "rest api", "soap api", "web services",
        "restful", "json", "xml",
        "wsdl", "xsd", "xslt",
        # OIC adapters
        "ftp adapter", "rest adapter", "soap adapter",
        "database adapter", "file adapter",
        "atp adapter", "erp cloud adapter",
        "hcm adapter", "jde adapter",
        "sftp adapter", "email adapter",
        # Middleware / architecture
        "middleware", "oracle paas", "cloud integration",
        "orchestration", "api gateway", "oauth",
        "api management", "api platform",
        "oracle soa", "soa suite", "bpel",
        "oracle esb", "service bus",
        "oracle mft", "managed file transfer",
        # General
        "oci", "oracle cloud infrastructure",
        "api integration",
    ],
    "Oracle NetSuite Consultant": [
        # Core NetSuite
        "netsuite", "oracle netsuite", "netsuite erp",
        "netsuite crm", "netsuite financial",
        # Development
        "suitescript", "suitescript 2.0", "suitescript 1.0",
        "suitelet", "restlet", "user event script",
        "scheduled script", "client script",
        "map reduce", "mass update", "workflow action script",
        # Customization
        "netsuite workflow", "netsuite customization",
        "netsuite saved search", "saved search",
        "netsuite reports", "custom forms",
        "custom fields", "custom records",
        "custom segments",
        # Modules
        "suite commerce", "suitecommerce",
        "netsuite financials", "netsuite manufacturing",
        "netsuite inventory", "netsuite wms",
        "netsuite scm", "netsuite procurement",
        "netsuite fixed assets",
        # Implementation
        "netsuite implementation", "netsuite migration",
        "netsuite functional", "netsuite technical",
        "netsuite integration", "netsuite connector",
        "celigo", "boomi netsuite",
    ],
    "Oracle Fusion Developer": [
        # Core Fusion / Cloud
        "oracle fusion", "fusion applications",
        "oracle cloud", "oracle saas",
        "oracle erp cloud", "oracle cloud erp",
        "fusion financials", "oracle financials cloud",
        "oracle cloud scm", "oracle cloud hcm",
        "oracle cloud procurement",
        # ADF / UI
        "adf", "oracle adf", "adf bc",
        "adf faces", "jdeveloper",
        "fusion web client",
        # Middleware / BPM
        "fusion middleware", "soa suite",
        "oracle bpel", "bpm", "webcenter",
        "oracle mds",
        # BI / Analytics
        "oracle bi publisher", "bi publisher",
        "otbi", "faw", "oracle analytics cloud",
        "oracle analytics", "oracle transactional bi",
        "oracle reporting", "financial reporting studio",
        # Integration / extensibility
        "oracle vbcs", "visual builder",
        "oracle apex cloud", "faas",
        "oracle dcs", "oracle pbcs",
        "oracle epbcs", "oracle epm",
        # General
        "oracle cloud implementation",
        "oracle cloud consultant",
        "oracle cloud technical",
    ],
    "Oracle Apex Developer": [
        # APEX core
        "oracle apex", "apex",
        "application express", "oracle application express",
        "apex developer", "apex consultant",
        "apex 22", "apex 23", "apex 24", "apex 21",
        # APEX features
        "apex plugins", "apex components",
        "apex collections", "apex processes",
        "apex validations", "apex dynamic actions",
        "apex rest", "apex authentication",
        "apex authorization", "apex themes",
        "universal theme", "jet charts",
        "apex security", "apex interactive report",
        "apex interactive grid",
        # ORDS
        "ords", "oracle rest data services",
        "rest enabled sql",
        # Supporting tech
        "pl/sql", "javascript", "css", "html",
        "jquery", "html5", "ajax",
        "oracle cloud apex",
        "low code", "low-code",
        "rapid application development",
    ],
    "Oracle Apps Developer": [
        # Core EBS
        "oracle apps", "oracle applications",
        "oracle ebs", "oracle e-business suite",
        "e-business suite", "e business suite",
        "oracle r12", "oracle 12.2", "oracle 12.1",
        "oracle 11i", "oracle 11.5",
        # EBS modules
        "oracle financials", "oracle manufacturing",
        "oracle supply chain", "oracle scm",
        "oracle purchasing", "oracle procurement",
        "oracle ar", "oracle ap", "oracle gl",
        "oracle fa", "oracle om", "oracle inventory",
        "oracle hrms", "oracle payables",
        "oracle receivables", "oracle general ledger",
        # Technical tools
        "oracle forms", "oracle reports",
        "discoverer", "xml publisher",
        "bi publisher", "oracle workflow",
        "oracle alerts", "oracle adi",
        "fnd", "fnd_request",
        "custom.pll", "oa framework",
        "oaf", "personalization",
        "oracle concurrent program",
        "request group",
        # APIs / interfaces
        "oracle api", "oracle interface",
        "oracle open interface",
        "data conversion", "conversion",
        "oracle aol",
    ],
    "ETL Developer": [
        # Core ETL
        "etl", "extract transform load",
        "data warehouse", "data warehousing",
        "data integration", "data pipeline",
        "data migration",
        # Tools — Informatica
        "informatica", "informatica powercenter",
        "informatica iics", "informatica bdm",
        "informatica cloud", "informatica idmc",
        "informatica developer", "powercenter",
        # Tools — IBM / other
        "datastage", "ibm datastage",
        "datastage parallel", "datastage server",
        "talend", "talend open studio",
        "talend cloud",
        "pentaho", "kettle",
        # Tools — Microsoft
        "ssis", "sql server integration services",
        "azure data factory", "adf pipeline",
        "azure synapse",
        # Tools — AWS
        "aws glue", "aws etl",
        "aws data pipeline",
        # Tools — Oracle
        "oracle data integrator", "odi",
        "oracle goldengate", "goldengate",
        # Tools — Modern / cloud
        "dbt", "data build tool",
        "apache spark", "pyspark",
        "databricks",
        "snowflake", "redshift",
        "big query", "bigquery",
        "apache kafka", "kafka",
        "apache airflow", "airflow",
        "nifi", "apache nifi",
        # Modeling
        "data modeling", "dimensional modeling",
        "star schema", "snowflake schema",
        "data vault", "slowly changing dimension", "scd",
        "fact table", "dimension table",
        # Programming
        "python etl", "python",
        "shell scripting", "unix scripting",
        "sql", "pl/sql",
    ],
}

# Core title-level terms — at least one must appear in title OR description
# to confirm the job is actually related to that role.
# Expanded to match all the title variations staffing agencies use.
CORE_TITLE_TERMS: dict[str, list[str]] = {
    "Oracle PL/SQL Developer": [
        "pl/sql", "plsql", "pl sql",
        "oracle sql", "oracle database", "oracle db",
        "stored procedure", "oracle developer",
        "oracle programmer", "oracle backend",
        "oracle 19c", "oracle 12c", "oracle 11g",
        "oracle technical",
    ],
    "Oracle HCM Developer": [
        "hcm", "oracle hcm", "fusion hcm",
        "human capital management", "human capital",
        "oracle hr", "oracle hrms", "oracle payroll",
        "oracle workforce", "oracle benefits",
        "oracle talent", "oracle recruiting",
        "oracle cloud hr", "core hr",
        "fast formula", "hcm cloud","payroll",
        "Techno - functional","functional","Technical",
    ],
    "Oracle OIC Developer": [
        "oic", "oracle oic", "oracle integration cloud",
        "oracle integration", "integration cloud",
        "ics", "integration cloud service",
        "oracle middleware", "oracle soa",
        "oracle api", "oracle paas",
        "oracle ipaaas", "oracle ipaas",
        "rest adapter", "soap adapter",
        "oracle cloud integration",
    ],
    "Oracle NetSuite Consultant": [
        "netsuite", "oracle netsuite",
        "suite script", "suitescript",
        "suitelet", "restlet",
        "netsuite erp", "netsuite crm",
        "netsuite functional", "netsuite technical",
        "netsuite implementation", "netsuite workflow",
        "netsuite customization", "suite commerce",
    ],
    "Oracle Fusion Developer": [
        "oracle fusion", "fusion developer",
        "fusion financials", "oracle erp cloud",
        "oracle cloud erp", "oracle erp",
        "fusion applications", "oracle cloud developer",
        "oracle cloud scm", "oracle cloud hcm",
        "oracle adf", "oracle saas",
        "fusion middleware", "oracle bi publisher",
        "otbi", "oracle analytics",
        "fusion technical",
    ],
    "Oracle Apex Developer": [
        # NOTE: bare "apex" intentionally removed — Salesforce also has an "Apex"
        # language, causing false matches on "Salesforce Developer" jobs.
        # All retained terms are unambiguously Oracle APEX.
        "oracle apex",
        "application express", "oracle application express",
        "apex developer",           # "APEX Developer" title → Oracle context
        "apex consultant",
        "apex engineer", "apex programmer",
        "apex 21", "apex 22", "apex 23", "apex 24",
        "ords", "oracle rest data services",
        "oracle low code",
    ],
    "Oracle Apps Developer": [
        "oracle apps", "oracle ebs",
        "e-business suite", "e business suite",
        "oracle applications", "oracle r12",
        "oracle 12.2", "oracle 11i",
        "oracle forms", "oracle reports",
        "oracle financials", "oracle erp",
        "oracle purchasing", "oracle ar",
        "oracle ap", "oracle gl",
        "oracle supply chain", "oracle manufacturing",
        "oa framework", "oracle workflow",
        "xml publisher", "bi publisher",
    ],
    "ETL Developer": [
        # Core ETL term — must appear in title or description
        "etl", "extract transform load",
        # Informatica — primary tool in scope
        "informatica", "powercenter", "informatica iics", "informatica bdm",
        # Oracle ETL tools
        "odi", "oracle data integrator",
        # Other specific ETL tools
        "datastage", "ibm datastage",
        "talend",
        "pentaho",
        "ssis",
        # DW context that strongly implies ETL work
        "data warehouse", "data warehousing",
        "data integration",
        # NOTE — intentionally REMOVED to avoid pulling in wrong-domain jobs:
        #   "data engineer"    → too broad; matches AWS/Spark Data Engineers
        #   "data pipeline"    → too broad; matches generic data engineering
        #   "data migration"   → too broad; matches DB migration non-ETL projects
        #   "dbt"              → modern analytics tool, not Oracle/Informatica ETL
        #   "aws glue"         → cloud-only ETL; pure AWS Data Engineers leak in
        #   "azure data factory" → same issue; still scored in JOB_TYPES for ATS
    ],
}

# Flat set of ALL keywords across all job types — used for broad relevance check
ALL_JOB_KEYWORDS: set[str] = {
    kw for kws in JOB_TYPES.values() for kw in kws
}

# ── Contract/C2C filter ───────────────────────────────────────────────────────
# Jobs must contain at least one STRONG or MEDIUM term to pass.
# Jobs are REJECTED if they contain an EXCLUDE term (W2-only / no-C2C language).

# Strong C2C terms — always pass (these are unambiguously C2C/1099)
# These are the exact phrases staffing agencies use in job descriptions on
# Dice, LinkedIn, Indeed, and Monster to signal C2C eligibility.
CONTRACT_STRONG: list[str] = [
    # Corp-to-corp variants (all the ways recruiters type it)
    "c2c",
    "corp to corp",
    "corp-to-corp",
    "corp2corp",
    "c2c only",
    "c2c ok",
    "c2c acceptable",
    "c2c accepted",
    "corp to corp ok",
    "corp to corp only",
    "open to c2c",
    "open for c2c",
    "c2c possible",
    "c2c allowed",
    # 1099 / independent contractor
    "1099",
    "1099 contractor",
    "1099 only",
    "independent contractor",
    "self employed",
    "self-employed",
    # Corp-to-hire (c2h) — placement firm owns your w2 then client hires
    "c2h",
    "corp to hire",
    "corp-to-hire",
    # Subcontracting / third-party — staffing agency language
    "subcontract",
    "sub-contract",
    "sub contract",
    "subcontractor",
    "third party",
    "third-party",
    "3rd party",
    "3rd-party",
    "vendor corp",
    "implementation partner",
    # Visa / status open language that usually signals C2C shop
    "all employment types",
    "all visa types",
    "all status",
    "any employment type",
]

# Medium terms — pass only if no EXCLUDE term is present
CONTRACT_MEDIUM: list[str] = [
    "contract to hire",
    "contract-to-hire",
    "contract to perm",
    "contract-to-perm",
    "contract to permanent",
    "contract position",
    "contract role",
    "contract opportunity",
    "contract basis",
    "contract engagement",
    "contract only",
    "contract work",
    "contract job",
    "contract assignment",
    "contract consultant",
    "consulting role",
    "consulting opportunity",
    "consulting engagement",
    "consulting contract",
    "temp to hire",
    "temp-to-hire",
    "temp to perm",
    "temp-to-perm",
    "right to hire",
    "right-to-hire",
    "on a contract",
    "on contract",
    "w2 or c2c",        # ambiguous — pass but watch for EXCLUDE
    "w2/c2c",
    "freelance",
    "freelancer",
    "staff augmentation",
    "contract",          # standalone — LinkedIn/Dice/Indeed staffing posts often use this alone
    "contractor",        # "looking for a contractor"
]

# Exclusion terms — reject even if a medium/contract term matched
CONTRACT_EXCLUDE: list[str] = [
    # Explicit W2-only signals
    "w2 only",
    "w-2 only",
    "w2 contractors only",
    "w2 candidate",
    "w2 candidates only",
    "must be on w2",
    "w2 basis only",
    "w2 payroll only",
    "must work on w2",
    "on w2 only",
    # Explicit C2C rejections
    "no c2c",
    "no corp to corp",
    "no corp-to-corp",
    "not c2c",
    "not available for c2c",
    "c2c not available",
    "c2c not accepted",
    "c2c not allowed",
    "not accepting c2c",
    # Third-party / subcontract rejections
    "no third party",
    "no third-party",
    "no 3rd party",
    "no subcontracting",
    "no subcontract",
    "no sub-contract",
    "no sub contracting",
    "no vendor",
    "no vendors",
    "no agencies",
    "no staffing agencies",
    "no consulting firms",
    # Permanent / full-time only
    "full time only",
    "fulltime only",
    "full-time only",
    "permanent position",
    "permanent role",
    "permanent placement",
    "direct hire",
    "direct placement",
    "direct employee",
    "employees only",
    "must be employee",
    "must be a direct employee",
    "no contractors",
    "no contract",
    "no freelancers",
]

# Backward-compat alias used by old code paths
CONTRACT_KEYWORDS: list[str] = CONTRACT_STRONG + CONTRACT_MEDIUM

# ── Search queries per job type ───────────────────────────────────────────────
# Comprehensive title variations as staffing agencies post them on
# LinkedIn, Indeed, Dice, and Monster for C2C / 1099 / Corp-to-Corp roles.
SEARCH_QUERIES = {
    # ── Oracle PL/SQL Developer ───────────────────────────────────────────────
    # Staffing agencies also post this under: "SQL Developer", "Database Developer",
    # "Oracle Backend Developer", "Oracle DB Engineer", "Oracle Programmer"
    "Oracle PL/SQL Developer": [
        "Oracle PL/SQL Developer",
        "PL/SQL Developer",
        "Oracle Database Developer",
        "Oracle SQL Developer",
        "Oracle DB Developer",
        "Oracle Backend Developer",
        "SQL Developer Oracle",
        "Oracle Database Engineer",
        "Oracle Stored Procedure Developer",
        "Oracle Developer PL SQL",
        "Oracle Database Programmer",
        "Oracle DB Programmer",
        "PL SQL Programmer",
        "Oracle Application Developer",
        "Senior Oracle Developer",
        "Oracle Software Developer",
        "Oracle Technical Developer",
        "Oracle DBA Developer",
        "Database Developer Oracle",
        "Oracle 19c Developer",
    ],

    # ── Oracle HCM Developer ──────────────────────────────────────────────────
    # Also posted as: "HRMS Developer", "Payroll Developer", "HR Cloud Developer",
    # "Oracle Benefits Developer", "Workforce Management Developer"
    "Oracle HCM Developer": [
        "Oracle HCM Developer",
        "Oracle Fusion HCM Developer",
        "Oracle Cloud HCM Developer",
        "Oracle HCM Consultant",
        "Oracle HCM Functional Consultant",
        "Oracle HCM Technical Consultant",
        "Oracle HCM Techno Functional",
        "Oracle HCM Techno-Functional Consultant",
        "Oracle Human Capital Management Developer",
        "Oracle HR Developer",
        "Oracle HRMS Developer",
        "Oracle Payroll Developer",
        "Oracle Fusion Payroll Developer",
        "Oracle HCM Cloud Consultant",
        "Oracle Workforce Management Developer",
        "Oracle Benefits Developer",
        "Oracle Talent Management Developer",
        "Fusion HCM Developer",
        "Oracle Cloud HR Consultant",
        "Oracle HCM Implementation Consultant",
        "Oracle HCM Functional Lead", 
        "Technical oracle hcm consultant", 
        "Oracle Cloud Absence Management Techno-Functional Consultant",  
        "Oracle HCM Fusion Techno Functional Consultant",
        "Oracle HCM Functional Payroll",
    ],

    # ── Oracle OIC / Integration Cloud Developer ──────────────────────────────
    # Also posted as: "Oracle Middleware Developer", "Oracle Integration Specialist",
    # "SOA Developer", "Oracle iPaaS Developer", "Integration Engineer"
    "Oracle OIC Developer": [
        "Oracle OIC Developer",
        "Oracle Integration Cloud Developer",
        "OIC Developer",
        "Oracle Integration Developer",
        "Oracle Cloud Integration Developer",
        "Oracle OIC Consultant",
        "Oracle Integration Cloud Consultant",
        "Oracle Integration Cloud Service Developer",
        "Oracle ICS Developer",
        "Oracle Middleware Developer",
        "Oracle SOA Developer",
        "Oracle SOA Suite Developer",
        "Oracle Integration Specialist",
        "Oracle iPaaS Developer",
        "Oracle API Developer",
        "Oracle API Integration Developer",
        "Oracle OIC Integration Developer",
        "Oracle Cloud Middleware Developer",
        "Integration Developer Oracle",
        "Oracle Fusion Integration Developer",
    ],

    # ── Oracle NetSuite Consultant ────────────────────────────────────────────
    # Also posted as: "NetSuite ERP Consultant", "SuiteScript Developer",
    # "NetSuite Administrator", "NetSuite Analyst", "NetSuite Functional Analyst"
    "Oracle NetSuite Consultant": [
        "NetSuite Consultant",
        "Oracle NetSuite Consultant",
        "NetSuite Developer",
        "Oracle NetSuite Developer",
        "NetSuite ERP Consultant",
        "NetSuite Functional Consultant",
        "NetSuite Technical Consultant",
        "NetSuite Techno Functional Consultant",
        "NetSuite Implementation Consultant",
        "SuiteScript Developer",
        "NetSuite Administrator",
        "NetSuite Analyst",
        "NetSuite Functional Analyst",
        "NetSuite ERP Developer",
        "NetSuite Solutions Consultant",
        "NetSuite CRM Consultant",
        "NetSuite Financial Consultant",
        "NetSuite WMS Consultant",
        "NetSuite Integration Developer",
        "Oracle NetSuite Functional Analyst",
    ],

    # ── Oracle Fusion Developer ───────────────────────────────────────────────
    # Also posted as: "Oracle ERP Developer", "Oracle Cloud ERP Developer",
    # "Oracle Financials Developer", "Oracle SCM Developer", "Oracle ADF Developer"
    "Oracle Fusion Developer": [
        "Oracle Fusion Developer",
        "Oracle ERP Cloud Developer",
        "Oracle Cloud ERP Developer",
        "Oracle Fusion Technical Developer",
        "Oracle Fusion Consultant",
        "Oracle Fusion Technical Consultant",
        "Oracle Fusion Techno Functional",
        "Oracle Fusion Techno-Functional Consultant",
        "Oracle Cloud Developer",
        "Oracle Fusion Financials Developer",
        "Oracle Financials Developer",
        "Oracle Cloud Financials Developer",
        "Oracle Fusion SCM Developer",
        "Oracle Cloud SCM Developer",
        "Oracle ADF Developer",
        "Oracle Fusion Applications Developer",
        "Oracle BICC Developer",
        "Oracle OTBI Developer",
        "Oracle BI Publisher Developer",
        "Oracle Cloud Applications Developer",
    ],

    # ── Oracle APEX Developer ─────────────────────────────────────────────────
    # Also posted as: "APEX Engineer", "Oracle Low Code Developer",
    # "Oracle Web Developer", "ORDS Developer", "Oracle Application Developer"
    "Oracle Apex Developer": [
        "Oracle APEX Developer",
        "Oracle Application Express Developer",
        "APEX Developer",
        "Oracle APEX Consultant",
        "Oracle APEX Engineer",
        "Oracle APEX Programmer",
        "Oracle Application Express Consultant",
        "Oracle Low Code Developer",
        "Oracle APEX Technical Developer",
        "APEX Web Developer",
        "Oracle ORDS Developer",
        "Oracle REST Data Services Developer",
        "Oracle APEX Full Stack Developer",
        "Oracle Database Application Developer",
        "Oracle APEX UI Developer",
        "Oracle APEX PL/SQL Developer",
        "Oracle APEX Cloud Developer",
        "Application Express Developer",
        "Oracle Web Application Developer",
        "Oracle APEX Senior Developer",
    ],

    # ── Oracle Apps / EBS Developer ───────────────────────────────────────────
    # Also posted as: "Oracle Financials Consultant", "Oracle R12 Developer",
    # "Oracle ERP Developer", "Oracle Technical Analyst", "Oracle Forms Developer"
    "Oracle Apps Developer": [
        "Oracle EBS Developer",
        "Oracle Apps Developer",
        "Oracle E-Business Suite Developer",
        "Oracle Applications Developer",
        "Oracle R12 Developer",
        "Oracle EBS Technical Developer",
        "Oracle EBS Functional Consultant",
        "Oracle EBS Techno Functional",
        "Oracle EBS Techno-Functional Consultant",
        "Oracle Financials Consultant",
        "Oracle EBS Consultant",
        "Oracle Forms Developer",
        "Oracle Reports Developer",
        "Oracle EBS Analyst",
        "Oracle Technical Consultant",
        "Oracle ERP Developer",
        "Oracle 12.2 Developer",
        "Oracle Applications Consultant",
        "Oracle Procurement Developer",
        "Oracle Supply Chain Developer",
    ],

    # ── ETL Developer ─────────────────────────────────────────────────────────
    # Also posted as: "Data Integration Developer", "Data Pipeline Engineer",
    # "Data Warehouse Developer", "Informatica ETL Developer", "ODI Developer"
    "ETL Developer": [
        "ETL Developer",
        "ETL Engineer",
        "ETL Consultant",
        "Oracle ODI Developer",
        "Oracle Data Integrator Developer",
        "Informatica Developer",
        "Informatica PowerCenter Developer",
        "Informatica ETL Developer",
        "DataStage Developer",
        "IBM DataStage Developer",
        "Data Warehouse Developer",
        "Data Warehouse Engineer",
        "Data Integration Developer",
        "Data Integration Engineer",
        "Data Pipeline Developer",
        "Data Pipeline Engineer",
        "SSIS Developer",
        "Talend Developer",
        "Azure Data Factory Developer",
        "AWS Glue Developer",
        "dbt Developer",
        "Data Engineer ETL",
        "ETL Data Engineer",
        "Informatica BDM Developer",
        "Informatica IICS Developer",
    ],
}

# ── Pipeline settings ─────────────────────────────────────────────────────────
PORTAL_DAYS_LOOKBACK = 2   # Portal pipeline: LinkedIn/Indeed/Dice/Monster — past 2 days
VENDOR_DAYS_LOOKBACK = 3   # Vendor pipeline: vendor list LinkedIn search — past 3 days
DAYS_LOOKBACK        = 3   # backward-compat alias
SCORE_LOW            = 40  # minimum % to include in report
SCORE_HIGH           = 90  # % threshold for "ready to send" tier
MAX_JOBS_PER_QUERY   = 25  # 25 per query (was 50) — saves ~50% Apify tokens

# ── Apify actor IDs ───────────────────────────────────────────────────────────
ACTOR_LINKEDIN = "curious_coder/linkedin-jobs-scraper"
ACTOR_INDEED   = "valig/indeed-jobs-scraper"
ACTOR_DICE     = "shahidirfan/Dice-Job-Scraper"
ACTOR_MONSTER  = "memo23/monster-scraper"

# ── Credentials from env ──────────────────────────────────────────────────────
APIFY_TOKENS = [t for t in [
    os.getenv("APIFY_TOKEN1"),
    os.getenv("APIFY_TOKEN2"),
    os.getenv("APIFY_TOKEN3"),
] if t]

GMAIL_USER         = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
NOTIFY_EMAIL       = os.getenv("NOTIFY_EMAIL", GMAIL_USER)

GDRIVE_FOLDER_ID  = os.getenv("GDRIVE_FOLDER_ID", "")
GDRIVE_CREDS_FILE = os.getenv("GDRIVE_CREDENTIALS_FILE", "credentials.json")

GSHEET_SPREADSHEET_ID = os.getenv("GSHEET_SPREADSHEET_ID", "")
GSHEET_CREDS_FILE     = os.getenv("GSHEET_CREDENTIALS_FILE", "credentials.json")

# Monster search URL template
MONSTER_SEARCH_TMPL = "https://www.monster.com/jobs/search?q={query}&where=USA&age=3"
