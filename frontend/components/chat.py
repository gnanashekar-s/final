"""Chat component for workflow interactions."""
import streamlit as st
from typing import Callable, Optional


def render_chat_interface(
    messages: list[dict],
    on_send: Callable[[str], None],
    placeholder: str = "Type your message...",
    disabled: bool = False,
):
    """
    Render a chat interface.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        on_send: Callback function when user sends a message
        placeholder: Input placeholder text
        disabled: Whether the input is disabled
    """
    # Display messages
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")

        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
        elif role == "assistant":
            with st.chat_message("assistant"):
                st.markdown(content)
        elif role == "system":
            with st.chat_message("assistant", avatar="🔔"):
                st.info(content)

    # Input
    if not disabled:
        if prompt := st.chat_input(placeholder):
            on_send(prompt)


def render_approval_interface(
    item_type: str,
    items: list[dict],
    on_approve: Callable[[list[int], bool, Optional[str]], None],
):
    """
    Render an approval interface for epics, stories, or specs.

    Args:
        item_type: Type of items ('epic', 'story', 'spec')
        items: List of items to review
        on_approve: Callback function (item_ids, approved, feedback)
    """
    st.markdown(f"### Review {item_type.title()}s")
    st.markdown(f"Please review the following {item_type}s and approve or reject them.")

    # Track selections
    if f"selected_{item_type}s" not in st.session_state:
        st.session_state[f"selected_{item_type}s"] = set()

    # Select all / none buttons
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("Select All"):
            st.session_state[f"selected_{item_type}s"] = set(range(len(items)))
            st.rerun()
    with col2:
        if st.button("Clear Selection"):
            st.session_state[f"selected_{item_type}s"] = set()
            st.rerun()

    st.divider()

    # Display items
    for i, item in enumerate(items):
        col1, col2 = st.columns([1, 10])

        with col1:
            selected = st.checkbox(
                "Select",
                key=f"{item_type}_{i}_checkbox",
                value=i in st.session_state[f"selected_{item_type}s"],
                label_visibility="collapsed",
            )
            if selected:
                st.session_state[f"selected_{item_type}s"].add(i)
            elif i in st.session_state[f"selected_{item_type}s"]:
                st.session_state[f"selected_{item_type}s"].remove(i)

        with col2:
            with st.expander(f"**{item.get('title', f'{item_type.title()} {i+1}')}**", expanded=i == 0):
                # Display item details based on type
                if item_type == "epic":
                    st.markdown(f"**Goal:** {item.get('goal', 'N/A')}")
                    st.markdown(f"**Scope:** {item.get('scope', 'N/A')}")
                    st.markdown(f"**Priority:** {item.get('priority', 'medium')}")
                    if item.get("dependencies"):
                        st.markdown(f"**Dependencies:** {item.get('dependencies')}")

                elif item_type == "story":
                    st.markdown(f"**Description:** {item.get('description', 'N/A')}")
                    st.markdown(f"**Priority:** {item.get('priority', 'medium')}")
                    if item.get("story_points"):
                        st.markdown(f"**Story Points:** {item.get('story_points')}")
                    if item.get("acceptance_criteria"):
                        st.markdown("**Acceptance Criteria:**")
                        for ac in item.get("acceptance_criteria", []):
                            st.markdown(f"- Given: {ac.get('given', 'N/A')}")
                            st.markdown(f"  When: {ac.get('when', 'N/A')}")
                            st.markdown(f"  Then: {ac.get('then', 'N/A')}")
                    if item.get("edge_cases"):
                        st.markdown(f"**Edge Cases:** {', '.join(item.get('edge_cases', []))}")

                elif item_type == "spec":
                    st.markdown(item.get("content", "No content"))
                    if item.get("api_design"):
                        st.markdown("**API Design:**")
                        st.json(item.get("api_design"))
                    if item.get("data_model"):
                        st.markdown("**Data Model:**")
                        st.json(item.get("data_model"))

    st.divider()

    # Approval actions
    selected_count = len(st.session_state[f"selected_{item_type}s"])
    st.markdown(f"**{selected_count} item(s) selected**")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Approve Selected", type="primary", disabled=selected_count == 0):
            selected_ids = list(st.session_state[f"selected_{item_type}s"])
            on_approve(selected_ids, True, None)
            st.session_state[f"selected_{item_type}s"] = set()

    with col2:
        feedback = st.text_area("Feedback (for rejection)", key=f"{item_type}_feedback")
        if st.button("Reject Selected", disabled=selected_count == 0):
            selected_ids = list(st.session_state[f"selected_{item_type}s"])
            on_approve(selected_ids, False, feedback)
            st.session_state[f"selected_{item_type}s"] = set()


def render_progress_indicator(
    current_stage: str,
    stages: list[str],
    progress_percent: float = 0,
):
    """
    Render a workflow progress indicator.

    Args:
        current_stage: Current workflow stage
        stages: List of all stages
        progress_percent: Progress percentage within current stage
    """
    # Calculate overall progress
    try:
        current_idx = stages.index(current_stage)
        overall_progress = (current_idx + progress_percent / 100) / len(stages)
    except ValueError:
        overall_progress = 0

    st.progress(overall_progress, text=f"Stage: {current_stage}")

    # Stage indicators
    cols = st.columns(len(stages))
    for i, (col, stage) in enumerate(zip(cols, stages)):
        with col:
            if stages.index(current_stage) > i:
                st.markdown(f"✅ {stage}")
            elif stage == current_stage:
                st.markdown(f"🔄 **{stage}**")
            else:
                st.markdown(f"⏳ {stage}")
