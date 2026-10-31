"""
Script to generate the ISWE407L Course Design Project Report as a formatted .docx document.
"""

import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from pathlib import Path


def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def create_report():
    doc = Document()

    # Set Margins
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Styles
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_inst = title_p.add_run("COURSE DESIGN PROJECT REPORT\n")
    run_inst.font.size = Pt(14)
    run_inst.font.bold = True
    run_inst.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    run_course = title_p.add_run("ISWE407L – User Interface and User Experience Design\n\n")
    run_course.font.size = Pt(16)
    run_course.font.bold = True
    run_course.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    run_proj = title_p.add_run("AgentProbe: UI/UX Design for an Enterprise AI Agent Failure-Mode Evaluation & Trajectory Replay Harness\n")
    run_proj.font.size = Pt(20)
    run_proj.font.bold = True
    run_proj.font.color.rgb = RGBColor(0x00, 0x20, 0x60)

    doc.add_paragraph().paragraph_format.space_after = Pt(20)

    # -------------------------------------------------------------
    # SECTION 1: PROJECT SCOPE AND DOMAIN
    # -------------------------------------------------------------
    h1 = doc.add_heading("1. Project Scope and Domain", level=1)
    h1.paragraph_format.space_before = Pt(12)

    doc.add_heading("1.1 Domain Overview", level=2)
    p = doc.add_paragraph(
        "AgentProbe is situated at the intersection of Enterprise Financial Operations (Payment Operations / PayOps), "
        "Autonomous AI Agent Tool Orchestration, and AI Reliability Engineering. In production enterprise environments, "
        "autonomous LLM-powered agents are increasingly deployed to automate multi-step operations over structured relational "
        "databases—such as auditing transaction declines, executing customer refunds, retrying failed payments, and enforcing anti-fraud "
        "compliance rules. However, because LLMs are non-deterministic, enterprise users and risk officers face severe cognitive friction "
        "due to the 'black box' problem, where agents hallucinate tool arguments, enter infinite execution loops, or fall prey to adversarial "
        "prompt injections hidden inside customer transaction notes."
    )

    doc.add_heading("1.2 Problem Statement", level=2)
    p = doc.add_paragraph(
        "Existing agent monitoring tools (e.g., raw console logs, static benchmark scoreboards) fail from a UI/UX perspective because:\n"
        "1. Lack of Explanatory Transparency: Operators cannot observe the chronological progression of agent reasoning (Plan ➔ Act ➔ Observe ➔ Reflect).\n"
        "2. Absence of Root-Cause Failure Taxonomies: Failures are reported as generic timeout or API exceptions rather than categorized behavioral failures.\n"
        "3. High Cognitive Burden in High-Risk Actions: Risk officers lack intuitive supervisory interfaces to review, approve, or reject high-risk actions (e.g., refunds exceeding $1,000) under strict compliance timeframes."
    )

    doc.add_heading("1.3 Project Scope", level=2)
    doc.add_paragraph("In-Scope UI/UX Capabilities:")
    in_scope_items = [
        "Interactive Executive Benchmark Dashboard: Real-time visual comparison of task success, tool selection accuracy, unnecessary calls, latency, and cost across multiple models and architectures.",
        "Diagnostic Failure Taxonomy Explorer: Interactive multi-level drill-down visualizing 7 distinct classes of agent failure modes (Hallucinated Args, Loops, Premature Stops, Constraint Violations, Prompt Injections, Gate Bypasses, Selection Errors).",
        "Chronological 'Flight Recorder' Trajectory Replayer: Granular visual timeline decomposing every single step of agent execution into Thought, Tool Action, Observation, and Reflection cards.",
        "Interactive Payment Operations Sandbox: Live testing environment allowing operators to filter scenarios, modify prompts, select model brains, and trigger live investigations with instant telemetry cards.",
        "Human-in-the-Loop (HITL) Supervisory Queue: Dedicated supervisory workspace for reviewing high-risk payment escalations with dual-action (Approve/Reject) controls and cryptographic token issuance."
    ]
    for item in in_scope_items:
        doc.add_paragraph(item, style='List Bullet')

    doc.add_paragraph("Out-of-Scope:")
    out_scope_items = [
        "Direct core banking ledger manipulation (handled securely via backend tool APIs).",
        "Manual model weight fine-tuning or low-level parameter training.",
        "General-purpose consumer chat interfaces (the interface is purpose-built for enterprise risk and AI reliability engineers)."
    ]
    for item in out_scope_items:
        doc.add_paragraph(item, style='List Bullet')

    doc.add_heading("1.4 Target User Personas", level=2)
    table_personas = doc.add_table(rows=1, cols=3)
    table_personas.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table_personas.rows[0].cells
    hdr[0].text = "User Persona"
    hdr[1].text = "Primary Goal & Context"
    hdr[2].text = "Key UI/UX Need"
    for c in hdr:
        set_cell_background(c, "1F4E79")
        for p in c.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                r.font.bold = True

    personas_data = [
        ("AI Reliability Engineer (Sarah, 29)", "Evaluates agent architectures (ReAct vs. LangGraph vs. Plan-and-Execute) to minimize tool waste and eliminate loops.", "High-density comparative metrics, side-by-side bar charts, and exportable JSON/CSV diagnostic telemetry."),
        ("Payment Operations Supervisor (Marcus, 42)", "Oversees customer disputes, audits agent decisions, and signs off on high-value refunds (> $1,000).", "High-clarity approval queue, visual risk level badges (Low, Medium, Critical), and one-click token authorization."),
        ("Financial Compliance & Security Officer (Elena, 36)", "Verifies that autonomous agents resist adversarial prompt injections and adhere to AML/fraud policies.", "Adversarial attack success rate telemetry, red-flag highlight alerts, and immutable audit log traces.")
    ]
    for role, goal, need in personas_data:
        row = table_personas.add_row().cells
        row[0].text = role
        row[1].text = goal
        row[2].text = need
        set_cell_background(row[0], "F2F2F2")

    # -------------------------------------------------------------
    # SECTION 2: FUNCTIONAL REQUIREMENTS
    # -------------------------------------------------------------
    doc.add_page_break()
    h2 = doc.add_heading("2. Functional Requirements", level=1)
    h2.paragraph_format.space_before = Pt(12)

    p_fr_intro = doc.add_paragraph(
        "The functional requirements for AgentProbe are categorized according to core user workflows and system modules:"
    )

    fr_data = [
        ("FR-1.1", "Benchmark KPI Telemetry", "System shall compute and render executive KPI cards displaying Task Success Rate, Tool Selection F1-Score, Argument Correctness, Adversarial Injection Defense Rate, and Total Test Runs.", "High"),
        ("FR-1.2", "Architecture Comparison Visualizer", "System shall render grouped bar charts comparing Barebones ReAct, LangGraph StateGraph, and Plan-and-Execute across tool efficiency, unnecessary calls, and latency.", "High"),
        ("FR-2.1", "Failure Mode Distribution Chart", "System shall visualize the proportion of execution failures across 7 standardized failure taxonomy categories using an interactive Plotly donut chart.", "High"),
        ("FR-2.2", "Taxonomy Drill-Down Inspector", "System shall allow users to select any failure category from a dropdown to immediately view all matching scenario runs, termination codes, and duration telemetry.", "Medium"),
        ("FR-3.1", "Scenario Trajectory Selector", "System shall provide a categorized selector allowing users to load any scenario and behavioral model run for step-by-step trace inspection.", "High"),
        ("FR-3.2", "Four-Phase Step Decomposer", "System shall visually decompose each execution step into collapsible accordion cards displaying: Model Thought, Tool Call (with JSON args), Observation, and Reflection.", "High"),
        ("FR-3.3", "Step Latency & Token Badge", "Each trajectory step card shall display real-time latency in milliseconds and token consumption badges for cost tracking.", "Medium"),
        ("FR-4.1", "Interactive Sandbox Runner", "System shall allow operators to modify the user dispute prompt, select agent architecture and model backend, and execute live investigations on an isolated sandbox database.", "High"),
        ("FR-4.2", "Live Evaluation Scorecard", "System shall render an immediate post-run evaluation scorecard showing Task Success (PASS/FAIL), Tool F1, Argument Accuracy, and Step Efficiency.", "High"),
        ("FR-5.1", "Escalation Queue Feed", "System shall render real-time cards for transactions escalated due to high value (> $1,000) or high risk, displaying transaction ID, amount, urgency, and rationale.", "High"),
        ("FR-5.2", "Cryptographic Sign-off Action", "System shall provide 'Approve' and 'Reject' buttons. Approval must issue a single-use cryptographic token (AUTH-GATE-XXXX) and update database status.", "High"),
        ("FR-6.1", "Multi-Format Report Export", "System shall allow users to download the comprehensive benchmark technical report as Markdown (.md) or raw trace data as JSON and CSV.", "Medium")
    ]

    table_fr = doc.add_table(rows=1, cols=4)
    table_fr.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_fr = table_fr.rows[0].cells
    hdr_fr[0].text = "Req ID"
    hdr_fr[1].text = "Feature Name"
    hdr_fr[2].text = "Functional Description"
    hdr_fr[3].text = "Priority"
    for c in hdr_fr:
        set_cell_background(c, "1F4E79")
        for p in c.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                r.font.bold = True

    for req_id, name, desc, prio in fr_data:
        row = table_fr.add_row().cells
        row[0].text = req_id
        row[1].text = name
        row[2].text = desc
        row[3].text = prio
        set_cell_background(row[0], "F8F9FA")

    # -------------------------------------------------------------
    # SECTION 3: CONCEPTUAL DESIGN
    # -------------------------------------------------------------
    doc.add_page_break()
    h3 = doc.add_heading("3. Conceptual Design", level=1)
    h3.paragraph_format.space_before = Pt(12)

    doc.add_paragraph(
        "For AgentProbe, we adopt the Object-Action Interface (OAI) Model and Mental Model Conceptual Framework "
        "grounded in Ben Shneiderman's Information Seeking Mantra ('Overview first, zoom and filter, details-on-demand'). "
        "The conceptual design bridges the gap between complex non-deterministic LLM execution mechanics and the enterprise user's mental model."
    )

    doc.add_heading("3.1 Conceptual Metaphors", level=2)
    metaphors = [
        ("The 'Flight Data Recorder' (Black Box) Metaphor:", 
         "Just as an aircraft flight recorder records cockpit voice and sensor readings sequentially to understand safety incidents, "
         "AgentProbe records each cognitive agent impulse as a discrete, replayable timestamped trajectory step: Plan (Pilot intention) ➔ "
         "Act (Control input) ➔ Observe (Instrument reading) ➔ Reflect (Course correction). This metaphor instantly demystifies agent reasoning for operators."),
        ("The 'Dual-Control Vault / Courtroom' Metaphor:", 
         "High-risk enterprise operations (> $1,000 refunds, account freezes) cannot be executed by an autonomous entity alone. "
         "They are placed into a supervisory 'holding cell' requiring a second human key (cryptographic supervisor token) to unlock, "
         "mimicking dual-control financial vaults."),
        ("The 'Diagnostic Pathology Lab' Metaphor:", 
         "Rather than viewing an agent failure as a software crash, failures are treated as biological pathologies categorized into a formal "
         "taxonomy (e.g., Hallucinations, Loops, Parasitic Prompt Injections), allowing precision diagnosis and targeted mitigation."
        )
    ]
    for title, desc in metaphors:
        p = doc.add_paragraph()
        r = p.add_run(title + " ")
        r.bold = True
        r.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
        p.add_run(desc)

    doc.add_heading("3.2 Object-Action Interface (OAI) Mapping", level=2)
    p_oai = doc.add_paragraph(
        "In the OAI model, user tasks are broken down into task objects and task actions, which are directly mapped to interface objects and interface actions:"
    )

    table_oai = doc.add_table(rows=1, cols=4)
    table_oai.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_oai = table_oai.rows[0].cells
    hdr_oai[0].text = "Task Object (Mental Model)"
    hdr_oai[1].text = "Task Action"
    hdr_oai[2].text = "Interface Object (UI Element)"
    hdr_oai[3].text = "Interface Action (Interaction)"
    for c in hdr_oai:
        set_cell_background(c, "1F4E79")
        for p in c.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                r.font.bold = True

    oai_rows = [
        ("Payment Scenario", "Test agent against corner-case or fraud attack", "Scenario Dropdown & Difficulty Filter", "Select scenario; click 'Run Sandbox'"),
        ("Agent Trajectory", "Inspect why an agent failed or took excessive steps", "Chronological Accordion Step Cards", "Click expander to view Plan/Act/Observe/Reflect"),
        ("Failure Taxonomy", "Identify systemic vulnerabilities across models", "Plotly Donut Chart & Category Matrix", "Click chart slice; filter drill-down table"),
        ("Approval Gate", "Review and authorize/reject high-risk actions", "Escalation Card with Urgency Pill", "Click 'Approve' to issue AUTH-GATE token"),
        ("Benchmark Suite", "Compare architectures (ReAct vs LangGraph)", "Multi-metric Grouped Bar Chart", "Toggle metrics legend; slider for scenario count")
    ]
    for to, ta, io, ia in oai_rows:
        row = table_oai.add_row().cells
        row[0].text = to
        row[1].text = ta
        row[2].text = io
        row[3].text = ia
        set_cell_background(row[0], "F2F2F2")

    # -------------------------------------------------------------
    # SECTION 4: DERIVING THE MENUS FROM YOUR DESIGN
    # -------------------------------------------------------------
    doc.add_page_break()
    h4 = doc.add_heading("4. Deriving the Menus from Your Design", level=1)
    h4.paragraph_format.space_before = Pt(12)

    doc.add_heading("4.1 Information Architecture (IA) Derivation", level=2)
    doc.add_paragraph(
        "The navigation and menu structure was derived through Closed Card Sorting and Task-Oriented Hierarchical Decomposition. "
        "The platform's features naturally cluster into three primary mental workflows:\n"
        "1. Aggregate Evaluation Workflow: Executive decision-makers and evaluators need macro-level summaries.\n"
        "2. Forensic Diagnostics Workflow: Engineers need micro-level trace replays and failure mode categorization.\n"
        "3. Operational Governance Workflow: Supervisors need active real-time queue management and sandbox experimentation."
    )

    doc.add_paragraph("Hierarchical Navigation Menu Structure:")
    ia_structure = [
        "Primary Navigation (Persistent Left Sidebar):",
        "  ├── 1. 📊 Benchmark Overview (Macro-level architecture & model comparison, KPI cards, suite configuration)",
        "  ├── 2. 🔍 Failure Taxonomy Diagnostics (Root-cause classification, donut distribution, incident drill-down)",
        "  ├── 3. 🎬 Step-by-Step Trajectory Replay (Flight recorder inspector, Plan-Act-Observe-Reflect chronological cards)",
        "  ├── 4. 🧪 Interactive Scenario Sandbox (Live testbed, custom prompt overrides, instant evaluation scorecard)",
        "  ├── 5. 🧑‍⚖️ Human Approval Queue (Supervisory governance desk, high-risk refund cards, one-click authorization)",
        "  └── 6. 📑 Technical Report & Export (Markdown research report download, raw JSON traces, CSV dataset export)"
    ]
    for s in ia_structure:
        p = doc.add_paragraph(s)
        p.paragraph_format.left_indent = Inches(0.2)
        p.paragraph_format.space_after = Pt(2)

    doc.add_heading("4.2 Menu Derivation Matrix", level=2)
    table_menu = doc.add_table(rows=1, cols=4)
    table_menu.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_m = table_menu.rows[0].cells
    hdr_m[0].text = "Menu Level"
    hdr_m[1].text = "Menu Item"
    hdr_m[2].text = "Underlying Conceptual Object"
    hdr_m[3].text = "User Need Addressed"
    for c in hdr_m:
        set_cell_background(c, "1F4E79")
        for p in c.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                r.font.bold = True

    menu_rows = [
        ("Global (Level 1)", "📊 Benchmark Overview", "BenchmarkSuiteResult, ModelPricing", "Quick assessment of overall pass rate, cost, and architecture trade-offs."),
        ("Global (Level 1)", "🔍 Failure Taxonomy", "FailureMode, FailureClassifier", "Pinpointing whether bugs are due to hallucinations, loops, or prompt injection."),
        ("Global (Level 1)", "🎬 Trajectory Replay", "Trajectory, StepRecord, ToolCall", "Detailed visual post-mortem of specific step-by-step agent decisions."),
        ("Global (Level 1)", "🧪 Sandbox Runner", "Scenario, AgentFactory, Database", "Testing live prompts against corner-case edge conditions without writing code."),
        ("Global (Level 1)", "🧑‍⚖️ Approval Queue", "ApprovalGate, TokenNonce", "Managing high-risk financial liability through supervisory sign-offs."),
        ("Contextual (Level 2)", "Architecture Dropdown", "BarebonesReAct, LangGraph, PlanExecute", "Switching execution paradigms within sandbox or trajectory replayer."),
        ("Contextual (Level 2)", "Model Profile Dropdown", "Golden, Hallucinating, Vulnerable", "Stress-testing agent resilience against specific behavioral archetypes.")
    ]
    for ml, mi, uco, una in menu_rows:
        row = table_menu.add_row().cells
        row[0].text = ml
        row[1].text = mi
        row[2].text = uco
        row[3].text = una
        set_cell_background(row[0], "F8F9FA")

    # -------------------------------------------------------------
    # SECTION 5: LOW-FIDELITY AND HIGH-FIDELITY SCREENSHOTS
    # -------------------------------------------------------------
    doc.add_page_break()
    h5 = doc.add_heading("5. Low-Fidelity and High-Fidelity Design Artifacts", level=1)
    h5.paragraph_format.space_before = Pt(12)

    doc.add_paragraph(
        "This section presents the low-fidelity architectural wireframes and high-fidelity screen implementations "
        "across the primary workflows of the AgentProbe platform."
    )

    doc.add_heading("5.1 Screen 1: Executive Benchmark & Architecture Comparison", level=2)
    doc.add_paragraph("Low-Fidelity Structural Wireframe (Layout Grid):")

    wireframe_screen1 = """
+-----------------------------------------------------------------------------------------------+
|  AGENTPROBE   |  [KPI: Pass Rate 91.8%] [KPI: Tool F1 94.7%] [KPI: Defense 100%] [Runs: 225]  |
+---------------+-------------------------------------------------------------------------------+
| [Nav Sidebar] |  Architecture Comparison: Success Rate vs Tool F1 (Grouped Bar Chart)          |
| * Benchmark   |  +-------------------------------------------------------------------------+  |
|   Taxonomy    |  |  100% |  [ReAct]       [LangGraph]      [Plan & Execute]                |  |
|   Replay      |  |   80% |  Success: 64%  Success: 88%     Success: 92%                    |  |
|   Sandbox     |  |   60% |  F1: 72%       F1: 91%          F1: 95%                         |  |
|   Approvals   |  |    0% +-----------------------------------------------------------------+  |
|   Reports     |                                                                               |
|               |  Architecture Performance Matrix (Tabular Breakdown)                          |
|               |  +--------------------+-------+--------------+---------+------------+-------+ |
|               |  | Architecture       | Runs  | Success Rate | Tool F1 | Unnec.Calls| Latency| |
|               |  +--------------------+-------+--------------+---------+------------+-------+ |
|               |  | Barebones ReAct    | 75    | 64.2%        | 72.1%   | 45         | 3.2ms | |
|               |  | LangGraph ReAct    | 75    | 88.0%        | 91.4%   | 15         | 4.8ms | |
|               |  | Plan & Execute     | 75    | 91.8%        | 94.7%   | 0          | 6.1ms | |
|               |  +--------------------+-------+--------------+---------+------------+-------+ |
+---------------+-------------------------------------------------------------------------------+
"""
    p_w1 = doc.add_paragraph(wireframe_screen1)
    p_w1.style.font.name = 'Courier New'
    p_w1.style.font.size = Pt(8.5)

    doc.add_paragraph("High-Fidelity UI Implementation Details (Screen 1):")
    screen1_details = [
        "Header KPI Cards: Rendered with high-contrast colored left-borders (#1f4e79), large 28pt metric typography, and contextual change badges.",
        "Interactive Plotly Charts: Color-coded grouped bar charts displaying Success Rate (#1f77b4), Tool F1 (#2ca02c), and Argument Correctness (#ff7f0e) with interactive hover tooltips.",
        "Sidebar Radio Navigation: Consistent persistent navigation state, branding shield icon, and architectural key reference guide."
    ]
    for d in screen1_details:
        doc.add_paragraph(d, style='List Bullet')

    doc.add_heading("5.2 Screen 2: Step-by-Step Trajectory Replay ('Flight Recorder')", level=2)
    doc.add_paragraph("Low-Fidelity Structural Wireframe:")

    wireframe_screen2 = """
+-----------------------------------------------------------------------------------------------+
|  AGENTPROBE   |  Scenario: SCEN-001 - Low-Value Refund | Model: Golden | Arch: BarebonesReAct   |
+---------------+-------------------------------------------------------------------------------+
| [Nav Sidebar] |  Status: [SUCCESS] | Termination: COMPLETED | Latency: 1.49ms | Cost: $0.00000 |
|   Benchmark   +-------------------------------------------------------------------------------+
|   Taxonomy    |  Execution Trajectory (Chronological Step Accordion)                          |
| * Replay      |  [-] Step 1: Phase 'act_observe_reflect' | Latency: 0.91ms                     |
|   Sandbox     |      Thought: "Plan: 1) Query database for TX-1001. 2) Fetch risk score."     |
|   Approvals   |      Tool Action: query_database {"query": "SELECT * FROM transactions..."}   |
|   Reports     |      Observation: [query_database SUCCESS] {"row_count": 1, "status": SETTLED}|
|               |      Reflection: Action executed successfully. Proceeding to risk fetch.      |
|               |  [-] Step 2: Phase 'act_observe_reflect' | Latency: 0.23ms                     |
|               |      Tool Action: fetch_risk_score {"transaction_id": "TX-1001"}              |
|               |      Observation: [fetch_risk_score SUCCESS] {"risk_score": 0.05, "LOW"}      |
|               |  [-] Step 3: Phase 'reflect' | Latency: 0.35ms                                |
|               |      Tool Action: refund_transaction {"amount_cents": 4500, "reason": "VALID"} |
|               |      Observation: [refund_transaction SUCCESS] Status: REFUNDED                |
|               |      Final Output: "Investigation complete. Full refund processed."           |
+---------------+-------------------------------------------------------------------------------+
"""
    p_w2 = doc.add_paragraph(wireframe_screen2)
    p_w2.style.font.name = 'Courier New'
    p_w2.style.font.size = Pt(8.5)

    doc.add_paragraph("High-Fidelity UI Implementation Details (Screen 2):")
    screen2_details = [
        "Accordion Card Hierarchy: Each step expands into a two-column grid separating internal cognitive thought from environmental tool input/output observations.",
        "JSON Inspector: Monospace formatted syntax-highlighted code blocks for tool arguments and database return rows.",
        "Telemetry Pill Badges: Real-time duration indicators and visual indicators for SUCCESS (green badge #d4edda) vs ERROR (red badge #f8d7da)."
    ]
    for d in screen2_details:
        doc.add_paragraph(d, style='List Bullet')

    doc.add_heading("5.3 Screen 3: Failure Taxonomy Diagnostics & Drill-Down", level=2)
    doc.add_paragraph("Low-Fidelity Structural Wireframe:")

    wireframe_screen3 = """
+-----------------------------------------------------------------------------------------------+
|  AGENTPROBE   |  Failure Mode Taxonomy & Root Cause Diagnostics                               |
+---------------+-------------------------------------------------------------------------------+
| [Nav Sidebar] |  Failure Mode Proportion (Donut Chart)   | Taxonomy Descriptions               |
|   Benchmark   |            .---.                         | 1. IGNORING_CONSTRAINTS (28%)       |
| * Taxonomy    |         .-'  |  '-.                      | 2. PROMPT_INJECTION (22%)           |
|   Replay      |        /  (Donut)  \                     | 3. INFINITE_LOOP (18%)              |
|   Sandbox     |       |    Chart    |                    | 4. HALLUCINATED_ARGS (14%)          |
|   Approvals   |        \           /                     | 5. PREMATURE_STOPPING (11%)         |
|   Reports     |         '-.     .-'                      | 6. APPROVAL_GATE_BYPASS (7%)        |
|               |            '---'                         +-------------------------------------+
|               |  Filter by Failure Mode: [IGNORING_CONSTRAINTS v]                              |
|               |  Matching Incidents (Tabular Drill-Down)                                       |
|               |  +-------------+------------------+-----------------------+------------------+ |
|               |  | Scenario ID | Architecture     | Model Profile         | Termination Code | |
|               |  +-------------+------------------+-----------------------+------------------+ |
|               |  | SCEN-029    | barebones_react  | constraint_violator   | POLICY_VIOLATION | |
|               |  | SCEN-030    | langgraph_react  | constraint_violator   | THRESHOLD_BREACH | |
|               |  +-------------+------------------+-----------------------+------------------+ |
+---------------+-------------------------------------------------------------------------------+
"""
    p_w3 = doc.add_paragraph(wireframe_screen3)
    p_w3.style.font.name = 'Courier New'
    p_w3.style.font.size = Pt(8.5)

    doc.add_heading("5.4 Screen 4: Human-in-the-Loop Supervisory Approval Queue", level=2)
    doc.add_paragraph("Low-Fidelity Structural Wireframe:")

    wireframe_screen4 = """
+-----------------------------------------------------------------------------------------------+
|  AGENTPROBE   |  Human-in-the-Loop Escalation Desk (Pending Supervisor Approvals)             |
+---------------+-------------------------------------------------------------------------------+
| [Nav Sidebar] |  +-------------------------------------------------------------------------+  |
|   Benchmark   |  | Gate ID: GATE-4B29 | Tx: TX-4001 | Amount: $2,500.00 | Urgency: [HIGH]  |  |
|   Taxonomy    |  | Action Requested: REFUND | Status: PENDING                              |  |
|   Replay      |  | Rationale: High-value refund exceeds unsupervised limit ($1,000.00).    |  |
|   Sandbox     |  | Auth Token: [AWAITING SUPERVISOR ACTION]                                |  |
| * Approvals   |  |                                                                         |  |
|   Reports     |  |   [ [v] Approve & Issue Token ]      [ [x] Reject Request ]             |  |
|               |  +-------------------------------------------------------------------------+  |
|               |  | Gate ID: GATE-8F12 | Tx: TX-5001 | Amount: $5,000.00 | Urgency: [CRIT]  |  |
|               |  | Action Requested: MANUAL_INVESTIGATION | Status: APPROVED               |  |
|               |  | Rationale: Adversarial prompt injection detected in memo field.         |  |
|               |  | Auth Token: AUTH-GATE-F4A19B7E329C                                      |  |
|               |  +-------------------------------------------------------------------------+  |
+---------------+-------------------------------------------------------------------------------+
"""
    p_w4 = doc.add_paragraph(wireframe_screen4)
    p_w4.style.font.name = 'Courier New'
    p_w4.style.font.size = Pt(8.5)

    doc.add_heading("5.5 Design System & Accessibility Compliance (WCAG 2.1 AA)", level=2)
    doc.add_paragraph(
        "To ensure production usability in mission-critical financial operations environments, AgentProbe adheres "
        "to a strict Design System and accessibility standards:\n"
        "1. Visual Hierarchy & Typography: Clean sans-serif primary interface font (Inter / Segoe UI) with fixed-pitch fonts (JetBrains Mono / Consolas) for transactional tokens and code outputs.\n"
        "2. Color Contrast Ratios: All text-to-background combinations maintain a minimum contrast ratio of 4.8:1, exceeding WCAG 2.1 AA requirements.\n"
        "3. Multi-Channel Feedback: System actions (such as token authorization) provide dual redundant feedback—both color-coded state transitions and descriptive textual status announcements."
    )

    # -------------------------------------------------------------
    # SECTION 6: CONCLUSION & SUMMARY
    # -------------------------------------------------------------
    h6 = doc.add_heading("6. Conclusion & Design Validation", level=1)
    h6.paragraph_format.space_before = Pt(12)
    doc.add_paragraph(
        "The AgentProbe UI/UX design successfully bridges the operational gap between complex autonomous agent behaviors "
        "and human supervisory control. By translating low-level execution logs into a structured Object-Action conceptual model "
        "(Flight Recorder metaphor, Supervisory Holding Gate, Diagnostic Pathology Lab), the system reduces cognitive overload, "
        "empowers risk analysts to audit multi-step agent decisions in milliseconds, and guarantees compliance with financial safety mandates."
    )

    out_file = Path("c:/Users/sanja/Downloads/AgentProbe/ISWE407L_Course_Design_Project_Report.docx")
    doc.save(str(out_file))
    print(f"Report generated successfully: {out_file}")


if __name__ == "__main__":
    create_report()
