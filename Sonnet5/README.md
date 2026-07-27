# Planificateur de repas — Sonnet 5

Application locale de planification de repas avec calcul de macronutriments,
suggestions de plats basées sur les aliments disponibles, et suivi
nutritionnel dans le temps.

## Lancer l'application

```bash
pip install -r requirements.txt
streamlit run app.py
```

L'application s'ouvre dans le navigateur à l'adresse `http://localhost:8501`.
Toutes les données (profil, inventaire, journal de repas) sont stockées
localement dans `data/app.db` (SQLite).

## Fonctionnalités

- **Profil** : calcul des besoins caloriques (Mifflin-St Jeor) et des macros
  cibles, adaptés au profil (sportif prise de masse / sèche / maintien, ou
  sédentaire), réparties intelligemment sur les repas de la journée.
- **Mes aliments** : inventaire des aliments disponibles à la maison, avec
  quantité et date de péremption optionnelle.
- **Suggestions de repas** : propose les recettes les plus adaptées aux
  macros du repas du moment, en priorisant les aliments qui périment
  bientôt, et en suggérant des substitutions pour les ingrédients manquants.
- **Recettes de base** : 10 recettes classiques de nutrition sportive.
- **Journal & Suivi** : historique des repas loggés et détection automatique
  de carences récurrentes (protéines, lipides, fibres) sur les 7 derniers
  jours.

## Structure du code

```
app.py                      interface Streamlit uniquement
meal_planner/
  models.py                 structures de données (dataclasses)
  macros.py                 calcul des besoins caloriques et macros par profil/repas
  recipes_data.py           base des 10 recettes
  substitutions.py          table de substitutions d'ingrédients
  suggestions.py            moteur de suggestion (macros + péremption + substitutions)
  tracking.py               agrégation 7 jours glissants et détection de carences
  storage.py                persistance SQLite (profil, inventaire, journal)
```
