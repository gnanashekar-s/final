"""Streamlit main application entry point."""
import streamlit as st

from components.auth import check_authentication, show_login_page

# Page configuration
st.set_page_config(
    page_title="Product-to-Code System",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .status-badge {
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
    }
    .status-pending { background-color: #ffeeba; color: #856404; }
    .status-approved { background-color: #c3e6cb; color: #155724; }
    .status-rejected { background-color: #f5c6cb; color: #721c24; }
    .status-completed { background-color: #bee5eb; color: #0c5460; }
</style>
""", unsafe_allow_html=True)


def main():
    """Main application entry point."""
    # Initialize session state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "token" not in st.session_state:
        st.session_state.token = None

    # Check authentication
    if not check_authentication():
        show_login_page()
        return

    # Show main application
    show_dashboard()


def show_dashboard():
    """Show the main dashboard."""
    # Sidebar
    with st.sidebar:
        st.markdown("### Product-to-Code")
        st.markdown(f"**User:** {st.session_state.user.get('email', 'Unknown')}")
        st.markdown(f"**Role:** {st.session_state.user.get('role', 'user')}")
        st.divider()

        # Navigation
        st.markdown("### Navigation")
        page = st.radio(
            "Go to",
            ["Dashboard", "Projects", "Epics", "Stories", "Specs", "Code", "Admin"],
            label_visibility="collapsed",
        )

        st.divider()

        if st.button("Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.token = None
            st.rerun()

    # Main content based on navigation
    if page == "Dashboard":
        show_dashboard_content()
    elif page == "Projects":
        st.switch_page("pages/1_projects.py")
    elif page == "Epics":
        st.switch_page("pages/2_epics.py")
    elif page == "Stories":
        st.switch_page("pages/3_stories.py")
    elif page == "Specs":
        st.switch_page("pages/4_specs.py")
    elif page == "Code":
        st.switch_page("pages/5_code.py")
    elif page == "Admin":
        if st.session_state.user.get("role") == "admin":
            st.switch_page("pages/6_admin.py")
        else:
            st.error("Admin access required")


def show_dashboard_content():
    """Show dashboard content."""
    st.markdown('<p class="main-header">Dashboard</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Welcome to the Product-to-Code Multi-Agent System</p>',
        unsafe_allow_html=True,
    )

    # Quick stats
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Projects", "0", help="Total number of projects")
    with col2:
        st.metric("Active Runs", "0", help="Currently running workflows")
    with col3:
        st.metric("Pending Approvals", "0", help="Items awaiting your review")
    with col4:
        st.metric("Completed", "0", help="Successfully completed projects")

    st.divider()

    # Quick actions
    st.markdown("### Quick Actions")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Create New Project")
        with st.form("quick_project"):
            name = st.text_input("Project Name")
            request = st.text_area("Product Request", height=100)
            submitted = st.form_submit_button("Create Project")

            if submitted and name and request:
                st.info("Navigate to Projects page to create a new project")

    with col2:
        st.markdown("#### Recent Activity")
        st.info("No recent activity")

    # Workflow overview
    st.divider()
    st.markdown("### Workflow Overview")
    st.markdown("""
    The Product-to-Code system transforms your product requirements into working FastAPI code through these stages:

    1. **Research** - Gathers relevant technical information
    2. **Epic Generation** - Creates high-level feature epics
    3. **Story Generation** - Breaks epics into user stories
    4. **Spec Generation** - Creates detailed technical specifications
    5. **Code Generation** - Generates FastAPI backend code
    6. **Validation** - Validates and tests the generated code
    """)

    # Mermaid diagram of workflow
    st.markdown("#### Workflow Diagram")
    st.code("""
graph LR
    A[Product Request] --> B[Research]
    B --> C[Epic Generation]
    C --> D{Epic Review}
    D -->|Approved| E[Story Generation]
    D -->|Rejected| C
    E --> F{Story Review}
    F -->|Approved| G[Spec Generation]
    F -->|Rejected| E
    G --> H{Spec Review}
    H -->|Approved| I[Code Generation]
    H -->|Rejected| G
    I --> J[Validation]
    J --> K{Valid?}
    K -->|Yes| L[Complete]
    K -->|No| M[Auto-Fix]
    M --> J
    """, language="mermaid")


if __name__ == "__main__":
    main()
