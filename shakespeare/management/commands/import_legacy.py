from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from shakespeare.legacy_sql import read_tables
from shakespeare.models import Chapter, Character, Genre, Paragraph, Quotation, Work, WordForm

# Only content tables. The dump also holds UserAccounts (personal data), the search
# logs, and the unlaunched annotation/media tables; those are deliberately not read.
TABLES = ["Genres", "Works", "Chapters", "Characters", "Paragraphs", "WordForms", "Quotations"]
BATCH = 2000


class Command(BaseCommand):
    help = "Load Open Source Shakespeare content from the legacy MySQL dump, replacing existing content."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default=settings.BASE_DIR / "legacy/db/oss-db-full.sql")

    def handle(self, path, **options):
        self.stdout.write(f"Reading {path}")
        data = read_tables(path, TABLES)
        for table in TABLES:
            if not data[table]:
                raise CommandError(f"No rows found for {table}")

        with transaction.atomic():
            # Full replace keeps the import repeatable; children first because of PROTECT.
            for model in (Paragraph, WordForm, Quotation, Character, Chapter, Work, Genre):
                model.objects.all().delete()

            Genre.objects.bulk_create(Genre(code=r["GenreType"], name=r["GenreName"]) for r in data["Genres"])

            Work.objects.bulk_create(
                Work(
                    id=r["WorkID"],
                    title=r["Title"],
                    long_title=r["LongTitle"],
                    short_title=r["ShortTitle"] or "",
                    date=r["Date"],
                    genre_id=r["GenreType"],
                    notes=r["Notes"] or "",
                    source=r["Source"],
                    total_words=r["TotalWords"],
                    total_paragraphs=r["TotalParagraphs"],
                )
                for r in data["Works"]
            )
            work_ids = {r["WorkID"] for r in data["Works"]}

            Chapter.objects.bulk_create(
                (
                    Chapter(
                        id=r["ChapterID"],
                        work_id=r["WorkID"],
                        section=r["Section"],
                        number=r["Chapter"],
                        description=r["Description"],
                    )
                    for r in data["Chapters"]
                ),
                batch_size=BATCH,
            )
            chapter_ids = {(r["WorkID"], r["Section"], r["Chapter"]): r["ChapterID"] for r in data["Chapters"]}

            Character.objects.bulk_create(
                (
                    Character(
                        id=r["CharID"],
                        name=r["CharName"],
                        abbrev=r["Abbrev"] or "",
                        description=r["Description"],
                        speech_count=r["SpeechCount"],
                    )
                    for r in data["Characters"]
                ),
                batch_size=BATCH,
            )
            # Legacy Characters.Works is a comma-separated list of WorkIDs.
            links = []
            for r in data["Characters"]:
                for work_id in filter(None, (w.strip() for w in r["Works"].split(","))):
                    if work_id not in work_ids:
                        raise CommandError(f"Character {r['CharID']} lists unknown work {work_id!r}")
                    links.append(Character.works.through(character_id=r["CharID"], work_id=work_id))
            Character.works.through.objects.bulk_create(links, batch_size=BATCH)
            character_ids = {r["CharID"] for r in data["Characters"]}

            paragraphs = []
            for r in data["Paragraphs"]:
                chapter_id = chapter_ids.get((r["WorkID"], r["Section"], r["Chapter"]))
                if chapter_id is None:
                    raise CommandError(f"Paragraph {r['ParagraphID']} has no chapter {r['WorkID']} {r['Section']}.{r['Chapter']}")
                if r["CharID"] not in character_ids:
                    raise CommandError(f"Paragraph {r['ParagraphID']} has unknown character {r['CharID']!r}")
                paragraphs.append(
                    Paragraph(
                        id=r["ParagraphID"],
                        work_id=r["WorkID"],
                        chapter_id=chapter_id,
                        character_id=r["CharID"],
                        line_number=r["ParagraphNum"],
                        plain_text=r["PlainText"],
                        phonetic_text=r["PhoneticText"] or "",
                        stem_text=r["StemText"] or "",
                        paragraph_type=r["ParagraphType"],
                        char_count=r["CharCount"],
                        word_count=r["WordCount"],
                    )
                )
            Paragraph.objects.bulk_create(paragraphs, batch_size=BATCH)

            WordForm.objects.bulk_create(
                (
                    WordForm(
                        id=r["WordFormID"],
                        plain_text=r["PlainText"],
                        phonetic_text=r["PhoneticText"],
                        stem_text=r["StemText"],
                        occurrences=r["Occurences"],
                    )
                    for r in data["WordForms"]
                ),
                batch_size=BATCH,
            )

            Quotation.objects.bulk_create(
                Quotation(id=r["QuotationID"], text=r["QuotationText"], location=r["Location"])
                for r in data["Quotations"]
            )

        for model in (Genre, Work, Chapter, Character, Paragraph, WordForm, Quotation):
            self.stdout.write(f"{model.__name__}: {model.objects.count()}")
        self.stdout.write(self.style.SUCCESS("Import complete"))
