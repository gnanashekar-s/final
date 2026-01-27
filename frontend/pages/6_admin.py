"""Admin page for Streamlit."""
import streamlit as st

from components.auth import api_request, check_authentication

st.set_page_config(page_title="Admin", page_icon="⚙️", layout="wide")

if not check_authentication():
    st.warning("Please login to access this page")
    st.stop()

# Check admin role
user = st.session_state.get("user", {})
if user.get("role") != "admin":
    st.error("Admin access required")
    st.stop()

st.markdown("## Admin Dashboard")


def load_stats():
    """Load system statistics."""
    success, result = api_request("GET", "/admin/stats")
    if success:
        return result
    return None


def load_users(page: int = 1, page_size: int = 20):
    """Load users."""
    success, result = api_request(
        "GET",
        "/admin/users",
        params={"page": page, "page_size": page_size},
    )
    if success:
        return result
    return {"items": [], "total": 0}


def load_all_projects(page: int = 1, page_size: int = 20):
    """Load all projects."""
    success, result = api_request(
        "GET",
        "/admin/projects",
        params={"page": page, "page_size": page_size},
    )
    if success:
        return result
    return {"items": [], "total": 0}


def promote_user(user_id: int):
    """Promote user to admin."""
    success, result = api_request("POST", f"/admin/users/{user_id}/promote")
    if success:
        st.success("User promoted to admin!")
        return result
    else:
        st.error(result)
        return None


def demote_user(user_id: int):
    """Demote admin to user."""
    success, result = api_request("POST", f"/admin/users/{user_id}/demote")
    if success:
        st.success("User demoted!")
        return result
    else:
        st.error(result)
        return None


def delete_user(user_id: int):
    """Delete a user."""
    success, result = api_request("DELETE", f"/admin/users/{user_id}")
    if success:
        st.success("User deleted!")
        return True
    else:
        st.error(result)
        return False


# System Statistics
st.markdown("### System Statistics")

stats = load_stats()

if stats:
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### Users")
        st.metric("Total Users", stats.get("users", {}).get("total", 0))

    with col2:
        st.markdown("#### Projects")
        project_stats = stats.get("projects", {})
        total_projects = sum(project_stats.values())
        st.metric("Total Projects", total_projects)

        with st.expander("By Status"):
            for status, count in project_stats.items():
                st.markdown(f"- **{status}:** {count}")

    with col3:
        st.markdown("#### Runs")
        run_stats = stats.get("runs", {})
        total_runs = sum(run_stats.values())
        st.metric("Total Runs", total_runs)

        with st.expander("By Status"):
            for status, count in run_stats.items():
                st.markdown(f"- **{status}:** {count}")

    # Artifacts breakdown
    st.markdown("#### Artifacts")
    artifact_stats = stats.get("artifacts", {})
    cols = st.columns(4)
    with cols[0]:
        st.metric("Epics", artifact_stats.get("epics", 0))
    with cols[1]:
        st.metric("Stories", artifact_stats.get("stories", 0))
    with cols[2]:
        st.metric("Specs", artifact_stats.get("specs", 0))
    with cols[3]:
        st.metric("Code Artifacts", artifact_stats.get("code_artifacts", 0))

else:
    st.error("Failed to load statistics")

st.divider()

# Tabs for different admin sections
tab1, tab2 = st.tabs(["Users", "All Projects"])

with tab1:
    st.markdown("### User Management")

    users_data = load_users()
    users = users_data.get("items", [])

    if users:
        for user_item in users:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

                with col1:
                    role_icon = "👑" if user_item.get("role") == "admin" else "👤"
                    st.markdown(f"**{role_icon} {user_item.get('email', 'Unknown')}**")
                    st.caption(f"ID: {user_item.get('id')} | Projects: {user_item.get('project_count', 0)}")

                with col2:
                    st.markdown(f"**{user_item.get('role', 'user')}**")

                with col3:
                    if user_item.get("role") == "user":
                        if st.button("Promote", key=f"promote_{user_item['id']}"):
                            promote_user(user_item["id"])
                            st.rerun()
                    elif user_item.get("role") == "admin" and user_item.get("id") != user.get("id"):
                        if st.button("Demote", key=f"demote_{user_item['id']}"):
                            demote_user(user_item["id"])
                            st.rerun()

                with col4:
                    if user_item.get("id") != user.get("id"):
                        if st.button("Delete", key=f"delete_{user_item['id']}", type="secondary"):
                            if delete_user(user_item["id"]):
                                st.rerun()

                st.divider()
    else:
        st.info("No users found")

with tab2:
    st.markdown("### All Projects")

    projects_data = load_all_projects()
    projects = projects_data.get("items", [])

    if projects:
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.selectbox(
                "Filter by Status",
                ["All", "draft", "in_progress", "completed", "failed"],
                key="project_status_filter",
            )

        # Display projects
        filtered_projects = projects
        if status_filter != "All":
            filtered_projects = [p for p in projects if p.get("status") == status_filter]

        for project in filtered_projects:
            with st.container():
                col1, col2, col3 = st.columns([4, 2, 1])

                with col1:
                    st.markdown(f"**{project.get('name', 'Unknown')}**")
                    st.caption(
                        f"ID: {project.get('id')} | "
                        f"User: {project.get('user_email', 'Unknown')}"
                    )

                with col2:
                    status = project.get("status", "draft")
                    status_icon = {
                        "draft": "⚪",
                        "in_progress": "🔄",
                        "completed": "✅",
                        "failed": "❌",
                    }.get(status, "⚪")
                    st.markdown(f"{status_icon} {status}")

                with col3:
                    st.caption(project.get("created_at", "")[:10])

                st.divider()
    else:
        st.info("No projects found")

# System Health
st.divider()
st.markdown("### System Health")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### Backend API")
    success, _ = api_request("GET", "/../health")
    if success:
        st.success("✓ Healthy")
    else:
        st.error("✗ Unhealthy")

with col2:
    st.markdown("#### Database")
    # If we can load stats, DB is working
    if stats:
        st.success("✓ Connected")
    else:
        st.error("✗ Connection Error")

with col3:
    st.markdown("#### Langfuse")
    st.info("ℹ️ Check dashboard")
    st.markdown("[Open Langfuse Dashboard](https://cloud.langfuse.com)")
