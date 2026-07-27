# 🥗 Assiette — planificateur de repas & macronutriments

Application locale de planification de repas : elle calcule vos besoins, les
répartit sur la journée, propose des plats à partir de ce que vous avez dans
vos placards (en privilégiant ce qui périme le plus tôt) et détecte les
déséquilibres qui reviennent sur la durée.

Tout tourne sur votre machine, sans compte ni connexion : les données restent
dans un fichier SQLite local.

---

## Démarrage

```bash
pip install -r requirements.txt
streamlit run app.py
```

Sous Windows, un double-clic sur `lancer.bat` suffit (installation des
dépendances comprise). L'application s'ouvre sur <http://localhost:8501>.

Premier lancement : renseignez l'onglet **Profil**, puis remplissez
**Mes aliments** (un bouton charge un garde-manger d'exemple pour essayer
immédiatement).

### Tests

```bash
python -m unittest discover -s tests -v
```

41 tests couvrent le calcul des besoins, la règle FEFO du garde-manger, le
moteur de suggestion, les substitutions, la détection de carences et la
persistance. Aucune dépendance de test : la bibliothèque standard suffit.

---

## Les cinq écrans

| Écran | Ce qu'on y fait |
| --- | --- |
| 🏠 **Aujourd'hui** | Où j'en suis, ce qu'il reste à manger, idées repas par repas |
| 🍽️ **Suggestions** | Plats adaptés à un repas précis, ou journée complète en un clic |
| 🧺 **Mes aliments** | Garde-manger, quantités et dates de péremption |
| 📈 **Suivi** | Historique, graphiques et alertes sur 7 jours glissants |
| 👤 **Profil** | Poids, taille, âge, sexe, activité, objectif, nombre de repas |

---

## Architecture

Séparation stricte entre la logique métier et l'interface : le paquet
`mealplanner` n'importe jamais Streamlit et reste utilisable depuis un script
ou un autre front.

```
Opus5/
├── app.py                      point d'entrée Streamlit (navigation)
├── mealplanner/                LOGIQUE MÉTIER — aucune dépendance à l'UI
│   ├── models.py               structures de données (NutritionFacts, Profile…)
│   ├── foods.py                ~60 aliments : macros + fibres + micronutriments
│   ├── recipes.py              10 recettes, macros dérivées des aliments
│   ├── nutrition.py            besoins caloriques, macros, répartition par repas
│   ├── pantry.py               garde-manger, règle FEFO, urgence de péremption
│   ├── suggester.py            moteur de suggestion (score composite)
│   ├── substitutions.py        remplacement d'un ingrédient manquant
│   ├── analytics.py            détection de carences sur 7 jours glissants
│   └── storage.py              persistance SQLite (seule couche qui parle SQL)
├── ui/                         INTERFACE — seule couche qui importe Streamlit
│   ├── shared.py               accès au store, mise en forme, composants communs
│   ├── page_today.py           🏠 Aujourd'hui
│   ├── page_suggest.py         🍽️ Suggestions
│   ├── page_pantry.py          🧺 Mes aliments
│   ├── page_history.py         📈 Suivi
│   └── page_profile.py         👤 Profil
├── tests/test_mealplanner.py   41 tests unittest
└── data/mealplanner.db         base locale (créée au premier lancement, ignorée par git)
```

---

## Choix techniques

### Pourquoi Python + Streamlit

L'application est à 90 % du calcul (besoins énergétiques, optimisation de
portions, agrégations sur fenêtre glissante) et à 10 % de la mise en forme.
Streamlit donne des formulaires, des tableaux éditables et des graphiques sans
écrire une ligne de front-end, et se lance avec une seule commande. Electron
aurait imposé un bundle de plusieurs centaines de Mo et un second langage pour
un gain d'ergonomie nul dans un usage personnel local.

### Pourquoi SQLite plutôt qu'un JSON

L'historique des repas est relationnel et interrogé par plage de dates
(« les 7 derniers jours »), ce que SQLite fait nativement et sans tout charger
en mémoire. La base est transactionnelle — une fermeture brutale ne corrompt
pas le fichier, contrairement à une réécriture complète de JSON. Le module
`sqlite3` est dans la bibliothèque standard : zéro dépendance ajoutée, et un
seul fichier à sauvegarder ou supprimer.

### Les macros des recettes ne sont jamais codées en dur

Chaque recette est une liste d'ingrédients ; ses valeurs nutritionnelles sont
recalculées depuis `foods.py`. Une correction dans la base d'aliments se
propage partout, et une recette ne peut pas diverger de son contenu réel.

### Les féculents sont exprimés crus

Un placard contient du riz cru, pas du riz cuit. Le garde-manger et les
recettes parlent donc le même langage, ce qui évite la principale source
d'erreur de ce type d'application.

---

## Comment ça marche, en détail

### 1. Des besoins qui dépendent vraiment du profil

```
Mifflin-St Jeor → métabolisme de base
      × facteur d'activité (1,20 sédentaire … 1,90 athlète) → dépense totale
      × ajustement de l'objectif (−20 % sèche … +15 % prise de masse) → calories
```

Les protéines sont ensuite ancrées **sur le poids de corps en g/kg**, jamais sur
un pourcentage de l'énergie. C'est ce qui crée une différence réelle entre les
profils : un sédentaire en maintien reçoit 1,0 g/kg, un sportif en sèche 2,4 g/kg.
Les lipides prennent une part de l'énergie (25 à 33 % selon l'objectif) avec un
plancher de 0,8 g/kg ; les glucides absorbent le reste.

Les jeux d'objectifs sont **disjoints** : « prise de masse » et « sèche »
n'apparaissent qu'à partir de 3 séances par semaine, « maintien du poids » et
« perte de poids » seulement en dessous.

Exemple, homme de 80 kg / 180 cm / 28 ans :

| Profil | Calories | P | G | L |
| --- | --- | --- | --- | --- |
| Sédentaire, maintien | 2 148 | 80 g | 280 g | 79 g |
| Sportif, maintien | 3 088 | 144 g | 412 g | 96 g |
| Sportif, prise de masse | 3 551 | 160 g | 506 g | 99 g |
| Sportif, sèche | 2 470 | 192 g | 271 g | 69 g |

### 2. Une répartition par repas, pas un total brut

Chaque macro est répartie **indépendamment** sur les repas selon des poids
propres, puis normalisée : la somme des repas redonne exactement l'objectif du
jour, macro par macro. Les glucides sont concentrés le matin et sur la
collation, les lipides décalés vers le soir, les protéines réparties
régulièrement. L'énergie de chaque repas est recalculée depuis ses macros, donc
toujours cohérente.

### 3. Suggestion de plats

Pour chaque recette, l'application balaie les tailles de portion de 0,5 à 2,0
(pas de 0,05) et retient celle qui maximise :

```
score = 0,50 × adéquation aux macros du repas
      + 0,28 × couverture par le garde-manger
      + 0,22 × urgence de péremption des ingrédients utilisés
      − 0,10 si la recette a été mangée dans les 2 derniers jours
```

La couverture est pondérée par la part d'énergie de chaque ingrédient : manquer
150 g de poulet pèse bien plus lourd que manquer 8 g d'huile. Comme la
couverture dépend elle-même de la portion, les deux sont évaluées ensemble.

### 4. Priorisation des aliments périssables

Un même aliment peut exister en plusieurs lots avec des dates différentes. Les
lots sont consommés **du plus proche de la péremption au plus lointain**
(FEFO), et chaque lot porte un score d'urgence continu :

```
urgence = 0                       si aucune date renseignée, ou > 7 jours
        = (7 − jours restants)/7  entre 0 et 7 jours
        = 1                       si périme aujourd'hui
```

L'urgence d'une recette est la moyenne de celle de ses ingrédients, pondérée
par la quantité réellement prélevée. Ne pas renseigner de date vaut 0 : ignorer
une information ne pénalise ni n'avantage aucune recette. Les produits périmés
sont exclus des suggestions et signalés à part.

### 5. Substitutions

Quand un ingrédient manque, l'application cherche un remplaçant dans cet ordre :
un équivalent culinaire curé à la main **déjà présent chez vous**, sinon
l'aliment de la même catégorie au profil de macros le plus proche, sinon un
équivalent à acheter. La quantité est calée sur le nutriment dominant de
l'aliment manquant (protéines pour une viande, glucides pour un féculent,
lipides pour une huile). Les conversions aberrantes sont rejetées, et un même
aliment n'est jamais proposé deux fois dans la même recette.

### 6. Détection de carences sur 7 jours glissants

Un écart ponctuel n'est pas un problème ; une habitude en est un. Pour chaque
nutriment suivi (calories, protéines, glucides, lipides, fibres, fer, calcium,
vitamine C, magnésium, oméga-3), l'application compare l'apport quotidien à
l'objectif et ne remonte une alerte que si l'écart touche **au moins 60 % des
journées renseignées**, avec un minimum de 3 journées. En dessous, elle affiche
les moyennes mais ne diagnostique rien.

La journée en cours est écartée du diagnostic tant qu'elle compte moins de
repas que les journées précédentes : sans cela, un petit-déjeuner logué à 8 h
ferait apparaître un déficit sur tous les nutriments.

Deux alertes de comportement complètent le tableau : apports trop irréguliers
d'un jour à l'autre (écart-type > 25 % de la moyenne) et monotonie (un même
plat au-delà de 40 % des repas). Chaque alerte est accompagnée d'un conseil et,
pour les micronutriments, des aliments les plus denses de la base — classés par
teneur **pour 100 kcal**, pour ne pas proposer que des aliments très caloriques.

---

## Ce qui reste hors périmètre

- Les recettes sont un socle de 10 plats classiques, pas un livre de cuisine.
- Une saisie libre de repas ne renseigne que calories et macros : elle ne
  compte pas dans la détection de carences en vitamines et minéraux, et
  l'interface le dit.
- Les valeurs nutritionnelles sont des ordres de grandeur issus des tables de
  composition usuelles ; elles ne remplacent pas un suivi diététique.
