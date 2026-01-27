"""Authentication components for Streamlit."""
import requests
import streamlit as st

# API base URL - should be configured via environment
API_URL = "http://localhost:8000/api/v1"


def check_authentication() -> bool:
    """Check if the user is authenticated."""
    return st.session_state.get("authenticated", False)


def show_login_page():
    """Show the login/register page."""
    st.markdown('<p class="main-header">Product-to-Code System</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Transform product requirements into working code</p>',
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        show_login_form()

    with tab2:
        show_register_form()


def show_login_form():
    """Show the login form."""
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password")
                return

            success, result = login(email, password)
            if success:
                st.session_state.authenticated = True
                st.session_state.token = result["access_token"]
                # Get user info
                user_info = get_current_user(result["access_token"])
                if user_info:
                    st.session_state.user = user_info
                st.success("Login successful!")
                st.rerun()
            else:
                st.error(result)


def show_register_form():
    """Show the registration form."""
    with st.form("register_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Register", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please fill in all fields")
                return

            if password != confirm_password:
                st.error("Passwords do not match")
                return

            if len(password) < 8:
                st.error("Password must be at least 8 characters")
                return

            success, result = register(email, password)
            if success:
                st.success("Registration successful! Please login.")
            else:
                st.error(result)


def login(email: str, password: str) -> tuple[bool, dict | str]:
    """Login and get access token."""
    try:
        response = requests.post(
            f"{API_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=10,
        )

        if response.status_code == 200:
            return True, response.json()
        else:
            error = response.json().get("detail", "Login failed")
            return False, error
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to server. Please ensure the backend is running."
    except Exception as e:
        return False, str(e)


def register(email: str, password: str) -> tuple[bool, dict | str]:
    """Register a new user."""
    try:
        response = requests.post(
            f"{API_URL}/auth/register",
            json={"email": email, "password": password},
            timeout=10,
        )

        if response.status_code == 201:
            return True, response.json()
        else:
            error = response.json().get("detail", "Registration failed")
            return False, error
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to server. Please ensure the backend is running."
    except Exception as e:
        return False, str(e)


def get_current_user(token: str) -> dict | None:
    """Get current user information."""
    try:
        response = requests.get(
            f"{API_URL}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )

        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


def get_auth_header() -> dict:
    """Get authorization header for API requests."""
    token = st.session_state.get("token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def api_request(
    method: str,
    endpoint: str,
    data: dict | None = None,
    params: dict | None = None,
) -> tuple[bool, dict | str]:
    """Make an authenticated API request."""
    try:
        url = f"{API_URL}{endpoint}"
        headers = get_auth_header()

        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            return False, f"Unsupported method: {method}"

        if response.status_code in [200, 201]:
            return True, response.json()
        elif response.status_code == 401:
            # Token expired, logout
            st.session_state.authenticated = False
            st.session_state.token = None
            st.session_state.user = None
            return False, "Session expired. Please login again."
        else:
            error = response.json().get("detail", "Request failed")
            return False, error

    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to server"
    except Exception as e:
        return False, str(e)
