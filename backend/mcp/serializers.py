import os
import sys
from pathlib import Path

from rest_framework import serializers


class MCPCallInputSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    arguments = serializers.DictField(required=False, default={})
