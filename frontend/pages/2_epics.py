"""Epics page for Streamlit."""
import streamlit as st

from components.auth import api_request, check_authentication
from components.chat import render_approval_interface
from components.mermaid import render_mermaid_with_fallback

st.set_page_config(page_title="Epics", page_icon="📋", layout="wide")

if not check_authentication():
    st.warning("Please login to access this page")
    st.stop()

st.markdown("## Epics")


def load_epics(project_id: int = None):
    """Load epics from API."""
    params = {}
    if project_id:
        params["project_id"] = project_id

    success, result = api_request("GET", "/epics", params=params)
    if success:
        return result.get("items", [])
    return []


def approve_epic(epic_id: int, approved: bool, feedback: str = None):
    """Approve or reject an epic."""
    success, result = api_request(
        "POST",
        f"/epics/{epic_id}/approve",
        data={"approved": approved, "feedback": feedback},
    )
    if success:
        st.success("Epic updated!")
        return result
    else:
        st.error(result)
        return None


def get_dependency_graph(project_id: int):
    """Get epic dependency graph."""
    success, result = api_request("GET", f"/epics/project/{project_id}/dependency-graph")
    if success:
        return result
    return None


# Sidebar filters
with st.sidebar:
    st.markdown("### Filters")

    # Project filter
    success, projects = api_request("GET", "/projects")
    project_options = ["All Projects"]
    project_map = {}
    if success:
        for p in projects.get("items", []):
            project_options.append(p["name"])
            project_map[p["name"]] = p["id"]

    selected_project = st.selectbox("Project", project_options)
    project_id = project_map.get(selected_project)

    # Status filter
    status_filter = st.selectbox(
        "Status",
        ["All", "draft", "pending_review", "approved", "rejected"],
    )

# Load epics
epics = load_epics(project_id)

if status_filter != "All":
    epics = [e for e in epics if e.get("status") == status_filter]

# Display dependency graph if project selected
if project_id:
    with st.expander("Dependency Graph"):
        graph_data = get_dependency_graph(project_id)
        if graph_data and graph_data.get("mermaid"):
            render_mermaid_with_fallback(graph_data["mermaid"])
        else:
            st.info("No dependency graph available")

st.divider()

# Pending approval section
pending_epics = [e for e in epics if e.get("status") == "pending_review"]
if pending_epics:
    st.markdown("### Pending Approval")

    def handle_approval(item_ids, approved, feedback):
        for idx in item_ids:
            epic = pending_epics[idx]
            approve_epic(epic["id"], approved, feedback)
        st.rerun()

    render_approval_interface("epic", pending_epics, handle_approval)

    st.divider()

# All epics list
st.markdown("### All Epics")

if not epics:
    st.info("No epics found. Start a workflow to generate epics.")
else:
    for epic in epics:
        with st.container():
            col1, col2 = st.columns([4, 1])

            with col1:
                status_icon = {
                    "draft": "⚪",
                    "pending_review": "🔔",
                    "approved": "✅",
                    "rejected": "❌",
                }.get(epic.get("status", "draft"), "⚪")

                st.markdown(f"### {status_icon} {epic['title']}")

                with st.expander("Details"):
                    st.markdown(f"**Goal:** {epic.get('goal', 'N/A')}")
                    st.markdown(f"**Scope:** {epic.get('scope', 'N/A')}")
                    st.markdown(f"**Priority:** {epic.get('priority', 'medium')}")

                    if epic.get("dependencies"):
                        st.markdown(f"**Dependencies:** Epic IDs {epic['dependencies']}")

                    if epic.get("feedback"):
                        st.warning(f"**Feedback:** {epic['feedback']}")

                    if epic.get("mermaid_diagram"):
                        st.markdown("**Diagram:**")
                        render_mermaid_with_fallback(epic["mermaid_diagram"], height=200)

            with col2:
                st.markdown(f"**v{epic.get('version', 1)}**")
                st.caption(epic.get("status", "draft"))

                if epic.get("status") == "pending_review":
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("✓", key=f"approve_{epic['id']}", help="Approve"):
                            approve_epic(epic["id"], True)
                            st.rerun()
                    with col_b:
                        if st.button("✗", key=f"reject_{epic['id']}", help="Reject"):
                            approve_epic(epic["id"], False, "Rejected from list view")
                            st.rerun()

            st.divider()
