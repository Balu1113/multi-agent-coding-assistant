from src import llm_service


def test_gemini_client_prefers_project_env_key_and_refreshes_cache(monkeypatch):
    file_key = "project-key"
    client = object()
    created_keys = []

    monkeypatch.setattr(llm_service, "env_path", type("EnvPath", (), {"exists": lambda _self: True})())
    monkeypatch.setattr("dotenv.dotenv_values", lambda _path: {"GEMINI_API_KEY": file_key})
    monkeypatch.setenv("GEMINI_API_KEY", "stale-process-key")
    monkeypatch.setattr(llm_service.genai, "Client", lambda api_key: created_keys.append(api_key) or client)
    monkeypatch.setattr(llm_service, "_client", None)
    monkeypatch.setattr(llm_service, "_client_api_key", None)

    result = llm_service._get_client()

    assert result is client
    assert created_keys == [file_key]
    assert llm_service._client_api_key == file_key


def test_chat_with_llm_includes_workspace_context(monkeypatch):
    captured = {}

    def fake_call(user, system, model=None):
        captured["user"] = user
        return "answer"

    monkeypatch.setattr(llm_service, "_call", fake_call)

    result = llm_service.chat_with_llm(
        "What features could be added?",
        workspace_context="--- src/app.py ---\nprint('hello')",
    )

    assert result == "answer"
    assert "src/app.py" in captured["user"]
    assert "What features could be added?" in captured["user"]


def test_generate_workspace_response_returns_plan_without_changes(monkeypatch):
    import json

    payload = {
        "mode": "plan",
        "analysis": "The entry point needs a focused update.",
        "message": "",
        "requirement": "Add a startup message.",
        "plan": "1. Update src/app.py.",
        "changes": [],
    }
    monkeypatch.setattr(llm_service, "_call", lambda *_args, **_kwargs: json.dumps(payload))

    result = llm_service.generate_workspace_response(
        "Add a startup message.", "src/app.py", [{"path": "src/app.py", "content": "print('hello')"}],
    )

    assert result["mode"] == "plan"
    assert result["changes"] == []


def test_generate_workspace_response_parses_wrapped_json(monkeypatch):
    import json

    payload = {
        "mode": "plan",
        "analysis": "The requested module needs an implementation.",
        "requirement": "Add model loading.",
        "plan": "1. Update utils/ml_models.py.",
        "changes": [],
    }
    encoded = json.dumps(payload)
    for response in (encoded, f"```json\n{encoded}\n```", f"Here is the plan:\n{encoded}\nLet me know if you approve."):
        monkeypatch.setattr(llm_service, "_call", lambda *_args, _response=response, **_kwargs: _response)
        result = llm_service.generate_workspace_response("Add model loading", "", [])
        assert result["mode"] == "plan"
        assert result["plan"] == payload["plan"]


def test_generate_workspace_response_reports_invalid_json(monkeypatch):
    import pytest

    monkeypatch.setattr(llm_service, "_call", lambda *_args, **_kwargs: "I will work on that now.")

    with pytest.raises(ValueError, match="after one format retry"):
        llm_service.generate_workspace_response("Add model loading", "", [])


def test_generate_workspace_response_repairs_invalid_first_response(monkeypatch):
    import json

    payload = {
        "mode": "plan",
        "analysis": "The model loader needs an update.",
        "requirement": "Add model loading.",
        "plan": "1. Update utils/ml_models.py.",
        "changes": [],
    }
    responses = iter(("I will work on that now.", json.dumps(payload)))
    calls = []

    def fake_call(prompt, system, **_kwargs):
        calls.append((prompt, system))
        return next(responses)

    monkeypatch.setattr(llm_service, "_call", fake_call)
    result = llm_service.generate_workspace_response("Add model loading", "", [])

    assert result["mode"] == "plan"
    assert len(calls) == 2
    assert "Reformat the supplied model response" in calls[1][1]


def test_generate_workspace_response_includes_conversation_history(monkeypatch):
    import json

    captured = {}
    payload = {
        "mode": "answer",
        "analysis": "The previous request asked for pandas.",
        "message": "I will keep using pandas.",
        "requirement": "",
        "plan": "",
        "changes": [],
    }

    def fake_call(prompt, _system, **_kwargs):
        captured["context"] = json.loads(prompt)
        return json.dumps(payload)

    monkeypatch.setattr(llm_service, "_call", fake_call)
    history = [
        {"role": "user", "content": "Use pandas for the data layer."},
        {"role": "assistant", "content": "I will use pandas."},
    ]

    llm_service.generate_workspace_response(
        "Continue with that choice.", "", [], conversation_history=history,
    )

    assert captured["context"]["conversation_history"] == history


def test_generate_workspace_response_preserves_explicit_file_deletion(monkeypatch):
    import json

    captured = {}
    payload = {
        "mode": "changes",
        "analysis": "The obsolete module is no longer used.",
        "message": "Removed the unused module.",
        "requirement": "Remove utils/legacy.py.",
        "plan": "1. Delete utils/legacy.py.",
        "changes": [{"path": "utils/legacy.py", "action": "delete", "content": ""}],
    }

    def fake_call(_prompt, system, **_kwargs):
        captured["system"] = system
        return json.dumps(payload)

    monkeypatch.setattr(llm_service, "_call", fake_call)
    result = llm_service.generate_workspace_response(
        "Remove utils/legacy.py.",
        "utils/legacy.py",
        [{"path": "utils/legacy.py", "content": "legacy code"}],
        approved_plan="1. Delete utils/legacy.py.",
    )

    assert result["changes"] == payload["changes"]
    assert 'action=delete' in captured["system"]


def test_generate_workspace_response_accepts_workspace_read_tool_call(monkeypatch):
    import json

    payload = {
        "mode": "tool_call",
        "analysis": "I need to inspect the model utility module before planning.",
        "tool_call": {"tool": "read_file", "path": "utils/ml_models.py"},
    }
    monkeypatch.setattr(llm_service, "_call", lambda *_args, **_kwargs: json.dumps(payload))

    result = llm_service.generate_workspace_response("Update model loading", "", [])

    assert result["tool_call"] == {"tool": "read_file", "path": "utils/ml_models.py"}
    assert result["changes"] == []


def test_generate_workspace_response_rejects_unsafe_tool_path(monkeypatch):
    import json
    import pytest

    payload = {
        "mode": "tool_call",
        "tool_call": {"tool": "read_file", "path": "../.env"},
    }
    monkeypatch.setattr(llm_service, "_call", lambda *_args, **_kwargs: json.dumps(payload))

    with pytest.raises(ValueError, match="read path was invalid"):
        llm_service.generate_workspace_response("Inspect config", "", [])


def test_generate_workspace_response_accepts_directory_listing_tool(monkeypatch):
    import json

    payload = {
        "mode": "tool_call",
        "analysis": "I need to verify the project folder contents.",
        "tool_call": {"tool": "list_directory", "path": "templates"},
    }
    monkeypatch.setattr(llm_service, "_call", lambda *_args, **_kwargs: json.dumps(payload))

    result = llm_service.generate_workspace_response("Remove templates", "", [], directories=["templates"])

    assert result["tool_call"] == {"tool": "list_directory", "path": "templates"}


def test_generate_workspace_response_accepts_approved_directory_removal(monkeypatch):
    import json

    payload = {
        "mode": "changes",
        "analysis": "The reviewed folder contents can be removed.",
        "requirement": "Remove templates.",
        "plan": "Delete the template file and then the empty folder.",
        "changes": [{"path": "templates", "action": "delete_directory", "content": ""}],
    }
    monkeypatch.setattr(llm_service, "_call", lambda *_args, **_kwargs: json.dumps(payload))

    result = llm_service.generate_workspace_response(
        "Remove templates", "", [], approved_plan="Delete the template file and then the empty folder."
    )

    assert result["changes"][0]["action"] == "delete_directory"


def test_generate_workspace_response_rejects_paths_outside_workspace(monkeypatch):
    import json
    import pytest

    payload = {
        "mode": "changes",
        "analysis": "",
        "message": "",
        "requirement": "",
        "changes": [{"path": "../outside.py", "content": "unsafe"}],
    }
    monkeypatch.setattr(llm_service, "_call", lambda *_args, **_kwargs: json.dumps(payload))

    with pytest.raises(ValueError, match="outside the workspace"):
        llm_service.generate_workspace_response(
            "Update a file", "src/app.py", [], approved_plan="1. Update src/app.py."
        )


def test_generate_workspace_response_requires_changes_after_approval(monkeypatch):
    import json
    import pytest

    payload = {
        "mode": "plan",
        "analysis": "The requested improvement is clear.",
        "message": "",
        "requirement": "Add request logging.",
        "plan": "1. Add request logging to the project.",
        "changes": [],
    }
    monkeypatch.setattr(llm_service, "_call", lambda *_args, **_kwargs: json.dumps(payload))

    with pytest.raises(ValueError, match="did not implement the approved plan"):
        llm_service.generate_workspace_response(
            "Suggest an improvement", "src/app.py", [], approved_plan="1. Add request logging."
        )


def test_generate_workspace_response_discards_changes_from_unapproved_plans(monkeypatch):
    import json
    import pytest

    payload = {
        "mode": "plan",
        "analysis": "The project could benefit from a health endpoint.",
        "message": "",
        "requirement": "Add a health endpoint.",
        "plan": "1. Add the health endpoint.",
        "changes": [{"path": "src/app.py", "content": "unsafe early edit"}],
    }
    monkeypatch.setattr(llm_service, "_call", lambda *_args, **_kwargs: json.dumps(payload))

    result = llm_service.generate_workspace_response("Make improvements", "src/app.py", [])

    assert result["mode"] == "plan"
    assert result["changes"] == []
    assert result["discarded_unapproved_changes"] is True


def test_generate_workspace_response_converts_premature_changes_to_plan(monkeypatch):
    import json

    payload = {
        "mode": "changes",
        "analysis": "This file is obsolete.",
        "message": "Removed the obsolete file.",
        "requirement": "Remove utils/old_model.py.",
        "plan": "",
        "changes": [{"path": "utils/old_model.py", "action": "delete", "content": ""}],
    }
    monkeypatch.setattr(llm_service, "_call", lambda *_args, **_kwargs: json.dumps(payload))

    result = llm_service.generate_workspace_response("Remove utils/old_model.py", "", [])

    assert result["mode"] == "plan"
    assert "Remove utils/old_model.py" in result["plan"]
    assert result["changes"] == []
    assert result["discarded_unapproved_changes"] is True


def test_generate_workspace_response_handles_missing_plan_field(monkeypatch):
    import json

    payload = {
        "mode": "changes",
        "analysis": "The obsolete model helper should be removed.",
        "changes": [{"path": "utils/ml_models.py", "action": "delete", "content": ""}],
    }
    monkeypatch.setattr(llm_service, "_call", lambda *_args, **_kwargs: json.dumps(payload))

    result = llm_service.generate_workspace_response("Remove utils/ml_models.py", "", [])

    assert result["mode"] == "plan"
    assert "Remove utils/ml_models.py" in result["plan"]
    assert result["changes"] == []


def test_generate_workspace_response_requires_approval_for_proposals(monkeypatch):
    import json

    captured = {}
    payload = {
        "mode": "changes",
        "analysis": "",
        "message": "Implemented the approved improvement.",
        "requirement": "",
        "plan": "",
        "changes": [{"path": "src/app.py", "content": "print('approved')"}],
    }

    def fake_call(_prompt, system, **_kwargs):
        captured["system"] = system
        return json.dumps(payload)

    monkeypatch.setattr(llm_service, "_call", fake_call)
    llm_service.generate_workspace_response(
        "Suggest an improvement", "src/app.py", [],
        approved_requirement="Add startup logging",
        approved_plan="1. Add startup logging to the app.",
    )

    assert "explicitly approved this implementation plan" in captured["system"]
    assert "do not ask for further approval" in captured["system"]