import uuid

from django.conf import settings
from django.db import models

try:
    from pgvector.django import VectorField
except ImportError:  # pgvector not installed / not on Postgres yet
    VectorField = None


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Track(TimeStampedModel):
    """
    A configurable interview 'track' — e.g. UPSC Civil Services Interview,
    Technical/Backend Engineering Interview, Behavioral Interview.
    Keeping this data-driven (not hardcoded) is what lets the same engine
    serve multiple very different interview styles.
    """

    class TrackType(models.TextChoices):
        CIVIL_SERVICES = "civil_services", "Civil Services / UPSC"
        TECHNICAL = "technical", "Technical Interview"
        BEHAVIORAL = "behavioral", "Behavioral Interview"
        CUSTOM = "custom", "Custom"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    track_type = models.CharField(max_length=20, choices=TrackType.choices)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Question(TimeStampedModel):
    """
    A seed question. Not every question shown to a student comes from here —
    the generation agent can also produce questions on the fly — but this
    bank gives the agent grounded, curated material to draw from and adapt.
    """

    class Difficulty(models.IntegerChoices):
        EASY = 1, "Easy"
        MEDIUM = 2, "Medium"
        HARD = 3, "Hard"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    topic = models.CharField(max_length=120, blank=True)
    difficulty = models.IntegerField(choices=Difficulty.choices, default=Difficulty.MEDIUM)
    reference_answer = models.TextField(
        blank=True, help_text="Optional model answer or key points, used by the evaluation agent."
    )
    rubric = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-question scoring criteria, e.g. {'structure': 0.3, 'depth': 0.4, 'relevance': 0.3}",
    )

    def __str__(self):
        return f"[{self.track.slug}] {self.text[:60]}"

class Document(TimeStampedModel):
    """
    An uploaded reference file (e.g. a PDF of current-affairs notes, a
    syllabus doc). This is the source; ReferenceSnippet rows are the
    chunks produced FROM this source once processing completes.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="documents")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents"
    )
    file = models.FileField(upload_to="reference_documents/%Y/%m/")
    original_filename = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True)
    chunk_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"[{self.track.slug}] {self.original_filename or self.file.name} ({self.status})"

class ReferenceSnippet(TimeStampedModel):
    """
    Corpus material used for retrieval-grounded question generation and
    evaluation (e.g. current-affairs notes for UPSC, syllabus topics for
    technical tracks).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="snippets")
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, null=True, blank=True, related_name="snippets"
    )
    content = models.TextField()
    source = models.CharField(max_length=255, blank=True)

    if VectorField is not None:
        embedding = VectorField(dimensions=768, null=True, blank=True)
    else:
        embedding = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"[{self.track.slug}] {self.content[:60]}"


class Session(TimeStampedModel):
    """One mock-interview attempt by a student on a given track."""

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        ABANDONED = "abandoned", "Abandoned"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessions")
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="sessions")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    overall_score = models.FloatField(null=True, blank=True)
    summary = models.JSONField(
        default=dict, blank=True, help_text="Strengths/weak-areas summary generated at session end."
    )

    def __str__(self):
        return f"{self.user} – {self.track.name} ({self.status})"


class Turn(TimeStampedModel):
    """
    A single question/answer/evaluation exchange within a session.
    follow_up_of links a probing follow-up back to the turn that triggered
    it, which is what makes a session a real multi-turn thread rather than
    a flat quiz.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="turns")
    question = models.ForeignKey(
        Question, on_delete=models.SET_NULL, null=True, blank=True, related_name="turns"
    )
    question_text = models.TextField(
        help_text="Snapshot of the question actually asked (covers agent-generated questions too)."
    )
    follow_up_of = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="follow_ups"
    )
    order = models.PositiveIntegerField(default=0)
    answer_text = models.TextField(blank=True)
    evaluation = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured rubric scores + rationale from the evaluation agent, e.g. "
        "{'scores': {'structure': 7, 'depth': 6}, 'rationale': '...'}",
    )

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"Turn {self.order} – {self.session_id}"
