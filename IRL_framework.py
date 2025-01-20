import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
from datetime import datetime

############################################################################
# IRL Co-Creation Wizard for Hydrogen Technologies
# 
# Features:
# 1) Passcode login ("DECODE"), optional name => "Anonymous" if blank.
# 2) 5-step wizard: Introduction -> Method Categories -> Parent Attributes
#    -> Child Attributes -> Final Comments.
# 3) Full dictionary of child attributes (including "Utility") for each category.
# 4) Stores feedback in a SQLite DB with possibility to delete
#    their own feedback.
# 5) No st.experimental_rerun / st.stop; uses a refresh flag approach.
# 6) Professional academic language suitable for consortium partners.
############################################################################

########################
# GLOBAL CONFIG
########################

PASSCODE = "DECODE"
DB_NAME = "irl_feedback.db"

# Wizard steps in order
WIZARD_STEPS = [
    "Introduction",
    "Method Categories",
    "Parent Attributes",
    "Child Attributes",
    "Final Comments"
]

# Method categories (5 main ones)
METHOD_CATEGORIES = [
    "Simulations",
    "Modeling",
    "Characterization",
    "Testing",
    "Assessment"
]

# Parent attributes (including Utility as a full dimension)
PARENT_ATTRIBUTES = [
    "Maturity",
    "Resource Requirements",
    "Interoperability",
    "Integration Complexity",
    "Utility"
]

# Full dictionary of child attributes for each category & parent attribute.
CHILD_ATTRIBUTES_DICT = {
    "Simulations": {
        "Maturity": [
            ("Validation Level",
             "How thoroughly the simulation method is validated against experimental or benchmark data.",
             "1=No validation; 5=Some; 9=Extensively validated"),
            ("Numerical Stability",
             "Frequency of solver crashes, convergence issues, or non-physical results.",
             "1=Frequent instabilities; 5=Occasional issues; 9=Very stable"),
            ("Method Standardization",
             "Degree of standardized protocols, best practices, and accepted formats.",
             "1=Ad-hoc; 5=Some guidelines; 9=Fully standardized")
        ],
        "Resource Requirements": [
            ("Licensing Costs",
             "Financial cost of simulation software licenses.",
             "1=Very expensive; 5=Moderate; 9=Open-source/free"),
            ("Computational Demand",
             "CPU/GPU hours, memory requirements, runtime.",
             "1=Requires HPC/very long runs; 5=Overnight; 9=Minimal footprint"),
            ("Training Load",
             "Expertise and time required to learn and operate the simulation method.",
             "1=Highly specialized; 5=Graduate-level skill; 9=Intuitive/minimal training")
        ],
        "Interoperability": [
            ("Data Format Compatibility",
             "Ability to import/export data in standard formats (e.g., EC-lab, netCDF).",
             "1=Proprietary only; 5=Partial; 9=Fully open"),
            ("Platform Independence",
             "Ability to run on various OS/HPC environments.",
             "1=Single OS; 5=Multi-OS with tweaks; 9=Fully cross-platform"),
            ("API/Scripting Availability",
             "Availability of APIs or scripting interfaces for customization.",
             "1=No API; 5=Limited; 9=Extensive APIs")
        ],
        "Integration Complexity": [
            ("Pre-processing Time",
             "Time/effort to set up geometry, boundary conditions, and meshing.",
             "1=Days; 5=Hours; 9=Automated in minutes"),
            ("Post-processing Tools",
             "Quality and user-friendliness of visualization and analysis tools.",
             "1=Complex external steps; 5=Basic tools; 9=Advanced & automated"),
            ("Parameter Sensitivity & UQ Modules",
             "Ease of performing uncertainty quantification and parameter sweeps.",
             "1=Manual/tedious; 5=Some scripting; 9=Fully integrated")
        ],
        "Utility": [
            ("Predictive Value",
             "How beneficial are the simulation outputs for hydrogen R&D or industrial workflows?",
             "1=Minimal impact; 5=Moderate; 9=Transformative"),
            ("Industry Alignment",
             "Relevance to IEC/ISO, DoE references, HPC usage optimizations.",
             "1=Low relevance; 5=Medium; 9=Fully aligned & strategic")
        ]
    },
    "Modeling": {
        "Maturity": [
            ("Theoretical Foundation Robustness",
             "How well-accepted the theoretical underpinnings are.",
             "1=Speculative; 5=Moderately accepted; 9=Widely accepted"),
            ("Code Base Stability",
             "Frequency and magnitude of model code revisions.",
             "1=Constant major changes; 5=Occasional updates; 9=Very stable"),
            ("Parameter Validation",
             "Level of parameter fitting and validation against data.",
             "1=Poorly validated; 5=Some; 9=Thoroughly validated")
        ],
        "Resource Requirements": [
            ("Software Cost",
             "Licensing or acquisition cost of modeling tools.",
             "1=Very expensive; 5=Moderate/partial OS; 9=Open-source/free"),
            ("Computational Efficiency",
             "Runtime and resource usage for solving or parameter estimation.",
             "1=Days/run; 5=Hours/run; 9=Minutes or less"),
            ("Maintenance Overhead",
             "Effort to keep the model updated and functional.",
             "1=Frequent recalibration; 5=Occasional updates; 9=Low maintenance")
        ],
        "Interoperability": [
            ("Input Data Format Compatibility",
             "Ability to use standard data sets or link with experimental databases.",
             "1=Proprietary only; 5=Some standard imports; 9=Fully flexible"),
            ("Model Coupling Capability",
             "Ease of linking this model to other models.",
             "1=Standalone; 5=Partial bridging; 9=Fully modular"),
            ("Documentation & Standards",
             "Quality of documentation and adherence to modeling standards.",
             "1=Poor docs; 5=Basic; 9=Comprehensive/standardized")
        ],
        "Integration Complexity": [
            ("Implementation Complexity",
             "Difficulty integrating the model into existing workflows.",
             "1=Very difficult; 5=Moderate; 9=Plug-and-play"),
            ("Sensitivity Analysis Tools",
             "Built-in parameter sensitivity and uncertainty routines.",
             "1=None; 5=Limited; 9=Robust integrated features"),
            ("Scalability",
             "Ability to scale from component-level to system-level modeling.",
             "1=Restricted; 5=Some scaling; 9=Easily scalable")
        ],
        "Utility": [
            ("Predictive Accuracy vs. Project Goals",
             "Does the model significantly improve decision-making or project KPIs?",
             "1=Marginal; 5=Useful; 9=Highly impactful"),
            ("Adoption Potential",
             "Likelihood that others in the consortium or industry adopt it once integrated.",
             "1=Unlikely; 5=Moderate; 9=Very likely")
        ]
    },
    "Characterization": {
        "Maturity": [
            ("Resolution & Sensitivity",
             "Smallest distinguishable feature or analyte quantity.",
             "1=Low res; 5=Moderate; 9=High-resolution"),
            ("Reproducibility",
             "Consistency of results under identical conditions.",
             "1=Highly variable; 5=Some variability; 9=Highly reproducible"),
            ("Standard Protocol Acceptance",
             "Adoption of widely recognized characterization protocols.",
             "1=None; 5=Some guidelines; 9=Industry-level standards")
        ],
        "Resource Requirements": [
            ("Equipment Investment",
             "Capital cost of required instrumentation.",
             "1=>€200k; 5=€50k–200k; 9=<€10k"),
            ("Consumable Usage",
             "Cost/frequency of consumables per measurement.",
             "1=High cost; 5=Moderate; 9=Minimal"),
            ("Labor Intensity",
             "Personnel time required per sample.",
             "1=Hours; 5=~1 hour; 9=Minutes")
        ],
        "Interoperability": [
            ("Hardware Compatibility",
             "Ability to fit into standard sample holders or test cells.",
             "1=Custom only; 5=Adapter needed; 9=Standard holders"),
            ("Data Format Standardization",
             "Output in known, open data formats.",
             "1=Proprietary only; 5=Limited; 9=Open formats"),
            ("Calibration Transferability",
             "Ease of applying same calibration across instruments.",
             "1=Unique per setup; 5=Transferable w/adjustments; 9=Easily transferable")
        ],
        "Integration Complexity": [
            ("Setup Time",
             "Time required to prepare and align instrument/sample.",
             "1=Hours; 5=Tens of minutes; 9=Minutes"),
            ("Data Processing Complexity",
             "Difficulty converting raw data into metrics.",
             "1=Complex multi-step; 5=Some manual steps; 9=Fully automated"),
            ("Detection Limit",
             "Lowest detectable quantity.",
             "1=High limit; 5=Moderate; 9=Very low limit")
        ],
        "Utility": [
            ("Impact on Project KPIs",
             "Degree to which characterization results drive design improvements.",
             "1=Marginal; 5=Moderate; 9=Key enabler"),
            ("Standardization Value",
             "Adds crucial standardized data for collaborative projects or regulatory approvals.",
             "1=Low; 5=Moderate; 9=High synergy")
        ]
    },
    "Testing": {
        "Maturity": [
            ("Test Protocol Stability",
             "Frequency of major changes to test procedures.",
             "1=Evolving; 5=Mostly stable; 9=Fully standardized"),
            ("Reliability Under Varied Conditions",
             "Consistency of results across different operating conditions.",
             "1=Wide variance; 5=Some; 9=Robust"),
            ("Reference to Industry Standards",
             "Alignment with recognized test standards.",
             "1=None; 5=Partial; 9=Fully aligned")
        ],
        "Resource Requirements": [
            ("Equipment Depreciation Rate",
             "Annual loss in equipment value.",
             "1=High; 5=Moderate; 9=Low depreciation"),
            ("Test Duration per Sample",
             "Length of each test cycle.",
             "1=Days; 5=Hours; 9=Minutes"),
            ("Energy Consumption per Cycle",
             "Energy used per test run.",
             "1=Very high; 5=Moderate; 9=Very low")
        ],
        "Interoperability": [
            ("Universality of Fixtures",
             "Ability to use standard fixtures for different sample types.",
             "1=Specialized; 5=Adapters needed; 9=Universal"),
            ("Software Integration Level",
             "Ease of linking test control/data acquisition with lab software.",
             "1=Manual; 5=Partial integration; 9=Fully automated"),
            ("Reporting Standardization",
             "Ability to produce results in standard reporting formats.",
             "1=Proprietary; 5=Limited; 9=Fully compliant")
        ],
        "Integration Complexity": [
            ("Setup Time",
             "Time to install and calibrate the test sample.",
             "1=Hours; 5=Tens of minutes; 9=Minutes"),
            ("Range of Test Conditions",
             "Diversity of conditions achievable (e.g., temperature, pressure).",
             "1=Very narrow; 5=Moderate; 9=Wide range"),
            ("Fault Diagnosis Tools",
             "Ability to detect/diagnose anomalies in real-time.",
             "1=None; 5=Basic alarms; 9=Advanced diagnostics")
        ],
        "Utility": [
            ("Relevance to Performance Validation",
             "Ensures direct feedback on device or material performance for project goals.",
             "1=Low; 5=Medium; 9=High synergy"),
            ("Data Quality for Scale-up",
             "Usefulness of test data for scaling to pilot or commercial applications.",
             "1=Marginal; 5=Moderate; 9=Essential")
        ]
    },
    "Assessment": {
        "Maturity": [
            ("Methodological Consensus",
             "Level of standardization and consensus.",
             "1=None; 5=Some guidance; 9=Fully standardized"),
            ("Data Quality Requirements",
             "Clarity and standardization of data quality metrics.",
             "1=Poorly defined; 5=Some guidelines; 9=Well-defined"),
            ("Update Frequency",
             "Frequency of major methodological changes.",
             "1=Frequent; 5=Occasional; 9=Very stable")
        ],
        "Resource Requirements": [
            ("Software/Database Licensing",
             "Cost of analysis tools and databases.",
             "1=Very expensive; 5=Moderate; 9=Free/open-source"),
            ("Data Acquisition Costs",
             "Effort/expense to gather input data.",
             "1=Very difficult; 5=Moderate; 9=Easily accessible"),
            ("Analyst Training",
             "Complexity of training required.",
             "1=Specialized experts; 5=Skilled professionals; 9=Minimal training")
        ],
        "Interoperability": [
            ("Compatibility with Other Frameworks",
             "Integration with other sustainability/economic frameworks.",
             "1=Very specialized; 5=Limited; 9=Broad compatibility"),
            ("Database Integration",
             "Ease of importing standard LCI or other datasets.",
             "1=None; 5=Some parsing; 9=Direct compatibility"),
            ("Reporting Standards",
             "Compliance with recognized reporting frameworks (e.g., ISO).",
             "1=Proprietary; 5=Partial; 9=Fully compliant")
        ],
        "Integration Complexity": [
            ("Time to Results",
             "Speed from input to final assessment.",
             "1=Weeks; 5=Days; 9=Hours or less"),
            ("Sensitivity/Scenario Analysis Capability",
             "Built-in scenario/uncertainty tools.",
             "1=None; 5=Manual; 9=Fully integrated"),
            ("Scalability Across Systems",
             "Suitability from component-level to full supply chain.",
             "1=Component-only; 5=Some scaling; 9=Easily scalable")
        ],
        "Utility": [
            ("Decision-Making Impact",
             "Does the assessment clearly guide strategic decisions or design changes?",
             "1=Minimal; 5=Some; 9=High impact"),
            ("Regulatory/Compliance Value",
             "Helps meet regulations, certifications, or official guidelines.",
             "1=Little relevance; 5=Useful; 9=Essential")
        ]
    }
}

###############################
# 2) DATABASE FUNCTIONS
###############################

def init_db():
    """
    Initialize the SQLite database and create the feedback table if it doesn't exist.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            user_name TEXT,
            step TEXT,
            section TEXT,
            feedback TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_feedback(user_id, user_name, step, section, feedback):
    """
    Add a new feedback entry to the database.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT INTO feedback (user_id, user_name, step, section, feedback)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, user_name, step, section, feedback.strip()))
    conn.commit()
    conn.close()

def get_feedback(step, section=None):
    """
    Retrieve feedback entries filtered by step and optionally by section.
    Returns a list of dictionaries.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if section:
        c.execute("""
            SELECT id, user_id, user_name, step, section, feedback, created_at 
            FROM feedback 
            WHERE step = ? AND section = ?
            ORDER BY created_at ASC
        """, (step, section))
    else:
        c.execute("""
            SELECT id, user_id, user_name, step, section, feedback, created_at 
            FROM feedback 
            WHERE step = ?
            ORDER BY created_at ASC
        """, (step,))
    rows = c.fetchall()
    conn.close()
    
    feedback_list = []
    for row in rows:
        feedback_list.append({
            "id": row[0],
            "user_id": row[1],
            "user_name": row[2] if row[2] else "Anonymous",
            "step": row[3],
            "section": row[4],
            "feedback": row[5],
            "created_at": row[6]
        })
    return feedback_list

def delete_feedback(record_id, user_id):
    """
    Delete a feedback entry if it belongs to the current user.
    Returns True if deletion was successful, False otherwise.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        DELETE FROM feedback
        WHERE id = ? AND user_id = ?
    """, (record_id, user_id))
    conn.commit()
    rowcount = c.rowcount
    conn.close()
    return rowcount > 0

###############################
# 3) HELPER DISPLAY FUNCTIONS
###############################

def display_feedback_entries(entries):
    """
    Display a list of feedback entries.
    Allows users to delete their own feedback entries.
    """
    if not entries:
        st.info("No feedback submitted yet for this section.")
        return
    
    for entry in entries:
        user_display = entry["user_name"]
        timestamp = entry["created_at"]
        feedback_text = entry["feedback"]
        st.markdown(f"**User**: {user_display} | **Time**: {timestamp}")
        st.write(feedback_text)
        
        # If the feedback belongs to the current user, show a delete button
        if entry["user_id"] == st.session_state["user_id"]:
            delete_key = f"delete_{entry['id']}"
            if st.button("Delete", key=delete_key):
                success = delete_feedback(entry["id"], st.session_state["user_id"])
                if success:
                    st.success("Your feedback has been deleted.")
                    # Refresh the page to reflect deletion
                    st.session_state["_refresh_flag"] = not st.session_state["_refresh_flag"]
                else:
                    st.error("Failed to delete feedback. Please try again.")
        
        st.markdown("---")

def collect_feedback(step, section_label):
    """
    Provide a text area and submit button for collecting feedback.
    """
    feedback_text = st.text_area("Your Feedback:", key=f"feedback_{step}_{section_label}", height=100)
    if st.button("Submit Feedback", key=f"submit_{step}_{section_label}"):
        if feedback_text.strip() == "":
            st.warning("Please enter some feedback before submitting.")
        else:
            add_feedback(
                user_id=st.session_state["user_id"],
                user_name=st.session_state["user_name"],
                step=step,
                section=section_label,
                feedback=feedback_text
            )
            st.success("Thank you! Your feedback has been recorded.")
            # Refresh to show the new feedback
            st.session_state["_refresh_flag"] = not st.session_state["_refresh_flag"]

###############################
# 4) WIZARD STEP FUNCTIONS
###############################

def step_introduction():
    """
    Step 1: Introduction
    """
    st.title("Step 1: Introduction to IRL Framework")
    st.info("Estimated time to complete all steps: ~30 minutes.")
    
    st.markdown(
        """
        **Welcome to the Integration Readiness Level (IRL) Framework Co-Creation Wizard.**
        
        As hydrogen technologies rapidly evolve—spanning fuel cells (PEMFC, AEMFC), 
        water electrolyzers (PEMWE, AEMWE), and related innovations—there is a growing 
        need for a standardized approach to assess how easily and effectively a given 
        scientific method can be integrated into existing Research, Development, and 
        Demonstration (RD&D) workflows.
        
        This wizard will guide you through the co-creation process of the IRL framework, 
        focusing on five core parent attributes:
        1. **Maturity**
        2. **Resource Requirements**
        3. **Interoperability**
        4. **Integration Complexity**
        5. **Utility**
        
        **Your Role:**
        - **Review** each section carefully.
        - **Provide feedback** on definitions, categorizations, and specific features.
        - **View and consider** feedback from other partners to foster collaborative refinement.
        
        **Next Steps:**
        Click on the "Next" button below to proceed to the Method Categories section.
        """
    )
    
    st.subheader("General Feedback on Introduction")
    collect_feedback("Introduction", "GeneralIntro")
    
    st.markdown("#### Existing Feedback")
    intro_feedback = get_feedback("Introduction", "GeneralIntro")
    display_feedback_entries(intro_feedback)

def step_method_categories():
    """
    Step 2: Method Categories
    """
    st.title("Step 2: Method Categories")
    st.markdown(
        """
        We propose **five main categories** for hydrogen-related methods:
        1. **Simulations** (e.g., atomistic, Computational Fluid Dynamics - CFD)
        2. **Modeling** (e.g., micro-kinetics, continuum models)
        3. **Characterization** (e.g., imaging, spectroscopy, electrochemical)
        4. **Testing** (e.g., performance, lifetime, accelerated stress tests)
        5. **Assessment** (e.g., Technology Economic Analysis - TEA, Life Cycle Assessment - LCA, Greenhouse Gas - GHG analysis, Supply Chain, Circularity)
        
        **Feedback Requested:**
        - Do these categories comprehensively cover all relevant hydrogen-related methods?
        - Should any categories be merged, subdivided, or renamed?
        - Are there any additional categories you recommend?
        """
    )
    
    chosen_cat = st.selectbox("Select a category to comment on (or 'General'):", ["General"] + METHOD_CATEGORIES)
    section_label = chosen_cat if chosen_cat != "General" else "GeneralCategories"
    collect_feedback("Method Categories", section_label)
    
    st.markdown("#### Existing Feedback")
    method_cat_feedback = get_feedback("Method Categories", section_label)
    display_feedback_entries(method_cat_feedback)

def step_parent_attributes():
    """
    Step 3: Parent Attributes
    """
    st.title("Step 3: Parent Attributes")
    st.markdown(
        """
        The IRL framework is defined by **five orthogonal parent attributes**:
        1. **Maturity** – How established, validated, and stable the method is, both theoretically and practically.
        2. **Resource Requirements** – Encompasses financial costs, computational demands, equipment investment, and training needs.
        3. **Interoperability** – Reflects the method’s capability to seamlessly exchange data with external tools, adhere to standards, and integrate into common digital ecosystems.
        4. **Integration Complexity** – Evaluates the practical effort required to incorporate the method into existing workflows, including setup complexity, configuration, and maintenance.
        5. **Utility** – Assesses how beneficial, impactful, or strategically valuable a method is once integrated. This dimension is context-dependent and should be considered separately from IRL.
        
        **Feedback Requested:**
        - Are these definitions clear and distinct?
        - Do these attributes comprehensively capture the dimensions necessary for assessing integration readiness?
        - Are there overlaps or areas needing further clarification?
        """
    )
    
    attr_choice = st.selectbox("Select an attribute to comment on (or 'General'):", ["General"] + PARENT_ATTRIBUTES)
    section_label = attr_choice if attr_choice != "General" else "GeneralAttributes"
    collect_feedback("Parent Attributes", section_label)
    
    st.markdown("#### Existing Feedback")
    parent_attr_feedback = get_feedback("Parent Attributes", section_label)
    display_feedback_entries(parent_attr_feedback)

def step_child_attributes():
    """
    Step 4: Child Attributes
    """
    st.title("Step 4: Child Attributes")
    st.markdown(
        """
        Each parent attribute can be further detailed into **child attributes** or **features**, 
        depending on the **method category**. This allows for a granular assessment of each 
        dimension.
        
        **Example Structure:**
        - **Simulations** ? **Maturity** ? "Validation Level," "Numerical Stability," etc.
        
        **Your Task:**
        1. **Select** a Method Category and a Parent Attribute.
        2. **Choose** a specific Child Attribute to provide feedback on.
        3. **Submit** your feedback for that specific attribute.
        
        **Note:** All child attributes are predefined based on the current IRL framework.
        """
    )
    
    # Select Method Category and Parent Attribute
    col1, col2 = st.columns(2)
    with col1:
        cat_choice = st.selectbox("Method Category:", METHOD_CATEGORIES, key="child_cat")
    with col2:
        attr_choice = st.selectbox("Parent Attribute:", PARENT_ATTRIBUTES, key="child_attr")
    
    # Retrieve all child attributes for the selected category and parent attribute
    child_attrs = []
    if cat_choice in CHILD_ATTRIBUTES_DICT and attr_choice in CHILD_ATTRIBUTES_DICT[cat_choice]:
        child_attrs = CHILD_ATTRIBUTES_DICT[cat_choice][attr_choice]
    
    if not child_attrs:
        st.info("No predefined child attributes for this combination.")
        child_feat_choice = "General"
        child_description = ""
        child_scoring = ""
    else:
        # Allow user to select a specific child attribute or "General"
        child_feat_options = [f[0] for f in child_attrs]
        child_feat_choice = st.selectbox("Select a Child Attribute to comment on:", ["General"] + child_feat_options, key="child_feat")
        
        if child_feat_choice != "General":
            # Retrieve description and scoring range for the selected child attribute
            selected_child = next((f for f in child_attrs if f[0] == child_feat_choice), None)
            if selected_child:
                child_description = selected_child[1]
                child_scoring = selected_child[2]
            else:
                child_description = ""
                child_scoring = ""
        else:
            child_description = ""
            child_scoring = ""
    
    # Display description and scoring range if not "General"
    if child_feat_choice != "General":
        st.markdown(f"**Description:** {child_description}")
        st.markdown(f"**Scoring Range:** {child_scoring}")
    
    # Define the section label based on selections
    section_label = f"{cat_choice} | {attr_choice} | {child_feat_choice}"
    
    # Collect feedback for the selected child attribute
    collect_feedback("Child Attributes", section_label)
    
    st.markdown("#### Existing Feedback")
    child_attr_feedback = get_feedback("Child Attributes", section_label)
    display_feedback_entries(child_attr_feedback)

def step_final_comments():
    """
    Step 5: Final Comments
    """
    st.title("Step 5: Final Comments & Recommendations")
    st.markdown(
        """
        **Thank you** for participating in the IRL Framework Co-Creation Wizard.
        
        This final step is an opportunity to provide any overarching remarks, suggestions, 
        or recommendations regarding:
        - Weighting of parent attributes
        - Refinement of scoring scales
        - Inclusion of case studies or examples
        - Next steps in finalizing the IRL framework
        - Any other insights to enhance the framework's robustness and applicability
        
        **Please share your concluding thoughts below:**
        """
    )
    
    section_label = "OverallFinal"
    collect_feedback("Final Comments", section_label)
    
    st.markdown("#### Existing Feedback")
    final_comments = get_feedback("Final Comments", section_label)
    display_feedback_entries(final_comments)
    
    st.success("Your participation is greatly appreciated. Thank you for contributing to the development of the IRL framework!")

###############################
# 5) WIZARD NAVIGATION
###############################

def wizard_navbar():
    """
    Renders the wizard navigation bar with Previous and Next buttons.
    """
    total_steps = len(WIZARD_STEPS)
    current_step = st.session_state.get("current_step", 0)
    step_name = WIZARD_STEPS[current_step]
    
    st.write(f"**Progress**: Step {current_step + 1}/{total_steps} — *{step_name}*")
    st.markdown("---")
    
    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("Previous", disabled=(current_step == 0)):
            st.session_state["current_step"] = max(current_step - 1, 0)
            st.session_state["_refresh_flag"] = not st.session_state["_refresh_flag"]
    with col2:
        if st.button("Next", disabled=(current_step == total_steps - 1)):
            st.session_state["current_step"] = min(current_step + 1, total_steps - 1)
            st.session_state["_refresh_flag"] = not st.session_state["_refresh_flag"]
    
    st.markdown("---")

def render_current_step():
    """
    Renders the content for the current step based on session state.
    """
    current_step = st.session_state["current_step"]
    step_name = WIZARD_STEPS[current_step]
    
    if step_name == "Introduction":
        step_introduction()
    elif step_name == "Method Categories":
        step_method_categories()
    elif step_name == "Parent Attributes":
        step_parent_attributes()
    elif step_name == "Child Attributes":
        step_child_attributes()
    elif step_name == "Final Comments":
        step_final_comments()

###############################
# 6) LOGIN PAGE
###############################

def login_page():
    """
    Displays the login page requiring passcode and optional username.
    """
    st.title("IRL Co-Creation - Secure Login")
    passcode = st.text_input("Enter Passcode:", type="password")
    user_name = st.text_input("Enter Your Name (Optional):", value="")
    
    if st.button("Login"):
        if passcode == PASSCODE:
            st.session_state["logged_in"] = True
            st.session_state["current_step"] = 0
            # Generate a unique user session ID
            st.session_state["user_id"] = str(uuid.uuid4())
            st.session_state["user_name"] = user_name.strip() if user_name.strip() else "Anonymous"
            st.session_state["_refresh_flag"] = not st.session_state["_refresh_flag"]  # Trigger refresh
        else:
            st.error("Incorrect passcode. Please try again.")

###############################
# 7) MAIN APP FUNCTION
###############################

def main():
    """
    The main function to run the Streamlit app.
    """
    # Initialize the database
    init_db()
    
    # Initialize session state variables if they don't exist
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = ""
    if "user_name" not in st.session_state:
        st.session_state["user_name"] = ""
    if "current_step" not in st.session_state:
        st.session_state["current_step"] = 0
    if "_refresh_flag" not in st.session_state:
        st.session_state["_refresh_flag"] = False
    
    # Display login or wizard based on session state
    if not st.session_state["logged_in"]:
        login_page()
    else:
        wizard_navbar()
        render_current_step()
    
    # Footer
    st.markdown("---")
    st.write("Powered by Streamlit.")
    st.write(
        "For more information, contact your project administrator or refer to the IRL framework documentation."
    )

if __name__ == "__main__":
    main()
