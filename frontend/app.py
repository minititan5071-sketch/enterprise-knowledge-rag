import os
from typing import Any

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(page_title="Enterprise Knowledge RAG", page_icon=None, layout="wide")


def api_request(
    method: str,
    path: str,
    token: str | None = None,
    **kwargs: Any,
) -> Any:
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.request(
        method,
        f"{BACKEND_URL}{path}",
        headers=headers,
        timeout=60,
        **kwargs,
    )
    if response.status_code >= 400:
        detail = response.text
        try:
            detail = response.json().get("detail", detail)
        except Exception:
            pass
        raise RuntimeError(detail)
    if not response.content:
        return None
    return response.json()


def token() -> str | None:
    return st.session_state.get("token")


def selected_workspace() -> dict | None:
    return st.session_state.get("workspace")


def require_workspace() -> dict | None:
    workspace = selected_workspace()
    if not workspace:
        st.info("Select a workspace from the sidebar.")
        return None
    return workspace


def login_screen() -> None:
    st.title("Enterprise Knowledge RAG")
    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
        if submitted:
            try:
                result = api_request(
                    "POST",
                    "/auth/login",
                    json={"email": email, "password": password},
                )
                st.session_state.token = result["access_token"]
                st.session_state.user = result["user"]
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    with register_tab:
        with st.form("register_form"):
            full_name = st.text_input("Full name")
            email = st.text_input("Work email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Create account", use_container_width=True)
        if submitted:
            try:
                api_request(
                    "POST",
                    "/auth/register",
                    json={"email": email, "password": password, "full_name": full_name or None},
                )
                st.success("Account created. You can log in now.")
            except Exception as exc:
                st.error(str(exc))


def load_workspaces() -> list[dict]:
    try:
        return api_request("GET", "/workspaces", token=token())
    except Exception as exc:
        st.error(str(exc))
        return []


def sidebar() -> str:
    user = st.session_state.get("user", {})
    st.sidebar.subheader(user.get("email", "Signed in"))
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    workspaces = load_workspaces()
    workspace_names = [f"{workspace['name']} ({workspace['role']})" for workspace in workspaces]
    if workspace_names:
        current_id = selected_workspace().get("id") if selected_workspace() else None
        default_index = 0
        for index, workspace in enumerate(workspaces):
            if workspace["id"] == current_id:
                default_index = index
                break
        choice = st.sidebar.selectbox("Workspace", workspace_names, index=default_index)
        st.session_state.workspace = workspaces[workspace_names.index(choice)]
    else:
        st.sidebar.info("Create a workspace to begin.")

    return st.sidebar.radio(
        "Navigation",
        [
            "Workspaces",
            "Documents",
            "Ask",
            "Query History",
            "Feedback",
            "Evaluation",
        ],
    )


def workspace_page() -> None:
    st.header("Workspaces")
    left, right = st.columns([1, 2])
    with left:
        st.subheader("Create Workspace")
        with st.form("workspace_create"):
            name = st.text_input("Name")
            description = st.text_area("Description")
            submitted = st.form_submit_button("Create", use_container_width=True)
        if submitted:
            try:
                workspace = api_request(
                    "POST",
                    "/workspaces",
                    token=token(),
                    json={"name": name, "description": description or None},
                )
                st.session_state.workspace = workspace
                st.success("Workspace created.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    with right:
        st.subheader("Membership")
        workspace = require_workspace()
        if workspace:
            st.write(f"Active workspace: **{workspace['name']}**")
            with st.form("add_member"):
                email = st.text_input("User email")
                role = st.selectbox("Role", ["viewer", "manager", "admin"])
                submitted = st.form_submit_button("Add or update member")
            if submitted:
                try:
                    api_request(
                        "POST",
                        f"/workspaces/{workspace['id']}/members",
                        token=token(),
                        json={"email": email, "role": role},
                    )
                    st.success("Membership updated.")
                except Exception as exc:
                    st.error(str(exc))


def documents_page() -> None:
    workspace = require_workspace()
    if not workspace:
        return
    st.header("Documents")
    with st.form("document_upload"):
        upload = st.file_uploader("Upload PDF, TXT, MD, or DOCX", type=["pdf", "txt", "md", "docx"])
        submitted = st.form_submit_button("Upload")
    if submitted and upload:
        try:
            files = {"file": (upload.name, upload.getvalue(), upload.type)}
            data = {"workspace_id": workspace["id"]}
            result = api_request(
                "POST",
                "/documents/upload",
                token=token(),
                files=files,
                data=data,
            )
            st.success(f"Queued ingestion: {result['document']['filename']}")
        except Exception as exc:
            st.error(str(exc))

    try:
        documents = api_request(
            "GET",
            "/documents",
            token=token(),
            params={"workspace_id": workspace["id"]},
        )
        st.dataframe(documents, use_container_width=True, hide_index=True)
    except Exception as exc:
        st.error(str(exc))


def ask_page() -> None:
    workspace = require_workspace()
    if not workspace:
        return
    st.header("Ask")
    with st.form("ask_form"):
        question = st.text_area("Question", height=110)
        top_k = st.slider("Top K", 1, 20, 5)
        submitted = st.form_submit_button("Ask")
    if submitted:
        try:
            result = api_request(
                "POST",
                "/query",
                token=token(),
                json={"workspace_id": workspace["id"], "question": question, "top_k": top_k},
            )
            st.session_state.last_answer = result
            st.session_state.last_question = question
        except Exception as exc:
            st.error(str(exc))

    result = st.session_state.get("last_answer")
    if result:
        st.subheader("Answer")
        st.write(result["answer"])
        metrics = st.columns(3)
        metrics[0].metric("Confidence", f"{result['confidence_score']:.2f}")
        metrics[1].metric("Citations", len(result["citations"]))
        metrics[2].metric("Model", result["model_name"])

        st.subheader("Citations")
        for citation in result["citations"]:
            label = citation["filename"]
            if citation.get("page_number"):
                label += f" page {citation['page_number']}"
            with st.expander(label):
                st.caption(f"Score {citation['score']:.3f}, chunk {citation['chunk_index']}")
                st.write(citation["snippet"])

        st.subheader("Feedback")
        cols = st.columns(3)
        for rating, col in zip(["helpful", "wrong", "unsafe"], cols, strict=True):
            if col.button(rating.title(), use_container_width=True):
                try:
                    api_request(
                        "POST",
                        "/feedback",
                        token=token(),
                        json={
                            "workspace_id": workspace["id"],
                            "audit_log_id": result["audit_log_id"],
                            "question": st.session_state.get("last_question"),
                            "answer": result["answer"],
                            "rating": rating,
                        },
                    )
                    st.success("Feedback recorded.")
                except Exception as exc:
                    st.error(str(exc))


def history_page() -> None:
    workspace = require_workspace()
    if not workspace:
        return
    st.header("Query History")
    try:
        rows = api_request(
            "GET",
            "/audit-logs",
            token=token(),
            params={"workspace_id": workspace["id"], "limit": 200},
        )
        st.dataframe(rows, use_container_width=True, hide_index=True)
    except Exception as exc:
        st.error(str(exc))


def feedback_page() -> None:
    workspace = require_workspace()
    if not workspace:
        return
    st.header("Feedback")
    try:
        rows = api_request(
            "GET",
            "/feedback",
            token=token(),
            params={"workspace_id": workspace["id"], "limit": 200},
        )
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No feedback has been recorded.")
    except Exception as exc:
        st.error(str(exc))


def evaluation_page() -> None:
    workspace = require_workspace()
    if not workspace:
        return
    st.header("Evaluation")
    qa_tab, run_tab, results_tab = st.tabs(["Golden QA", "Run", "Results"])

    with qa_tab:
        with st.form("golden_qa"):
            question = st.text_area("Question")
            expected_answer = st.text_area("Expected answer")
            required_facts = st.text_area("Required facts, one per line")
            required_document_ids = st.text_area("Required document IDs, one per line")
            submitted = st.form_submit_button("Save golden QA")
        if submitted:
            try:
                api_request(
                    "POST",
                    "/eval/golden",
                    token=token(),
                    json={
                        "workspace_id": workspace["id"],
                        "question": question,
                        "expected_answer": expected_answer or None,
                        "required_facts": [line for line in required_facts.splitlines() if line],
                        "required_document_ids": [
                            line for line in required_document_ids.splitlines() if line
                        ],
                    },
                )
                st.success("Golden QA saved.")
            except Exception as exc:
                st.error(str(exc))

    with run_tab:
        if st.button("Run evaluation", use_container_width=True):
            try:
                result = api_request(
                    "POST",
                    "/eval/run",
                    token=token(),
                    json={"workspace_id": workspace["id"]},
                )
                st.success(f"Evaluation completed: {result['id']}")
                st.json(result)
            except Exception as exc:
                st.error(str(exc))

    with results_tab:
        try:
            runs = api_request(
                "GET",
                "/eval/results",
                token=token(),
                params={"workspace_id": workspace["id"]},
            )
            st.dataframe(runs, use_container_width=True, hide_index=True)
            run_ids = [run["id"] for run in runs]
            if run_ids:
                selected_run_id = st.selectbox("Run details", run_ids)
                details = api_request(
                    "GET",
                    "/eval/results",
                    token=token(),
                    params={"run_id": selected_run_id},
                )
                st.dataframe(details, use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(str(exc))


def main() -> None:
    if not token():
        login_screen()
        return

    page = sidebar()
    if page == "Workspaces":
        workspace_page()
    elif page == "Documents":
        documents_page()
    elif page == "Ask":
        ask_page()
    elif page == "Query History":
        history_page()
    elif page == "Feedback":
        feedback_page()
    elif page == "Evaluation":
        evaluation_page()


if __name__ == "__main__":
    main()
