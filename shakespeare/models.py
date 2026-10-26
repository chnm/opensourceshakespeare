"""Content models for Open Source Shakespeare.

These mirror the legacy MySQL tables (see legacy/db/oss-db-full.sql and the OSS
thesis, Appendix A). Legacy primary keys are kept so old URLs such as
playmenu.php?WorkID=hamlet and charlines.php?CharID=claudius can be redirected.
Text fields are stored exactly as in the legacy data: `[p]` marks a line break
inside a paragraph, and typographic characters are HTML entities (&#8217;).
"""

from django.db import models


class Genre(models.Model):
    code = models.CharField(max_length=1, primary_key=True)  # c, h, p, s, t
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Work(models.Model):
    id = models.CharField(max_length=50, primary_key=True)  # legacy WorkID slug, e.g. "hamlet"
    title = models.CharField(max_length=255)
    long_title = models.CharField(max_length=255)
    short_title = models.CharField(max_length=255, blank=True)
    date = models.IntegerField(help_text="Approximate year of composition")
    genre = models.ForeignKey(Genre, on_delete=models.PROTECT, related_name="works")
    notes = models.TextField(blank=True)
    source = models.CharField(max_length=255, blank=True)
    total_words = models.IntegerField(null=True)
    total_paragraphs = models.IntegerField(null=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class Chapter(models.Model):
    """A scene of a play, a single sonnet, or a section of a poem."""

    id = models.IntegerField(primary_key=True)  # legacy ChapterID
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="chapters")
    section = models.IntegerField(help_text="Act number for plays; 0 is a prologue")
    number = models.IntegerField(help_text="Scene number within the act")
    description = models.CharField(max_length=255, blank=True)  # setting, e.g. "Elsinore. A room in the Castle."

    class Meta:
        ordering = ["work", "section", "number"]
        constraints = [
            models.UniqueConstraint(fields=["work", "section", "number"], name="unique_chapter_position"),
        ]

    def __str__(self):
        return f"{self.work_id} {self.section}.{self.number}"


class Character(models.Model):
    id = models.CharField(max_length=50, primary_key=True)  # legacy CharID; "xxx" is stage directions
    name = models.CharField(max_length=255)
    abbrev = models.CharField(max_length=255, blank=True)
    works = models.ManyToManyField(Work, related_name="characters")
    description = models.CharField(max_length=255, blank=True)
    speech_count = models.IntegerField(null=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Paragraph(models.Model):
    """One speech or stage direction."""

    id = models.IntegerField(primary_key=True)  # legacy ParagraphID; also the reading order
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="paragraphs")
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="paragraphs")
    character = models.ForeignKey(Character, on_delete=models.PROTECT, related_name="paragraphs")
    line_number = models.IntegerField(help_text="Line on which the paragraph starts (legacy ParagraphNum)")
    plain_text = models.TextField()
    phonetic_text = models.TextField(blank=True)
    stem_text = models.TextField(blank=True)
    paragraph_type = models.CharField(max_length=1)
    char_count = models.IntegerField()
    word_count = models.IntegerField()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.work_id} {self.line_number}"


class WordForm(models.Model):
    """A concordance entry: one spelling and how often it occurs across all works."""

    id = models.IntegerField(primary_key=True)  # legacy WordFormID
    plain_text = models.CharField(max_length=100, db_index=True)
    phonetic_text = models.CharField(max_length=100)
    stem_text = models.CharField(max_length=100)
    occurrences = models.IntegerField()

    class Meta:
        ordering = ["plain_text"]

    def __str__(self):
        return self.plain_text


class Quotation(models.Model):
    """A short quotation shown in the page header. Both fields contain legacy HTML."""

    id = models.IntegerField(primary_key=True)
    text = models.CharField(max_length=255)
    location = models.CharField(max_length=255)

    def __str__(self):
        return self.text
