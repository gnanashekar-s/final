"""Projects page for Streamlit."""
import streamlit as st

from components.auth import api_request, check_authentication

st.set_page_config(page_title="Projects", page_icon="📁", layout="wide")

if not check_authentication():
    st.warning("Please login to access this page")
    st.stop()

st.markdown("## Projects")


def load_projects():
    """Load projects from API."""
    success, result = api_request("GET", "/projects")
    if success:
        return result.get("items", [])
    else:
        st.error(result)
        return []


def create_project(name: str, product_request: str):
    """Create a new project."""
    success, result = api_request(
        "POST",
        "/projects",
        data={"name": name, "product_request": product_request},
    )
    if success:
        st.success("Project created successfully!")
        return result
    else:
        st.error(result)
        return None


def start_workflow(project_id: int, constraints: str = None):
    """Start a workflow for a project."""
    success, result = api_request(
        "POST",
        f"/projects/{project_id}/runs",
    )
    if success:
        st.success("Workflow started!")
        return result
    else:
        st.error(result)
        return None


# Create new project
with st.expander("Create New Project", expanded=False):
    with st.form("create_project"):
        name = st.text_input("Project Name")
        product_request = st.text_area(
            "Product Request",
            height=200,
            placeholder="Describe the product you want to build...",
        )
        constraints = st.text_area(
            "Constraints (optional)",
            height=100,
            placeholder="Any specific constraints or requirements...",
        )

        if st.form_submit_button("Create Project", type="primary"):
            if name and product_request:
                project = create_project(name, product_request)
                if project:
                    st.session_state["selected_project"] = project
                    st.rerun()
            else:
                st.error("Please fill in project name and product request")

st.divider()

# List projects
st.markdown("### Your Projects")

projects = load_projects()

if not projects:
    st.info("No projects yet. Create your first project above!")
else:
    for project in projects:
        with st.container():
            col1, col2, col3 = st.columns([4, 2, 2])

            with col1:
                st.markdown(f"**{project['name']}**")
                st.caption(f"ID: {project['id']} | Status: {project['status']}")

            with col2:
                status = project["status"]
                if status == "draft":
                    st.markdown("⚪ Draft")
                elif status == "in_progress":
                    st.markdown("🔄 In Progress")
                elif status == "completed":
                    st.markdown("✅ Completed")
                elif status == "failed":
                    st.markdown("❌ Failed")

            with col3:
                if st.button("View", key=f"view_{project['id']}"):
                    st.session_state["selected_project"] = project
                    st.rerun()

            st.divider()

# Project details
if "selected_project" in st.session_state:
    project = st.session_state["selected_project"]

    st.markdown(f"## Project: {project['name']}")

    tab1, tab2, tab3 = st.tabs(["Details", "Runs", "Artifacts"])

    with tab1:
        st.markdown("### Product Request")
        st.text_area(
            "Product Request",
            value=project.get("product_request", ""),
            disabled=True,
            height=200,
            label_visibility="collapsed",
        )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Status:** {project['status']}")
            st.markdown(f"**Created:** {project.get('created_at', 'N/A')}")
        with col2:
            if project["status"] == "draft":
                if st.button("Start Workflow", type="primary"):
                    run = start_workflow(project["id"])
                    if run:
                        st.session_state["current_run"] = run
                        st.rerun()

    with tab2:
        st.markdown("### Workflow Runs")
        success, runs_data = api_request("GET", f"/projects/{project['id']}/runs")
        if success:
            runs = runs_data if isinstance(runs_data, list) else []
            if runs:
                for run in runs:
                    with st.container():
                        col1, col2, col3 = st.columns([3, 2, 2])
                        with col1:
                            st.markdown(f"**Run #{run['id']}**")
                            st.caption(f"Stage: {run.get('current_stage', 'N/A')}")
                        with col2:
                            st.markdown(f"Status: {run['status']}")
                        with col3:
                            if st.button("Monitor", key=f"monitor_{run['id']}"):
                                st.session_state["current_run"] = run
                        st.divider()
            else:
                st.info("No runs yet")

    with tab3:
        st.markdown("### Generated Artifacts")
        st.info("View generated epics, stories, specs, and code in their respective pages")
