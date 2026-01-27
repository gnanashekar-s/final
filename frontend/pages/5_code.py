"""Code page for Streamlit."""
import streamlit as st

from components.auth import api_request, check_authentication

st.set_page_config(page_title="Code", page_icon="💻", layout="wide")

if not check_authentication():
    st.warning("Please login to access this page")
    st.stop()

st.markdown("## Generated Code")


def load_code_artifacts(spec_id: int = None):
    """Load code artifacts from API."""
    params = {}
    if spec_id:
        params["spec_id"] = spec_id

    success, result = api_request("GET", "/code", params=params)
    if success:
        return result.get("items", [])
    return []


def get_validation_report(artifact_id: int):
    """Get validation report for an artifact."""
    success, result = api_request("GET", f"/code/{artifact_id}/validation-report")
    if success:
        return result
    return None


def download_code(artifact_id: int):
    """Get download URL for code artifact."""
    # This would typically return a download link
    return f"/api/v1/code/{artifact_id}/export"


# Sidebar filters
with st.sidebar:
    st.markdown("### Filters")

    # Spec filter
    success, specs_data = api_request("GET", "/specs")
    spec_options = ["All Specs"]
    spec_map = {}
    if success:
        for s in specs_data.get("items", []):
            spec_options.append(f"Spec #{s['id']}")
            spec_map[f"Spec #{s['id']}"] = s["id"]

    selected_spec = st.selectbox("Spec", spec_options)
    spec_id = spec_map.get(selected_spec)

    # Status filter
    status_filter = st.selectbox(
        "Status",
        ["All", "draft", "validating", "valid", "invalid", "fixing"],
    )

# Load artifacts
artifacts = load_code_artifacts(spec_id)

if status_filter != "All":
    artifacts = [a for a in artifacts if a.get("status") == status_filter]

# Summary
if artifacts:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Artifacts", len(artifacts))
    with col2:
        valid_count = len([a for a in artifacts if a.get("status") == "valid"])
        st.metric("Valid", valid_count)
    with col3:
        invalid_count = len([a for a in artifacts if a.get("status") == "invalid"])
        st.metric("Invalid", invalid_count)
    with col4:
        total_files = sum(len(a.get("files", {})) for a in artifacts)
        st.metric("Total Files", total_files)

st.divider()

# Code artifacts list
st.markdown("### Code Artifacts")

if not artifacts:
    st.info("No code artifacts found. Generate code from approved specs.")
else:
    for artifact in artifacts:
        with st.container():
            status_icon = {
                "draft": "⚪",
                "validating": "🔄",
                "valid": "✅",
                "invalid": "❌",
                "fixing": "🔧",
            }.get(artifact.get("status", "draft"), "⚪")

            col1, col2, col3 = st.columns([4, 1, 1])

            with col1:
                st.markdown(
                    f"### {status_icon} Code Artifact #{artifact['id']} "
                    f"(Spec: {artifact.get('spec_id', 'N/A')})"
                )

            with col2:
                st.markdown(f"**v{artifact.get('version', 1)}**")
                st.caption(f"Fix attempts: {artifact.get('fix_attempts', 0)}")

            with col3:
                if artifact.get("status") == "valid":
                    if st.button("Download", key=f"download_{artifact['id']}"):
                        st.markdown(
                            f"[Download ZIP]({download_code(artifact['id'])})"
                        )

            # Tabs for code and validation
            tab1, tab2 = st.tabs(["Files", "Validation"])

            with tab1:
                files = artifact.get("files", {})
                if files:
                    # File tree
                    file_list = sorted(files.keys())

                    selected_file = st.selectbox(
                        "Select File",
                        file_list,
                        key=f"file_select_{artifact['id']}",
                    )

                    if selected_file:
                        # Determine language for syntax highlighting
                        lang = "python"
                        if selected_file.endswith(".txt"):
                            lang = "text"
                        elif selected_file.endswith(".toml"):
                            lang = "toml"
                        elif selected_file.endswith(".json"):
                            lang = "json"
                        elif selected_file.endswith(".md"):
                            lang = "markdown"

                        st.code(files[selected_file], language=lang)

                    # File statistics
                    st.divider()
                    st.markdown("**File Statistics:**")

                    file_stats = []
                    for fname, content in files.items():
                        lines = len(content.split("\n"))
                        file_stats.append({
                            "File": fname,
                            "Lines": lines,
                            "Size": f"{len(content)} bytes",
                        })

                    st.dataframe(file_stats, use_container_width=True)
                else:
                    st.info("No files in this artifact")

            with tab2:
                report = get_validation_report(artifact["id"])

                if report:
                    st.markdown(f"**Status:** {report.get('status', 'N/A')}")
                    st.markdown(f"**Fix Attempts:** {report.get('fix_attempts', 0)}")

                    # Validation Report
                    if report.get("validation_report"):
                        st.markdown("### Validation Report")
                        st.json(report["validation_report"])

                    # Lint Results
                    if report.get("lint_results"):
                        st.markdown("### Lint Results")
                        lint_errors = report["lint_results"]
                        if lint_errors:
                            for error in lint_errors:
                                st.error(
                                    f"**{error.get('file', 'unknown')}:{error.get('line', 0)}** "
                                    f"[{error.get('code', 'ERR')}] {error.get('message', '')}"
                                )
                        else:
                            st.success("No lint errors!")

                    # Test Results
                    if report.get("test_results"):
                        st.markdown("### Test Results")
                        for test in report["test_results"]:
                            if test.get("passed"):
                                st.success(f"✓ {test.get('test_name', 'Test')}")
                            else:
                                st.error(
                                    f"✗ {test.get('test_name', 'Test')}: "
                                    f"{test.get('error_message', 'Failed')}"
                                )

                    # Error Log
                    if report.get("error_log"):
                        st.markdown("### Error Log")
                        st.code(report["error_log"])
                else:
                    st.info("No validation report available")

            st.divider()

# Export all code section
st.markdown("### Export All Code")

valid_artifacts = [a for a in artifacts if a.get("status") == "valid"]
if valid_artifacts:
    st.markdown(f"**{len(valid_artifacts)} valid artifact(s) available for export**")

    if st.button("Export All Valid Artifacts"):
        for artifact in valid_artifacts:
            st.markdown(f"- [Download Artifact #{artifact['id']}]({download_code(artifact['id'])})")
else:
    st.info("No valid code artifacts available for export")
