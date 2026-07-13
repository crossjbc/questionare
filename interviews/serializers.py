from rest_framework import serializers

from .models import Question, ReferenceSnippet, Session, Track, Turn


class TrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Track
        fields = ["id", "name", "slug", "track_type", "description", "is_active", "created_at"]


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            "id", "track", "text", "topic", "difficulty",
            "reference_answer", "rubric", "created_at",
        ]


class ReferenceSnippetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferenceSnippet
        fields = ["id", "track", "content", "source", "created_at"]
        # embedding intentionally excluded from API output — internal only


class TurnSerializer(serializers.ModelSerializer):
    class Meta:
        model = Turn
        fields = [
            "id", "session", "question", "question_text", "follow_up_of",
            "order", "answer_text", "evaluation", "created_at",
        ]
        read_only_fields = ["evaluation"]  # set by the evaluation agent, not the client


class SessionSerializer(serializers.ModelSerializer):
    turns = TurnSerializer(many=True, read_only=True)

    class Meta:
        model = Session
        fields = [
            "id", "user", "track", "status", "started_at",
            "completed_at", "overall_score", "summary", "turns",
        ]
        read_only_fields = ["overall_score", "summary", "completed_at"]


class SessionCreateSerializer(serializers.ModelSerializer):
    """Slim serializer for starting a new session — just needs a track."""

    class Meta:
        model = Session
        fields = ["id", "track"]

from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            "id", "track", "file", "original_filename",
            "status", "error_message", "chunk_count",
            "uploaded_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "error_message", "chunk_count", "uploaded_by", "created_at", "updated_at"]