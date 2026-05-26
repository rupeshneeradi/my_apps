"""
Role Domain Classifier — v2.0
──────────────────────────────
Classifies a resume or JD into a primary work domain based on weighted
keyword signals and title patterns.

v1: 6 domains (devops_cloud, oracle_erp, data_engineering,
               software_dev, cybersecurity, database_admin)

v2: 15 domains — adds:
    qa_testing, ai_ml, network_infra, salesforce, sap,
    workday, servicenow, mobile_dev, business_analysis, non_it

non_it: manufacturing, automotive, telecom-hardware, biomedical, etc.
        Jobs classified as non_it should be skipped in the pipeline.

Also computes a role_fit_score (0–100) between a resume domain and a
JD domain, and a combined_score that weights role fit + keyword ATS.

No AI, no external calls — 100 % local and deterministic.
"""
import re
from functools import lru_cache

# ── Domain definitions ─────────────────────────────────────────────────────────
# Each domain has:
#   primary   — high-specificity terms (weight 3): almost never appear outside this domain
#   secondary — supporting terms  (weight 1): common but reinforce the domain
#   titles    — role title signals (weight 4): strongest signal

DOMAINS: dict[str, dict] = {
    "devops_cloud": {
        "label": "DevOps / Cloud",
        "primary": [
            "kubernetes","k8s","docker","terraform","ansible","helm","argocd","argo cd",
            "flux","tekton","jenkins","github actions","gitlab ci","circleci","teamcity",
            "infrastructure as code","iac","gitops","devsecops","platform engineering",
            "prometheus","grafana","alertmanager","datadog","newrelic","elk stack",
            "cloudformation","pulumi","bicep","kustomize","packer","vagrant",
            "service mesh","istio","linkerd","envoy","vault","consul",
            "ci/cd","cicd","continuous integration","continuous delivery",
        ],
        "secondary": [
            "aws","azure","gcp","google cloud","amazon web services",
            "linux","bash","shell scripting","python","go","golang",
            "monitoring","logging","tracing","observability","alerting",
            "container","containerization","microservices","deployment","pipeline",
            "incident management","on-call","runbook","slo","sli","sre",
            "s3","ec2","lambda","eks","aks","gke","fargate","ecs",
        ],
        "titles": [
            "devops engineer","cloud engineer","site reliability engineer","sre",
            "platform engineer","infrastructure engineer","mlops engineer",
            "devsecops engineer","build engineer","release engineer",
            "cloud architect","solutions architect","cloud consultant",
            "cloud operations","cloud infrastructure","cloud native",
        ],
    },

    "oracle_erp": {
        "label": "Oracle / ERP",
        "primary": [
            "oracle fusion","oracle hcm","oracle scm","oracle financials","oracle erp",
            "pl/sql","plsql","oracle apex","apex","oracle oic","oic","oracle integration",
            "obiee","obia","odi","oracle data integrator","bip","bi publisher",
            "otm","oracle transportation","wms","oracle wms","oracle cloud",
            "peoplesoft","netsuite","jd edwards","oracle e-business suite","ebs",
            "oracle r12","11i","12c","19c","oracle 11g","oracle 12c",
            "oracle forms","oracle reports","oracle workflow","fnd","hrms",
            "payroll","core hr","talent management","absence management",
            "procurement","order management","accounts payable","accounts receivable",
            "general ledger","fixed assets","oracle soa","soa suite",
        ],
        "secondary": [
            "erp","saas","hcm","fast formula","infolets","hdl","hsdl","rest api oracle",
            "sql","stored procedure","package","trigger","function","view","materialized",
            "integration","middleware","web services","wsdl","soap","xml","xsl",
            "application developer","functional consultant","technical consultant",
            "configuration","setup","flexfields","dff","kff","value sets",
        ],
        "titles": [
            "oracle developer","oracle consultant","oracle hcm","oracle fusion",
            "pl/sql developer","oracle dba","oracle apex developer","oracle architect",
            "erp consultant","erp developer","oracle analyst","oracle administrator",
            "peoplesoft developer","netsuite developer","jde developer",
        ],
    },

    "data_engineering": {
        "label": "Data Engineering / Analytics",
        "primary": [
            "apache spark","pyspark","hadoop","hdfs","hive","apache kafka","kafka",
            "apache airflow","airflow","dagster","prefect","luigi",
            "databricks","snowflake","dbt","data build tool",
            "bigquery","redshift","azure synapse","synapse analytics",
            "data warehouse","data lake","data lakehouse","delta lake","iceberg",
            "etl","elt","data pipeline","data ingestion","data transformation",
            "looker","tableau","power bi","qlik","metabase",
            "spark streaming","flink","kinesis","pub/sub","event streaming",
        ],
        "secondary": [
            "python","sql","scala","java","pandas","numpy","dask",
            "schema design","data modeling","star schema","kimball","inmon",
            "orchestration","workflow","batch processing","real-time","streaming",
            "data quality","data governance","data catalog","lineage",
            "mysql","postgresql","mongodb","cassandra","hbase","elasticsearch",
        ],
        "titles": [
            "data engineer","data architect","etl developer","etl engineer",
            "analytics engineer","bi developer","bi engineer","data platform",
            "data infrastructure","database engineer","pipeline engineer",
        ],
    },

    "software_dev": {
        "label": "Software Development",
        "primary": [
            "spring boot","spring framework","hibernate","jpa","jakarta ee","java ee",
            "react","angular","vue","next.js","nuxt","svelte",
            "node.js","express","nestjs","fastapi","django","flask",
            "graphql","rest api","grpc","microservices","event-driven",
            "unit testing","jest","junit","pytest","tdd","bdd",
            "oauth","jwt","saml","authentication","authorization",
            "solid principles","design patterns","clean architecture","ddd",
        ],
        "secondary": [
            "java","python","javascript","typescript","c#","dotnet","go","kotlin","swift",
            "backend","frontend","full stack","web application","mobile",
            "api","database","postgresql","mysql","mongodb","redis","cache",
            "agile","scrum","kanban","jira","git","code review","pr",
            "ci/cd","deployment","docker","aws","azure",
        ],
        "titles": [
            "software engineer","backend engineer","frontend engineer","full stack engineer",
            "application developer","web developer","mobile developer",
            "java developer","python developer","dotnet developer","react developer",
            "software developer","swe","application engineer",
        ],
    },

    "cybersecurity": {
        "label": "Cybersecurity",
        "primary": [
            "penetration testing","pentest","vulnerability assessment","red team","blue team",
            "siem","splunk siem","ibm qradar","elastic siem",
            "sast","dast","sca","snyk","sonarqube","veracode","checkmarx",
            "zero trust","ztna","owasp","cve","cvss","exploit",
            "incident response","digital forensics","threat hunting","threat intelligence",
            "malware analysis","reverse engineering","ctf",
            "pci dss","hipaa","soc 2","iso 27001","nist","fedramp","cmmc",
            "iam","pam","privileged access","mfa","saml sso",
        ],
        "secondary": [
            "security","appsec","devsecops","firewall","ids","ips","endpoint",
            "encryption","pki","certificate","vpn","network security",
            "cloud security","container security","trivy","clair","aqua",
            "compliance","audit","risk management","policy","governance",
            "aws security","azure security","gcp security",
        ],
        "titles": [
            "security engineer","cybersecurity engineer","appsec engineer","soc analyst",
            "penetration tester","security analyst","information security",
            "devsecops engineer","cloud security engineer","security architect",
        ],
    },

    "database_admin": {
        "label": "Database / DBA",
        "primary": [
            "dba","database administrator","oracle dba","sql server dba","mysql dba",
            "backup and recovery","rman","dataguard","data guard","rac","oracle rac",
            "replication","mirroring","log shipping","always on","availability group",
            "performance tuning","query optimization","execution plan","index tuning",
            "tablespace","redo log","archive log","awr","ash","statspack",
            "patching","upgrade","migration dba","database migration",
        ],
        "secondary": [
            "oracle","sql server","mysql","postgresql","mongodb","cassandra",
            "sql","pl/sql","t-sql","stored procedure","trigger","view","index",
            "database design","schema","normalization","partitioning","sharding",
            "high availability","disaster recovery","failover","clustering",
        ],
        "titles": [
            "database administrator","oracle dba","sql dba","database engineer",
            "database developer","sql developer","database architect",
        ],
    },

    # ── v2 new domains ──────────────────────────────────────────────────────────

    "qa_testing": {
        "label": "QA / Test Automation",
        "primary": [
            "selenium","webdriver","cypress","playwright","puppeteer",
            "appium","xcuitest","espresso",
            "testng","junit","pytest","jest","mocha","jasmine",
            "bdd","tdd","cucumber","gherkin","specflow",
            "performance testing","load testing","jmeter","gatling","k6",
            "api testing","postman","rest assured","soapui","karate",
            "test automation","automated testing","test framework",
            "test plan","test case","test suite","test script",
            "regression testing","smoke testing","integration testing","e2e testing",
            "manual testing","exploratory testing","user acceptance testing","uat",
            "bug tracking","defect management","jira","testrail","zephyr","qtest",
            "code coverage","test coverage","mutation testing","sonarqube",
        ],
        "secondary": [
            "qa","quality assurance","quality engineer","sdet","software tester",
            "python","java","javascript","c#","ruby",
            "ci/cd","jenkins","github actions","docker","agile","scrum",
            "mobile testing","cross-browser testing","accessibility testing",
        ],
        "titles": [
            "qa engineer","sdet","test automation engineer","software test engineer",
            "quality assurance engineer","qa analyst","test lead",
            "automation engineer","test architect","qa automation engineer",
        ],
    },

    "ai_ml": {
        "label": "AI / ML / Data Science",
        "primary": [
            "machine learning","deep learning","neural network","llm","large language model",
            "generative ai","gen ai","chatgpt","openai","anthropic","langchain","langgraph",
            "rag","retrieval augmented generation","vector database","embedding",
            "pytorch","tensorflow","keras","scikit-learn","hugging face","transformers",
            "nlp","natural language processing","computer vision","object detection",
            "convolutional neural network","cnn","rnn","lstm","transformer","bert","gpt",
            "reinforcement learning","federated learning","transfer learning",
            "model training","model inference","hyperparameter tuning","fine-tuning",
            "xgboost","lightgbm","catboost","random forest","gradient boosting",
            "feature engineering","feature selection","model evaluation","cross validation",
            "recommendation system","anomaly detection","time series forecasting",
            "mlflow","kubeflow","sagemaker","vertex ai","azure ml","databricks ml",
            "data science","statistical modeling","a/b testing","hypothesis testing",
        ],
        "secondary": [
            "python","r","jupyter","pandas","numpy","scipy","matplotlib","seaborn",
            "sql","spark","aws","gcp","azure",
            "data analyst","research scientist","applied scientist",
            "statistics","probability","linear algebra","calculus",
        ],
        "titles": [
            "data scientist","machine learning engineer","ml engineer","ai engineer",
            "research scientist","applied scientist","nlp engineer","cv engineer",
            "llm engineer","ai researcher","deep learning engineer",
            "data analyst","business intelligence","bi analyst",
        ],
    },

    "network_infra": {
        "label": "Network / Systems Infrastructure",
        "primary": [
            "cisco","juniper","aruba","palo alto networks","fortinet","checkpoint",
            "bgp","ospf","eigrp","mpls","sdwan","sd-wan","vxlan","evpn",
            "vlan","spanning tree","stp","rstp","qos","nat","acl","routing","switching",
            "firewall","ids","ips","dmz","network security",
            "active directory","ldap","group policy","windows server","exchange server",
            "vmware vcenter","vsphere","esxi","hyper-v","virtual machines",
            "storage area network","san","nas","nfs","cifs","iscsi",
            "tcp/ip","dns","dhcp","radius","tacacs",
            "network monitoring","nagios","solarwinds","prtg",
            "wireshark","packet capture","network troubleshooting",
            "ipam","network automation","noc","help desk tier 2","tier 3",
        ],
        "secondary": [
            "linux","windows","aws networking","azure networking","vpc","vpn",
            "network engineer","systems administrator","it infrastructure",
            "cabling","fiber","wireless","wi-fi","802.11","lte","5g",
        ],
        "titles": [
            "network engineer","network administrator","systems administrator",
            "infrastructure engineer","it infrastructure engineer","sysadmin",
            "network architect","cloud network engineer","network security engineer",
        ],
    },

    "salesforce": {
        "label": "Salesforce",
        "primary": [
            "salesforce","salesforce crm","salesforce sales cloud","salesforce service cloud",
            "salesforce marketing cloud","salesforce pardot","salesforce cpq",
            "salesforce experience cloud","salesforce community cloud",
            "apex salesforce","apex code","visualforce","lightning web component","lwc",
            "salesforce flow","process builder","workflow rules","validation rule",
            "soql","sosl","salesforce api","salesforce rest api","salesforce soap api",
            "salesforce integration","mulesoft","salesforce connect",
            "salesforce admin","salesforce developer","salesforce architect",
            "trailhead","salesforce certification","salesforce certified",
            "salesforce platform","salesforce shield","salesforce einstein",
            "salesforce analytics","crm analytics","tableau crm",
            "salesforce data loader","data migration salesforce",
            "permission sets","profiles","roles","salesforce security",
        ],
        "secondary": [
            "crm","customer relationship management","javascript","typescript",
            "rest api","agile","scrum","devops",
        ],
        "titles": [
            "salesforce developer","salesforce administrator","salesforce admin",
            "salesforce architect","salesforce consultant","salesforce engineer",
            "salesforce analyst","crm developer","salesforce solution architect",
        ],
    },

    "sap": {
        "label": "SAP",
        "primary": [
            "sap","sap s/4hana","s/4hana","sap ecc","sap r/3",
            "sap abap","abap","bapi","badi","user exit","enhancement point",
            "sap hana","sap hana db","column store","sap fiori","ui5","sapui5",
            "sap btp","business technology platform","sap cloud platform",
            "sap integration suite","sap api management","sap bw","bw/4hana",
            "sap pp","sap mm","sap sd","sap fi","sap co","sap pm","sap qm",
            "sap hr","sap hcm","sap successfactors","successfactors",
            "sap basis","sap security","sap transport","sap landscape",
            "sap ariba","sap concur","sap fieldglass","sap commerce cloud",
            "sap implementation","sap migration","sap upgrade",
            "sap functional consultant","sap technical consultant",
        ],
        "secondary": [
            "erp","java","javascript","sql","agile","fiori",
            "odata","rest api","idoc",
        ],
        "titles": [
            "sap developer","sap consultant","sap abap developer","sap analyst",
            "sap architect","sap functional consultant","sap technical consultant",
            "sap administrator","sap basis administrator","sap hana developer",
        ],
    },

    "workday": {
        "label": "Workday",
        "primary": [
            "workday","workday hcm","workday financial management","workday financials",
            "workday payroll","workday benefits","workday talent","workday recruiting",
            "workday prism","workday extend","workday integration",
            "workday studio","eis","enterprise interface builder","eib",
            "workday business process","calculated field","condition rule",
            "workday report","workday custom report","workday raas",
            "workday security","workday configuration","workday tenant",
            "workday implementation","workday deployment","workday testing",
            "workday functional consultant","workday technical consultant",
        ],
        "secondary": [
            "hcm","hrms","xml","xslt","rest api","agile",
        ],
        "titles": [
            "workday developer","workday consultant","workday analyst",
            "workday architect","workday administrator","workday functional analyst",
            "workday integration developer","workday hcm consultant",
        ],
    },

    "servicenow": {
        "label": "ServiceNow",
        "primary": [
            "servicenow","snow","service now","itsm","itom","itbm","itsm platform",
            "service catalog","change management","incident management itil",
            "problem management","cmdb","configuration management database",
            "servicenow scripting","glide record","glide ajax","business rule servicenow",
            "servicenow flow designer","workflow servicenow","ui policy","client script",
            "servicenow integration","rest integration servicenow","soap servicenow",
            "servicenow discovery","service mapping","event management",
            "servicenow hrsd","hr service delivery","employee center",
            "servicenow csp","customer service management","servicenow now platform",
            "servicenow admin","servicenow developer","servicenow architect",
        ],
        "secondary": [
            "itil","javascript","xml","rest api","agile",
            "itsm consultant","it service management",
        ],
        "titles": [
            "servicenow developer","servicenow administrator","servicenow admin",
            "servicenow architect","servicenow consultant","servicenow engineer",
            "servicenow analyst","itsm developer","servicenow implementation consultant",
        ],
    },

    "mobile_dev": {
        "label": "Mobile Development",
        "primary": [
            "ios development","swift","swiftui","objective-c","xcode","cocoapods",
            "android development","kotlin","android studio","jetpack compose",
            "react native","flutter","dart","ionic","xamarin","maui",
            "mobile app development","cross-platform mobile","hybrid mobile",
            "app store connect","google play console","push notifications",
            "core data","room database","mobile architecture","mvvm mobile",
            "mobile ui","mobile ux","responsive design","accessibility ios",
            "fastlane","mobile ci/cd","firebase","crashlytics","testflight",
        ],
        "secondary": [
            "javascript","typescript","java","python","rest api",
            "backend","api","aws amplify","firebase",
            "agile","scrum","git",
        ],
        "titles": [
            "ios developer","android developer","mobile developer","mobile engineer",
            "react native developer","flutter developer","cross-platform developer",
            "ios engineer","android engineer","mobile app developer",
        ],
    },

    "business_analysis": {
        "label": "Business Analysis / Product",
        "primary": [
            "business analyst","business analysis","requirements gathering",
            "functional requirements","business requirements document","brd",
            "use case","user story","acceptance criteria","stakeholder management",
            "gap analysis","process mapping","as-is to-be","current state future state",
            "business process improvement","bpmn","visio","lucidchart",
            "product owner","product backlog","backlog refinement","sprint planning",
            "scrum master","agile coach","release planning","roadmap",
            "jira","confluence","ado","azure devops boards",
            "data analysis","power bi","tableau","excel advanced","pivot table",
            "uat","user acceptance testing","test management","test scenarios",
            "change management","training documentation","sop","runbook",
            "sql reporting","sql queries","business intelligence",
        ],
        "secondary": [
            "agile","scrum","kanban","waterfall","project management",
            "communication","stakeholder","documentation","analysis",
        ],
        "titles": [
            "business analyst","product owner","scrum master","product manager",
            "systems analyst","it analyst","functional analyst","ba",
            "agile coach","requirements analyst","process analyst",
        ],
    },

    "non_it": {
        "label": "Non-IT / Other Industry",
        "primary": [
            # Manufacturing / industrial
            "plc programming","plc ladder logic","scada","hmi","dcs",
            "cnc machining","cam software","solidworks","autocad",
            "structural analysis","finite element","fea","cfd",
            "hvac design","plumbing design","electrical panel",
            "field service","on-site maintenance","preventive maintenance",
            # Biomedical / life sciences
            "fda 21 cfr","gmp","glp","clinical trials","irb","clinical data management",
            "drug discovery","genomics","proteomics","bioinformatics pipeline",
            # Construction / energy
            "autocad civil","revit","bim","construction management",
            "project estimating","cost estimating","subcontractor",
            "power plant","transmission line","substation","smart grid",
            # Telecom hardware
            "fiber splicing","fiber optic installation","osp","itu-t",
            "rf planning","cell site","spectrum management",
        ],
        "secondary": [
            "manufacturing","automotive","aerospace","defense","energy",
            "biomedical","pharmaceutical","construction","utilities",
        ],
        "titles": [
            "controls engineer","process engineer","manufacturing engineer",
            "mechanical engineer","electrical engineer","chemical engineer",
            "civil engineer","structural engineer","hvac engineer",
            "fiber network engineer","rf engineer","telecom engineer",
            "biomedical engineer","clinical engineer","field service engineer",
        ],
    },
}

# ── How well does a resume domain fit a JD domain? ────────────────────────────
# (resume_domain, jd_domain) → role_fit_score 0-100
# Symmetric unless noted.
_COMPAT: dict[tuple, int] = {
    # ── Perfect matches (self → self) ──────────────────────────────────────────
    ("devops_cloud",      "devops_cloud"):      100,
    ("oracle_erp",        "oracle_erp"):        100,
    ("data_engineering",  "data_engineering"):  100,
    ("software_dev",      "software_dev"):      100,
    ("cybersecurity",     "cybersecurity"):     100,
    ("database_admin",    "database_admin"):    100,
    ("qa_testing",        "qa_testing"):        100,
    ("ai_ml",             "ai_ml"):             100,
    ("network_infra",     "network_infra"):     100,
    ("salesforce",        "salesforce"):        100,
    ("sap",               "sap"):               100,
    ("workday",           "workday"):           100,
    ("servicenow",        "servicenow"):        100,
    ("mobile_dev",        "mobile_dev"):        100,
    ("business_analysis", "business_analysis"): 100,

    # ── v1 original adjacent pairs ─────────────────────────────────────────────
    ("devops_cloud",     "cybersecurity"):      65,
    ("cybersecurity",    "devops_cloud"):       65,
    ("devops_cloud",     "software_dev"):       55,
    ("software_dev",     "devops_cloud"):       55,
    ("devops_cloud",     "data_engineering"):   45,
    ("data_engineering", "devops_cloud"):       45,
    ("software_dev",     "data_engineering"):   60,
    ("data_engineering", "software_dev"):       60,
    ("software_dev",     "cybersecurity"):      55,
    ("cybersecurity",    "software_dev"):       55,
    ("database_admin",   "data_engineering"):   50,
    ("data_engineering", "database_admin"):     50,
    ("database_admin",   "oracle_erp"):         55,
    ("oracle_erp",       "database_admin"):     55,
    ("database_admin",   "software_dev"):       40,
    ("software_dev",     "database_admin"):     40,

    # ── v1 distant pairs ───────────────────────────────────────────────────────
    ("oracle_erp",       "devops_cloud"):       18,
    ("devops_cloud",     "oracle_erp"):         18,
    ("oracle_erp",       "data_engineering"):   35,
    ("data_engineering", "oracle_erp"):         35,
    ("oracle_erp",       "software_dev"):       40,
    ("software_dev",     "oracle_erp"):         40,
    ("oracle_erp",       "cybersecurity"):      12,
    ("cybersecurity",    "oracle_erp"):         12,
    ("database_admin",   "devops_cloud"):       28,
    ("devops_cloud",     "database_admin"):     28,
    ("database_admin",   "cybersecurity"):      30,
    ("cybersecurity",    "database_admin"):     30,
    ("data_engineering", "cybersecurity"):      30,
    ("cybersecurity",    "data_engineering"):   30,

    # ── v2 new domain adjacency ────────────────────────────────────────────────

    # qa_testing adjacency
    ("qa_testing",       "software_dev"):       65,   # QA engineer → SW dev role: transferable
    ("software_dev",     "qa_testing"):         60,
    ("qa_testing",       "devops_cloud"):       50,   # SDET with CI/CD knowledge
    ("devops_cloud",     "qa_testing"):         45,
    ("qa_testing",       "ai_ml"):              40,   # ML model testing / eval
    ("ai_ml",            "qa_testing"):         35,
    ("qa_testing",       "data_engineering"):   35,
    ("data_engineering", "qa_testing"):         30,

    # ai_ml adjacency
    ("ai_ml",            "data_engineering"):   70,   # DS often does DE work
    ("data_engineering", "ai_ml"):              60,
    ("ai_ml",            "software_dev"):       60,   # MLE is a SWE subspecialty
    ("software_dev",     "ai_ml"):              50,
    ("ai_ml",            "devops_cloud"):       45,   # MLOps overlaps with DevOps
    ("devops_cloud",     "ai_ml"):              40,
    ("ai_ml",            "database_admin"):     35,
    ("database_admin",   "ai_ml"):              30,

    # network_infra adjacency
    ("network_infra",    "devops_cloud"):       45,   # Infra engineers moving to cloud
    ("devops_cloud",     "network_infra"):      40,
    ("network_infra",    "cybersecurity"):      50,   # Network security overlap
    ("cybersecurity",    "network_infra"):      45,
    ("network_infra",    "database_admin"):     30,
    ("database_admin",   "network_infra"):      30,

    # salesforce adjacency (Salesforce is its own ecosystem)
    ("salesforce",       "software_dev"):       45,   # Apex/JS → general SWE
    ("software_dev",     "salesforce"):         35,
    ("salesforce",       "oracle_erp"):         30,   # Both are CRM/ERP platforms
    ("oracle_erp",       "salesforce"):         30,
    ("salesforce",       "business_analysis"):  55,   # SF BA/Admin → BA
    ("business_analysis","salesforce"):         50,

    # sap adjacency
    ("sap",              "oracle_erp"):         35,   # Both ERP, different platforms
    ("oracle_erp",       "sap"):                35,
    ("sap",              "business_analysis"):  50,
    ("business_analysis","sap"):                45,
    ("sap",              "software_dev"):       35,
    ("software_dev",     "sap"):                30,

    # workday adjacency
    ("workday",          "oracle_erp"):         40,   # Both HCM/Finance cloud
    ("oracle_erp",       "workday"):            40,
    ("workday",          "sap"):                35,
    ("sap",              "workday"):            35,
    ("workday",          "business_analysis"):  55,
    ("business_analysis","workday"):            50,

    # servicenow adjacency
    ("servicenow",       "software_dev"):       50,   # SNow dev uses JS/APIs
    ("software_dev",     "servicenow"):         40,
    ("servicenow",       "devops_cloud"):       45,   # ITOM / DevOps overlap
    ("devops_cloud",     "servicenow"):         40,
    ("servicenow",       "business_analysis"):  55,
    ("business_analysis","servicenow"):         50,
    ("servicenow",       "network_infra"):      40,   # ITSM / CMDB
    ("network_infra",    "servicenow"):         40,

    # mobile_dev adjacency
    ("mobile_dev",       "software_dev"):       70,   # Mobile is a SW specialty
    ("software_dev",     "mobile_dev"):         60,
    ("mobile_dev",       "devops_cloud"):       35,
    ("devops_cloud",     "mobile_dev"):         30,
    ("mobile_dev",       "qa_testing"):         50,   # Mobile QA overlap
    ("qa_testing",       "mobile_dev"):         50,

    # business_analysis adjacency
    ("business_analysis","oracle_erp"):         45,   # Oracle functional BA
    ("oracle_erp",       "business_analysis"):  45,
    ("business_analysis","data_engineering"):   40,
    ("data_engineering", "business_analysis"):  35,
    ("business_analysis","software_dev"):       40,
    ("software_dev",     "business_analysis"):  35,

    # non_it — very low fit with everything
    ("non_it",           "devops_cloud"):        5,
    ("non_it",           "software_dev"):        5,
    ("non_it",           "oracle_erp"):          5,
    ("non_it",           "data_engineering"):    5,
    ("non_it",           "cybersecurity"):       5,
    ("non_it",           "database_admin"):      5,
    ("non_it",           "qa_testing"):          5,
    ("non_it",           "ai_ml"):               5,
    ("non_it",           "network_infra"):       8,  # slight overlap (cabling / telecom)
    ("non_it",           "salesforce"):          3,
    ("non_it",           "sap"):                 5,
    ("non_it",           "workday"):             3,
    ("non_it",           "servicenow"):          3,
    ("non_it",           "mobile_dev"):          3,
    ("non_it",           "business_analysis"):   8,
}

_DEFAULT_COMPAT = 20   # fallback for any pair not listed (slightly lower than v1's 25)


# ── Classifier ─────────────────────────────────────────────────────────────────

def _wb(kw: str) -> re.Pattern:
    return re.compile(r'\b' + re.escape(kw) + r'\b', re.I)


def classify(text: str) -> tuple[str, int, dict[str, int]]:
    """
    Classify text into a domain.

    Returns (domain_name, confidence_0_to_100, all_domain_scores_dict).

    confidence is how dominant the top domain is vs the second-best.
    Low confidence (< 40) means the text is ambiguous or multi-domain.
    """
    tl = text.lower()
    scores: dict[str, int] = {}

    for domain, cfg in DOMAINS.items():
        s = 0
        for kw in cfg["primary"]:
            if _wb(kw).search(tl):
                s += 3
        for kw in cfg["secondary"]:
            if _wb(kw).search(tl):
                s += 1
        for kw in cfg["titles"]:
            if _wb(kw).search(tl):
                s += 4
        scores[domain] = s

    if not any(scores.values()):
        return "unknown", 0, scores

    top_domain   = max(scores, key=scores.__getitem__)
    top_score    = scores[top_domain]
    sorted_vals  = sorted(scores.values(), reverse=True)
    second_score = sorted_vals[1] if len(sorted_vals) > 1 else 0

    # Confidence: gap between top and second-best, normalised
    gap        = top_score - second_score
    confidence = min(100, int((gap / max(top_score, 1)) * 100))

    return top_domain, confidence, scores


def role_fit(resume_domain: str, jd_domain: str) -> int:
    """Return 0-100 compatibility score between resume domain and JD domain."""
    if resume_domain == "unknown" or jd_domain == "unknown":
        return 50   # can't judge — be neutral
    # non_it resume on any IT JD (or vice versa) = near zero fit
    if resume_domain == "non_it" or jd_domain == "non_it":
        return _COMPAT.get(
            (resume_domain, jd_domain),
            _COMPAT.get((jd_domain, resume_domain), 5)
        )
    return _COMPAT.get((resume_domain, jd_domain),
           _COMPAT.get((jd_domain, resume_domain), _DEFAULT_COMPAT))


def is_non_it(domain: str) -> bool:
    """Returns True if the classified domain is non-IT (should be skipped in pipeline)."""
    return domain == "non_it"


def combined_score(ats: float, fit: int) -> int:
    """
    Weighted combined score.

    When role fit is high  (≥ 65): ATS keyword quality matters more → 60/40 split
    When role fit is medium(35-64): balanced                          → 50/50 split
    When role fit is low   (< 35):  role mismatch dominates penalty  → 30/70 split

    This means a 90% ATS oracle resume on a DevOps job (fit~18)
    gets: 90*0.3 + 18*0.7 = 27 + 13 = 40 — borderline / low
    While a 65% ATS DevOps resume on a DevOps job (fit~100)
    gets: 65*0.6 + 100*0.4 = 39 + 40 = 79 — strong fit
    """
    if fit >= 65:
        return round(ats * 0.60 + fit * 0.40)
    elif fit >= 35:
        return round(ats * 0.50 + fit * 0.50)
    else:
        return round(ats * 0.30 + fit * 0.70)


def domain_label(domain: str) -> str:
    """Human-readable label for a domain key."""
    return DOMAINS.get(domain, {}).get("label", domain.replace("_", " ").title())
