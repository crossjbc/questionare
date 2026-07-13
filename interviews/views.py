from rest_framework import mixins, generics, permissions
from rest_framework.response import Response, generics, permissions

from .models import Question, ReferenceSnippet, Session, Track, Turn, Document
from .serializers import (
    QuestionSerializer,
    ReferenceSnippetSerializer,
    SessionCreateSerializer,
    SessionSerializer,
    TrackSerializer,
    TurnSerializer,
    DocumentSerializer
)
from .utils import process_document

# ---------------------------------------------------------------------------
# Track
# ---------------------------------------------------------------------------
class TrackListCreateView(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    generics.GenericAPIView,
):
    """
    Read-only for anonymous users so the frontend can list available tracks
    before login; write requires auth (intended for admin/instructor use).
    """

    queryset = Track.objects.filter(is_active=True)
    serializer_class = TrackSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class TrackDetailView(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    generics.GenericAPIView,
):
    queryset = Track.objects.filter(is_active=True)
    serializer_class = TrackSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = "slug"

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

# ---------------------------------------------------------------------------
# Question
# ---------------------------------------------------------------------------
class QuestionListCreateView(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    generics.GenericAPIView,
):
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Question.objects.all()
        track = self.request.query_params.get("track")
        if track:
            qs = qs.filter(track__slug=track)
        return qs

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class QuestionDetailView(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    generics.GenericAPIView,
):
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Question.objects.all()
        track = self.request.query_params.get("track")
        if track:
            qs = qs.filter(track__slug=track)
        return qs

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

# ---------------------------------------------------------------------------
# ReferenceSnippet
# ---------------------------------------------------------------------------
class ReferenceSnippetListCreateView(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    generics.GenericAPIView,
):
    serializer_class = ReferenceSnippetSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ReferenceSnippet.objects.all()

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

class ReferenceSnippetDetailView(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    generics.GenericAPIView,
):
    serializer_class = ReferenceSnippetSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ReferenceSnippet.objects.all()

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------
class SessionListCreateView(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    generics.GenericAPIView,
):
    """
    A student's mock-interview sessions. Scoped to the requesting user —
    nobody should be able to list or read someone else's interview attempts.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Session.objects.filter(user=self.request.user).select_related("track")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SessionCreateSerializer
        return SessionSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class SessionDetailView(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    generics.GenericAPIView,
):
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Session.objects.filter(user=self.request.user).select_related("track")

    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = SessionSerializer(instance)
        return Response(serializer.data)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

# ---------------------------------------------------------------------------
# Turn
# ---------------------------------------------------------------------------
class TurnListCreateView(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    generics.GenericAPIView,
):
    """
    Turns within a session. Phase 1 is plain CRUD — no agent logic yet.
    Phase 3+ will replace/extend `create` so that posting an answer here
    triggers the evaluation agent and (conditionally) generates a follow-up
    turn automatically.
    """

    serializer_class = TurnSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Turn.objects.filter(session__user=self.request.user)
        session_id = self.request.query_params.get("session")
        if session_id:
            qs = qs.filter(session_id=session_id)
        return qs

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class TurnDetailView(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    generics.GenericAPIView,
):
    serializer_class = TurnSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Turn.objects.filter(session__user=self.request.user)
        session_id = self.request.query_params.get("session")
        if session_id:
            qs = qs.filter(session_id=session_id)
        return qs

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)
    

class DocumentListCreateView(generics.ListCreateAPIView):
    """
    GET  -> list all documents
    POST -> upload a new document (multipart/form-data)
    """
    queryset = Document.objects.all().order_by("-created_at")
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        uploaded_file = serializer.validated_data.get("file")
        document = serializer.save(
            uploaded_by=self.request.user,
            original_filename=getattr(uploaded_file, "name", ""),
        )
        process_document(document)


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    """
    GET    -> check status of one document (poll this while processing)
    DELETE -> remove a document
    """
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]