"""Stories page for Streamlit."""
import streamlit as st

from components.auth import api_request, check_authentication
from components.chat import render_approval_interface

st.set_page_config(page_title="Stories", page_icon="📖", layout="wide")

if not check_authentication():
    st.warning("Please login to access this page")
    st.stop()

st.markdown("## User Stories")


def load_stories(epic_id: int = None):
    """Load stories from API."""
    params = {}
    if epic_id:
        params["epic_id"] = epic_id

    success, result = api_request("GET", "/stories", params=params)
    if success:
        return result.get("items", [])
    return []


def approve_story(story_id: int, approved: bool, feedback: str = None):
    """Approve or reject a story."""
    success, result = api_request(
        "POST",
        f"/stories/{story_id}/approve",
        data={"approved": approved, "feedback": feedback},
    )
    if success:
        st.success("Story updated!")
        return result
    else:
        st.error(result)
        return None


# Sidebar filters
with st.sidebar:
    st.markdown("### Filters")

    # Epic filter
    success, epics_data = api_request("GET", "/epics")
    epic_options = ["All Epics"]
    epic_map = {}
    if success:
        for e in epics_data.get("items", []):
            epic_options.append(e["title"][:50])
            epic_map[e["title"][:50]] = e["id"]

    selected_epic = st.selectbox("Epic", epic_options)
    epic_id = epic_map.get(selected_epic)

    # Status filter
    status_filter = st.selectbox(
        "Status",
        ["All", "draft", "pending_review", "approved", "rejected"],
    )

# Load stories
stories = load_stories(epic_id)

if status_filter != "All":
    stories = [s for s in stories if s.get("status") == status_filter]

# Pending approval section
pending_stories = [s for s in stories if s.get("status") == "pending_review"]
if pending_stories:
    st.markdown("### Pending Approval")

    def handle_approval(item_ids, approved, feedback):
        for idx in item_ids:
            story = pending_stories[idx]
            approve_story(story["id"], approved, feedback)
        st.rerun()

    render_approval_interface("story", pending_stories, handle_approval)

    st.divider()

# Summary statistics
if stories:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Stories", len(stories))
    with col2:
        approved_count = len([s for s in stories if s.get("status") == "approved"])
        st.metric("Approved", approved_count)
    with col3:
        total_points = sum(s.get("story_points", 0) or 0 for s in stories)
        st.metric("Total Points", total_points)
    with col4:
        pending_count = len([s for s in stories if s.get("status") == "pending_review"])
        st.metric("Pending", pending_count)

st.divider()

# All stories list
st.markdown("### All Stories")

if not stories:
    st.info("No stories found. Generate stories from approved epics.")
else:
    for story in stories:
        with st.container():
            col1, col2 = st.columns([4, 1])

            with col1:
                status_icon = {
                    "draft": "⚪",
                    "pending_review": "🔔",
                    "approved": "✅",
                    "rejected": "❌",
                }.get(story.get("status", "draft"), "⚪")

                st.markdown(f"### {status_icon} {story['title']}")

                with st.expander("Details"):
                    st.markdown(f"**Description:** {story.get('description', 'N/A')}")
                    st.markdown(f"**Priority:** {story.get('priority', 'medium')}")

                    if story.get("story_points"):
                        st.markdown(f"**Story Points:** {story['story_points']}")

                    # Acceptance Criteria
                    if story.get("acceptance_criteria"):
                        st.markdown("**Acceptance Criteria:**")
                        for i, ac in enumerate(story["acceptance_criteria"], 1):
                            st.markdown(f"""
                            **Criterion {i}:**
                            - **Given:** {ac.get('given', 'N/A')}
                            - **When:** {ac.get('when', 'N/A')}
                            - **Then:** {ac.get('then', 'N/A')}
                            """)

                    # Edge Cases
                    if story.get("edge_cases"):
                        st.markdown("**Edge Cases:**")
                        for ec in story["edge_cases"]:
                            st.markdown(f"- {ec}")

                    if story.get("feedback"):
                        st.warning(f"**Feedback:** {story['feedback']}")

            with col2:
                st.markdown(f"**v{story.get('version', 1)}**")

                if story.get("story_points"):
                    st.metric("Points", story["story_points"])

                st.caption(story.get("status", "draft"))

                if story.get("status") == "pending_review":
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("✓", key=f"approve_{story['id']}", help="Approve"):
                            approve_story(story["id"], True)
                            st.rerun()
                    with col_b:
                        if st.button("✗", key=f"reject_{story['id']}", help="Reject"):
                            approve_story(story["id"], False, "Rejected from list view")
                            st.rerun()

            st.divider()
