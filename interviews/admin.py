from django.contrib import admin

from .models import Question, ReferenceSnippet, Session, Track, Turn


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "track_type", "is_active", "created_at"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["__str__", "track", "difficulty", "topic"]
    list_filter = ["track", "difficulty"]
    search_fields = ["text", "topic"]


@admin.register(ReferenceSnippet)
class ReferenceSnippetAdmin(admin.ModelAdmin):
    list_display = ["__str__", "track", "source"]
    list_filter = ["track"]


class TurnInline(admin.TabularInline):
    model = Turn
    extra = 0
    fields = ["order", "question_text", "answer_text", "evaluation"]
    readonly_fields = ["evaluation"]


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ["__str__", "status", "overall_score", "started_at", "completed_at"]
    list_filter = ["status", "track"]
    inlines = [TurnInline]


@admin.register(Turn)
class TurnAdmin(admin.ModelAdmin):
    list_display = ["__str__", "order", "follow_up_of"]
    list_filter = ["session__track"]
