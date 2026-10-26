from django.contrib import admin

from .models import Chapter, Character, Genre, Paragraph, Quotation, Work, WordForm


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ["code", "name"]


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ["title", "id", "genre", "date", "total_words", "total_paragraphs"]
    list_filter = ["genre"]
    search_fields = ["id", "title", "long_title"]


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ["work", "section", "number", "description", "id"]
    list_filter = ["work__genre", "work"]
    list_select_related = ["work"]
    search_fields = ["description"]


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ["name", "id", "speech_count", "work_list", "description"]
    list_filter = ["works__genre", "works"]
    search_fields = ["id", "name", "abbrev", "description"]
    filter_horizontal = ["works"]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("works")

    @admin.display(description="Works")
    def work_list(self, obj):
        return ", ".join(w.title for w in obj.works.all())


@admin.register(Paragraph)
class ParagraphAdmin(admin.ModelAdmin):
    list_display = ["id", "work", "act_scene", "line_number", "character", "excerpt"]
    list_filter = ["work__genre", "work"]
    list_select_related = ["work", "chapter", "character"]
    search_fields = ["plain_text", "character__name"]
    raw_id_fields = ["work", "chapter", "character"]

    @admin.display(description="Act.Scene", ordering="chapter")
    def act_scene(self, obj):
        return f"{obj.chapter.section}.{obj.chapter.number}"

    @admin.display(description="Text")
    def excerpt(self, obj):
        # Shown raw on purpose: [p] markers and HTML entities are what the legacy data holds.
        return obj.plain_text[:120]


@admin.register(WordForm)
class WordFormAdmin(admin.ModelAdmin):
    list_display = ["plain_text", "occurrences", "stem_text", "phonetic_text"]
    search_fields = ["plain_text", "stem_text", "phonetic_text"]
    ordering = ["-occurrences"]


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ["text", "location"]
    search_fields = ["text", "location"]
