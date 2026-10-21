from rest_framework import serializers


class WorkflowInputSerializer(serializers.Serializer):
    prompt = serializers.CharField(required=True, min_length=1, max_length=5000)
    history = serializers.ListField(required=False, default=[])
    model = serializers.CharField(required=False, default="")
    agents = serializers.ListField(required=False, default=[], child=serializers.CharField())
    service = serializers.CharField(required=False, default="")
    plan = serializers.CharField(required=False, default="")
    execute_plan = serializers.BooleanField(required=False, default=False)
    plan_approved = serializers.BooleanField(required=False, default=False)
    research_mode = serializers.BooleanField(required=False, default=False)
    web_search = serializers.BooleanField(required=False, default=True)


class WorkflowOutputSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    type = serializers.CharField(default="code")
    code = serializers.CharField(default="")
    review = serializers.CharField(default="")
    tests = serializers.CharField(default="")
    research = serializers.CharField(default="")
    plan = serializers.CharField(default="")
    requires_approval = serializers.BooleanField(default=False)
    error = serializers.CharField(default="")
    duration = serializers.FloatField(default=0.0)


class WorkspaceFileSerializer(serializers.Serializer):
    path = serializers.CharField(max_length=500)
    action = serializers.ChoiceField(choices=("write", "delete", "delete_directory"), default="write")
    content = serializers.CharField(max_length=60000, allow_blank=True, required=False, default="")
    truncated = serializers.BooleanField(required=False, default=False)


class WorkspaceHistoryMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=("user", "assistant"))
    content = serializers.CharField(max_length=4000, allow_blank=True)


class WorkspaceToolResultSerializer(serializers.Serializer):
    tool = serializers.ChoiceField(choices=("search_workspace", "read_file", "list_directory"))
    query = serializers.CharField(required=False, default="", max_length=200, allow_blank=True)
    path = serializers.CharField(required=False, default="", max_length=500, allow_blank=True)
    result = serializers.CharField(max_length=50000, allow_blank=True)


class WorkspaceAgentInputSerializer(serializers.Serializer):
    prompt = serializers.CharField(required=True, min_length=1, max_length=5000)
    inventory = serializers.CharField(required=False, default="", max_length=8000, allow_blank=True)
    directories = serializers.ListField(child=serializers.CharField(max_length=500), required=False, default=list, max_length=1000)
    files = serializers.ListField(child=WorkspaceFileSerializer(), required=False, default=list, max_length=14)
    history = serializers.ListField(
        child=WorkspaceHistoryMessageSerializer(), required=False, default=list, max_length=20,
    )
    tool_results = serializers.ListField(
        child=WorkspaceToolResultSerializer(), required=False, default=list, max_length=4,
    )
    model = serializers.CharField(required=False, default="", allow_blank=True)
    approved_requirement = serializers.CharField(required=False, default="", max_length=5000, allow_blank=True)
    approved_plan = serializers.CharField(required=False, default="", max_length=10000, allow_blank=True)


class ChatInputSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, min_length=1, max_length=5000)
    history = serializers.ListField(required=False, default=[])
    model = serializers.CharField(required=False, default="")
    web_search = serializers.BooleanField(required=False, default=True)
    workspace_context = serializers.CharField(required=False, default="", max_length=1500000)


class ChatOutputSerializer(serializers.Serializer):
    type = serializers.CharField(default="chat")
    message = serializers.CharField()


class DebugInputSerializer(serializers.Serializer):
    error = serializers.CharField(required=True, min_length=1, max_length=5000)
    model = serializers.CharField(required=False, default="")


class DebugOutputSerializer(serializers.Serializer):
    type = serializers.CharField(default="debug")
    error_type = serializers.CharField()
    analysis = serializers.CharField()
    fix = serializers.CharField()
    code = serializers.CharField(default="")


class LanguageAliasSerializer(serializers.Serializer):
    name = serializers.CharField()
    aliases = serializers.ListField(child=serializers.CharField())


class LanguagesOutputSerializer(serializers.Serializer):
    languages = LanguageAliasSerializer(many=True)


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)
    prompt = serializers.CharField(required=False, default="")
    model = serializers.CharField(required=False, default="")
    agents = serializers.ListField(required=False, default=[], child=serializers.CharField())
    service = serializers.CharField(required=False, default="")
    history = serializers.CharField(required=False, default="")
    web_search = serializers.BooleanField(required=False, default=True)
    plan = serializers.CharField(required=False, default="")
    execute_plan = serializers.BooleanField(required=False, default=False)
    plan_approved = serializers.BooleanField(required=False, default=False)
    research_mode = serializers.BooleanField(required=False, default=False)


class ImageInputSerializer(serializers.Serializer):
    prompt = serializers.CharField(required=True, min_length=1, max_length=2000)
    model = serializers.CharField(required=False, default="")


class ImageOutputSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    image_data = serializers.CharField(default="")
    mime_type = serializers.CharField(default="")
    error = serializers.CharField(default="")
