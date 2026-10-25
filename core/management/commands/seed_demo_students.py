from django.core.management.base import BaseCommand
from core.models import StudentProfile

DEMO = [
    {"slug":"maya","name":"Maya Krishnan","initials":"MK","year":"3rd year · CSE","skills":{"python":4,"machine learning":4,"data analysis":3},"interests":["AI","healthtech"],"availability":"Weekends + evenings","contribution":"AI / data","color":"violet"},
    {"slug":"arjun","name":"Arjun Menon","initials":"AM","year":"2nd year · CSE","skills":{"javascript":4,"react":4,"html":4,"css":4},"interests":["EdTech","product design"],"availability":"Evenings","contribution":"Frontend","color":"blue"},
    {"slug":"isha","name":"Isha Rao","initials":"IR","year":"3rd year · IT","skills":{"python":3,"fastapi":4,"sql":4,"postgresql":4},"interests":["Developer tools","fintech"],"availability":"Flexible","contribution":"Backend / API","color":"orange"},
    {"slug":"dev","name":"Dev Shah","initials":"DS","year":"2nd year · ECE","skills":{"figma":4,"ui ux":4,"research":3,"html":2},"interests":["Accessibility","design"],"availability":"Weekends","contribution":"Design / research","color":"green"},
    {"slug":"sana","name":"Sana Patel","initials":"SP","year":"3rd year · CSE","skills":{"python":3,"machine learning":3,"javascript":2,"sql":3},"interests":["AI","climate tech"],"availability":"Evenings + weekends","contribution":"AI / full-stack","color":"pink"},
    {"slug":"rohan","name":"Rohan Das","initials":"RD","year":"1st year · CSE","skills":{"javascript":3,"react":2,"figma":2,"research":3},"interests":["Community","EdTech"],"availability":"Weekends","contribution":"Frontend / research","color":"teal"},
]

class Command(BaseCommand):
    help = "Create clearly labelled illustrative ThinkLink demo profiles."

    def handle(self, *args, **options):
        for item in DEMO:
            StudentProfile.objects.update_or_create(
                slug=item["slug"],
                defaults={**item, "college":"ThinkLink Demo Campus", "is_demo":True},
            )
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(DEMO)} illustrative student profiles."))
