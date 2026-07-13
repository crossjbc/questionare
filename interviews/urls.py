from django.urls import path
from .views import (
    TrackListCreateView, TrackDetailView,
    QuestionListCreateView, QuestionDetailView,
    ReferenceSnippetListCreateView, ReferenceSnippetDetailView,
    SessionListCreateView, SessionDetailView,
    TurnListCreateView, TurnDetailView,DocumentListCreateView, DocumentDetailView
)
    

urlpatterns = [
    path("tracks/", TrackListCreateView.as_view()),
    path("tracks/<slug:slug>/", TrackDetailView.as_view()),
    path("questions/", QuestionListCreateView.as_view()),
    path("questions/<int:pk>/", QuestionDetailView.as_view()),
    path("reference-snippets/", ReferenceSnippetListCreateView.as_view()),
    path("reference-snippets/<int:pk>/", ReferenceSnippetDetailView.as_view()),
    path("sessions/", SessionListCreateView.as_view()),
    path("sessions/<int:pk>/", SessionDetailView.as_view()),
    path("turns/", TurnListCreateView.as_view()),
    path("turns/<int:pk>/", TurnDetailView.as_view()),
    path("documents/", DocumentListCreateView.as_view(), name="document-list-create"),
    path("documents/<uuid:pk>/", DocumentDetailView.as_view(), name="document-detail"),
]
