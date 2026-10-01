from django.db import migrations


LOCATIONS = {
    'Brazzaville': ['Makélékélé', 'Bacongo', 'Poto-Poto', 'Moungali', 'Ouenzé', 'Talangaï', 'Mfilou', 'Madibou'],
    'Pointe-Noire': ['Lumumba', 'Mvou-Mvou', 'Tié-Tié', 'Loandjili', 'Mongo-Mpoukou', 'Ngoyo'],
    'Bouenza': ['Madingou', 'Nkayi', 'Boko-Songho', 'Mfouati'],
    'Cuvette': ['Owando', 'Boundji', 'Mossaka', 'Oyo'],
    'Cuvette-Ouest': ['Ewo', 'Etoumbi', 'Kelle'],
    'Kouilou': ['Hinda', 'Madingo-Kayes', 'Nzambi', 'Loango'],
    'Lékoumou': ['Sibiti', 'Komono', 'Zanaga'],
    'Likouala': ['Impfondo', 'Dongou', 'Épéna', 'Bétou'],
    'Niari': ['Dolisie', 'Mouyondzi', 'Mossendjo', 'Kimongo'],
    'Plateaux': ['Djambala', 'Gamboma', 'Lekana', 'Ngo'],
    'Pool': ['Kinkala', 'Mindouli', 'Boko', 'Kimba'],
    'Sangha': ['Ouésso', 'Sembé', 'Souanké', 'Pokola'],
}


def seed_locations(apps, schema_editor):
    Department = apps.get_model('users', 'Department')
    Arrondissement = apps.get_model('users', 'Arrondissement')
    for department_name, arrondissement_names in LOCATIONS.items():
        department = Department.objects.create(name=department_name)
        Arrondissement.objects.bulk_create([
            Arrondissement(department=department, name=name)
            for name in arrondissement_names
        ])


def remove_locations(apps, schema_editor):
    apps.get_model('users', 'Department').objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [('users', '0006_department_arrondissement')]
    operations = [migrations.RunPython(seed_locations, remove_locations)]
