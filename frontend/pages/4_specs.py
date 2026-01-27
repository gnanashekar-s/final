"""Specs page for Streamlit."""
import streamlit as st

from components.auth import api_request, check_authentication
from components.chat import render_approval_interface
from components.mermaid import render_mermaid_with_fallback

st.set_page_config(page_title="Specs", page_icon="📝", layout="wide")

if not check_authentication():
    st.warning("Please login to access this page")
    st.stop()

st.markdown("## Technical Specifications")


def load_specs(story_id: int = None):
    """Load specs from API."""
    params = {}
    if story_id:
        params["story_id"] = story_id

    success, result = api_request("GET", "/specs", params=params)
    if success:
        return result.get("items", [])
    return []


def approve_spec(spec_id: int, approved: bool, feedback: str = None):
    """Approve or reject a spec."""
    success, result = api_request(
        "POST",
        f"/specs/{spec_id}/approve",
        data={"approved": approved, "feedback": feedback},
    )
    if success:
        st.success("Spec updated!")
        return result
    else:
        st.error(result)
        return None


def get_spec_diagrams(spec_id: int):
    """Get diagrams for a spec."""
    success, result = api_request("GET", f"/specs/{spec_id}/diagrams")
    if success:
        return result.get("diagrams", {})
    return {}


# Sidebar filters
with st.sidebar:
    st.markdown("### Filters")

    # Story filter
    success, stories_data = api_request("GET", "/stories")
    story_options = ["All Stories"]
    story_map = {}
    if success:
        for s in stories_data.get("items", []):
            story_options.append(s["title"][:50])
            story_map[s["title"][:50]] = s["id"]

    selected_story = st.selectbox("Story", story_options)
    story_id = story_map.get(selected_story)

    # Status filter
    status_filter = st.selectbox(
        "Status",
        ["All", "draft", "pending_review", "approved", "rejected"],
    )

# Load specs
specs = load_specs(story_id)

if status_filter != "All":
    specs = [s for s in specs if s.get("status") == status_filter]

# Pending approval section
pending_specs = [s for s in specs if s.get("status") == "pending_review"]
if pending_specs:
    st.markdown("### Pending Approval")

    def handle_approval(item_ids, approved, feedback):
        for idx in item_ids:
            spec = pending_specs[idx]
            approve_spec(spec["id"], approved, feedback)
        st.rerun()

    render_approval_interface("spec", pending_specs, handle_approval)

    st.divider()

# All specs list
st.markdown("### All Specifications")

if not specs:
    st.info("No specifications found. Generate specs from approved stories.")
else:
    for spec in specs:
        with st.container():
            status_icon = {
                "draft": "⚪",
                "pending_review": "🔔",
                "approved": "✅",
                "rejected": "❌",
            }.get(spec.get("status", "draft"), "⚪")

            col1, col2 = st.columns([5, 1])

            with col1:
                st.markdown(f"### {status_icon} Spec #{spec['id']} (Story: {spec.get('story_id', 'N/A')})")

            with col2:
                st.markdown(f"**v{spec.get('version', 1)}**")
                st.caption(spec.get("status", "draft"))

            # Tabs for different spec sections
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "Content", "API Design", "Data Model", "Security", "Diagrams"
            ])

            with tab1:
                st.markdown(spec.get("content", "No content available"))

                if spec.get("requirements"):
                    with st.expander("Requirements"):
                        st.json(spec["requirements"])

            with tab2:
                api_design = spec.get("api_design", {})
                if api_design:
                    endpoints = api_design.get("endpoints", [])
                    if endpoints:
                        for ep in endpoints:
                            method = ep.get("method", "GET")
                            path = ep.get("path", "/")
                            desc = ep.get("description", "")

                            method_color = {
                                "GET": "🟢",
                                "POST": "🔵",
                                "PUT": "🟡",
                                "DELETE": "🔴",
                            }.get(method, "⚪")

                            st.markdown(f"**{method_color} {method}** `{path}`")
                            st.caption(desc)

                            if ep.get("request_body"):
                                st.markdown("Request:")
                                st.json(ep["request_body"])
                            if ep.get("response"):
                                st.markdown("Response:")
                                st.json(ep["response"])
                            st.divider()
                    else:
                        st.info("No API endpoints defined")
                else:
                    st.info("No API design available")

            with tab3:
                data_model = spec.get("data_model", {})
                if data_model:
                    models = data_model.get("models", [])
                    if models:
                        for model in models:
                            st.markdown(f"**{model.get('name', 'Model')}**")
                            if model.get("fields"):
                                for field in model["fields"]:
                                    pk = "🔑" if field.get("primary_key") else ""
                                    nullable = "?" if field.get("nullable") else ""
                                    st.markdown(
                                        f"- `{field.get('name')}`: {field.get('type')}{pk}{nullable}"
                                    )
                            st.divider()
                    else:
                        st.info("No data models defined")
                else:
                    st.info("No data model available")

            with tab4:
                security = spec.get("security_requirements", {})
                if security:
                    st.json(security)
                else:
                    st.info("No security requirements defined")

            with tab5:
                diagrams = spec.get("mermaid_diagrams", {})
                if diagrams:
                    for name, diagram in diagrams.items():
                        st.markdown(f"**{name.replace('_', ' ').title()}**")
                        render_mermaid_with_fallback(diagram, height=300)
                else:
                    st.info("No diagrams available")

            # Feedback
            if spec.get("feedback"):
                st.warning(f"**Feedback:** {spec['feedback']}")

            # Action buttons
            if spec.get("status") == "pending_review":
                col_a, col_b, col_c = st.columns([2, 2, 4])
                with col_a:
                    if st.button("Approve", key=f"approve_{spec['id']}", type="primary"):
                        approve_spec(spec["id"], True)
                        st.rerun()
                with col_b:
                    feedback = st.text_input("Feedback", key=f"feedback_{spec['id']}")
                    if st.button("Reject", key=f"reject_{spec['id']}"):
                        approve_spec(spec["id"], False, feedback)
                        st.rerun()

            st.divider()
