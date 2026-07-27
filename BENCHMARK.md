# Benchmark Opus 5 vs Sonnet 5 — planificateur de repas

Évaluation d'un run par modèle sur un brief identique. Méthode : inventaire, lecture
intégrale des 32 fichiers source, exécution réelle des deux applications, et
vérification des règles métier par appel direct à la logique des deux projets sur
des cas identiques.

Environnement : Windows 11, Python 3.14.2, Streamlit 1.60.0, pandas 3.0.0.
Date de référence des calculs : 2026-07-27.

---

## 1. Verdict en trois phrases

Opus5 l'emporte nettement (4,7 contre 2,35 sur 5), et l'écart ne vient pas du volume
de code mais de la solidité des règles métier : sa répartition par repas est exacte à
10⁻⁴ g près là où celle de Sonnet5 annonce un petit-déjeuner à 888 kcal dont les macros
en valent 961, et son moteur de suggestion exclut les aliments périmés là où Sonnet5
leur accorde le **plus gros bonus de priorité** et les recommande en tête de liste.
Sonnet5 produit une application qui démarre, ne plante pas et couvre les cinq
fonctionnalités dans leur principe, avec 4,5 fois moins de code — mais deux d'entre
elles ne fonctionnent que partiellement (aucune mise à l'échelle des portions, aucun
micronutriment dans la détection de carences) et l'absence totale de tests laisse
passer trois bugs à conséquence utilisateur directe.
Sur un seul critère les deux projets sont réellement à égalité : les besoins
journaliers d'un homme de 80 kg sportif en prise de masse — 3551 kcal / 160 P / 506 G
/ 99 L — sont **identiques au kcal près**, les deux modèles ayant choisi la même
chaîne Mifflin-St Jeor → facteur d'activité → g/kg de protéines.

---

## 2. Tableau de scores

| Critère | Poids | Opus5 | Sonnet5 | Pondéré Opus5 | Pondéré Sonnet5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Conformité au brief | 25 % | 5,0 | 3,0 | 1,250 | 0,750 |
| Justesse des règles métier | 25 % | 4,5 | 2,0 | 1,125 | 0,500 |
| Qualité de l'architecture | 15 % | 4,5 | 3,0 | 0,675 | 0,450 |
| Robustesse | 15 % | 4,5 | 1,0 | 0,675 | 0,150 |
| Expérience utilisateur réelle | 10 % | 4,5 | 3,0 | 0,450 | 0,300 |
| Documentation et justifications | 10 % | 5,0 | 2,0 | 0,500 | 0,200 |
| **Total sur 5** | | | | **4,675** | **2,350** |

---

## 3. Tableau des fonctionnalités

| Exigence du brief | Opus5 | Sonnet5 | Commentaire |
| --- | :---: | :---: | --- |
| Formulaire poids/taille/âge/sexe/activité | ✅ | ✅ | Les deux : Mifflin-St Jeor, 5 niveaux d'activité, mêmes coefficients 1,20→1,90. |
| Besoins caloriques et macros adaptés au profil | ✅ | 🟡 | Sonnet5 calcule juste au niveau journalier mais n'impose aucune borne : à 200 kg en sèche il renvoie **glucides = 0 g** et 440 g de protéines, soit 76 % de l'énergie ([macros.py:83](Sonnet5/meal_planner/macros.py:83)). Opus5 plafonne les protéines à 40 % et garde un plancher glucidique de 10 % ([nutrition.py:89-91](Opus5/mealplanner/nutrition.py:89)). |
| Écart CLAIR sportif vs sédentaire | ✅ | 🟡 | Écarts chiffrés identiques (×1,65 kcal, ×2,0 protéines). Mais chez Sonnet5 activité et objectif sont deux champs indépendants : « Extrêmement actif » + « Sédentaire - maintien » est sélectionnable et donne 3401 kcal à 1,0 g/kg de protéines. Opus5 rend les jeux d'objectifs **disjoints** par niveau d'activité ([nutrition.py:98-101](Opus5/mealplanner/nutrition.py:98)). |
| Répartition des macros par repas | ✅ | 🟡 | Opus5 : somme exacte à 10⁻⁴ sur 3, 4 et 5 repas, énergie de chaque repas recalculée depuis ses macros. Sonnet5 : 4 repas figés, et les kcal annoncées par repas divergent de leurs propres macros de −3,3 % à **+8,2 %**. |
| Saisie du garde-manger avec quantité | ✅ | ✅ | Opus5 : catalogue de 59 aliments, lots multiples fusionnés/distingués par date. Sonnet5 : texte libre, plus souple mais non normalisé. |
| Suggestion de plats correspondant aux macros du repas | ✅ | 🟡 | Opus5 balaie 31 tailles de portion (0,5→2,0) et affiche l'écart à la cible. Sonnet5 ne met **jamais les portions à l'échelle** : pour un déjeuner cible de 1243 kcal il propose une recette figée à 560 kcal sans jamais signaler le manque de 683 kcal. |
| Priorisation des ingrédients qui périment le plus tôt | ✅ | 🟡 | Opus5 : score d'urgence continu, FEFO, périmés exclus ; la priorisation fait effectivement changer la tête de classement (+0,0675 sur un écart initial de 0,0153). Sonnet5 : la péremption n'est qu'un départage **à nombre d'ingrédients manquants égal**, et un aliment périmé depuis 30 jours obtient un bonus de 44 contre 13 pour un aliment périmant demain. |
| Substitution d'un ingrédient manquant | ✅ | ✅ | Le brief n'exige pas de recalcul de macros. Sonnet5 renvoie des noms plausibles (29 entrées). Opus5 va plus loin : quantité convertie, disponibilité en stock, motif (59 entrées). |
| 8 à 10 recettes de base avec macros | ✅ | ✅ | 10 recettes des deux côtés. Opus5 dérive les macros de sa table d'aliments ; Sonnet5 les code en dur (cohérence énergie/macros vérifiée : ±4,2 % max, correcte). |
| Historique des repas loggés par jour | ✅ | 🟡 | Opus5 : agrégation par journée, graphiques, saisie manuelle et libre, suppression. Sonnet5 : table plate de tous les repas, **sans regroupement par jour**, sans saisie manuelle, sans suppression. |
| Carences/déséquilibres récurrents sur 7 jours glissants | ✅ | 🟡 | Opus5 surveille 10 nutriments dont 6 micronutriments, plus 2 alertes de comportement. Sonnet5 en surveille **3** (protéines, lipides, fibres) : le brief demandait explicitement « fibres, lipides, micronutriments… ». |
| Stockage local justifié | ✅ | 🟡 | SQLite des deux côtés. Opus5 justifie le choix en 8 lignes (relationnel, filtrage par plage de dates, transactionnel, zéro dépendance). Sonnet5 mentionne SQLite sans aucune justification, alors que le brief écrit « à justifier ». |
| Stack au choix avec justification | ✅ | ❌ | Opus5 justifie Python+Streamlit et écarte explicitement Electron. Le README de Sonnet5 ne contient **aucune** justification de stack. |
| Interface simple, calculs invisibles | ✅ | ✅ | Les deux y parviennent : l'utilisateur ne voit que des résultats. |
| Séparation logique métier / interface | ✅ | 🟡 | Opus5 : `mealplanner/` n'importe jamais Streamlit, `ui/` est la seule couche qui le fait. Sonnet5 : `tracking.py` importe `storage` ([tracking.py:11](Sonnet5/meal_planner/tracking.py:11)), et `app.py` décrémente le garde-manger dans un handler de bouton ([app.py:191-194](Sonnet5/app.py:191)). |

---

## 4. Métriques objectives

| Métrique | Opus5 | Sonnet5 |
| --- | ---: | ---: |
| Lignes de code réelles (hors blancs, commentaires, docstrings) | 2 977 | 662 |
| — dont logique métier | 1 685 | 470 |
| — dont interface | 903 | 192 |
| — dont tests | 389 | 0 |
| Lignes totales | 3 821 | 877 |
| Lignes de docstrings | 232 | 62 |
| Lignes de commentaires | 99 | 26 |
| Ratio documentation / code | 11,1 % | 13,3 % |
| Modules Python | 19 | 9 |
| — modules métier | 9 | 7 |
| — modules d'interface | 7 | 1 (monolithe de 192 LOC) |
| Aliments en base | 59 | 0 (aucune table) |
| Nutriments modélisés par aliment | 10 | — |
| Recettes | 10 | 10 |
| Ingrédients moyens par recette | 5,3 | 3,8 |
| Étapes de préparation fournies | oui | non |
| Entrées de substitution | 59 | 29 |
| Nutriments surveillés en détection de carences | 10 | 3 |
| Configurations de repas | 3 (3/4/5 repas) | 1 (4 repas figés) |
| Tests | 41, tous verts en 0,017 s | 0 |
| Temps de démarrage serveur (froid → HTTP 200) | 1,14 s | 1,08 s |
| Import de la logique métier (moyenne de 3) | 75,7 ms | 43,3 ms |
| Dépendances externes | `streamlit`, `pandas` | `streamlit` |
| Imports inutilisés (pyflakes) | 1 | 1 |
| Données utilisateur committées dans git | non | non |

Les deux `.gitignore` excluent correctement `data/` et `*.db` ; `git ls-files` confirme
qu'aucune base n'est versionnée dans l'un ou l'autre projet.

---

## 5. Analyse par critère

### 5.1 Conformité au brief — Opus5 5,0 / Sonnet5 3,0

Trois des cinq fonctionnalités sont complètes des deux côtés (profil, recettes de base,
substitutions). Les deux autres divergent nettement.

**Suggestion de plats.** Opus5 traite le problème comme une optimisation sur le couple
(recette, portion) :

```python
# Opus5/mealplanner/suggester.py:181-186
for portions in grid:                     # 0,50 → 2,00 par pas de 0,05
    evaluation = _evaluate(recipe, portions, lots, weights, base_facts, target)
    if best is None or evaluation[0] > best[0]:
        best = (*evaluation, portions)
```

Sonnet5 traite le même problème comme un filtre suivi d'un tri :

```python
# Sonnet5/meal_planner/suggestions.py:90
scored.sort(key=lambda s: (len(s["missing_ingredients"]), s["score"]))
```

Conséquence mesurée sur le même profil (déjeuner, cible 1243 kcal chez Sonnet5,
1160 kcal chez Opus5) : Sonnet5 propose « Riz - Poulet - Brocolis » à 560 kcal, soit
45 % de la cible, sans le signaler. Opus5 propose « Riz, poulet & brocolis » à
1,20 portion et affiche l'écart résiduel en clair.

**Suivi.** La page « Journal & Suivi » de Sonnet5 contient exactement deux blocs : les
alertes et une table plate de tous les repas ([app.py:217-243](Sonnet5/app.py:217)).
Il n'existe aucune vue « où j'en suis aujourd'hui », aucun regroupement par jour, aucun
graphique, aucune saisie manuelle et aucune suppression d'entrée. Le brief demandait un
« historique des repas loggés **par jour** ».

### 5.2 Justesse des règles métier — Opus5 4,5 / Sonnet5 2,0

#### Besoins journaliers — homme 80 kg / 180 cm / 28 ans

| Cas | Moteur | kcal | P | G | L | P g/kg | kcal recalculées depuis les macros |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sédentaire-maintien | Opus5 | 2 148 | 80 | 280 | 79 | 1,00 | 2 148 (+0,0) |
| | Sonnet5 | 2 148 | 80 | 296 | 72 | 1,00 | 2 152 (+4,0) |
| sportif-prise de masse | Opus5 | 3 551 | 160 | 506 | 99 | 2,00 | 3 551 (+0,0) |
| | Sonnet5 | 3 551 | 160 | 506 | 99 | 2,00 | 3 555 (+4,0) |
| sportif-sèche | Opus5 | 2 470 | 192 | 271 | 69 | 2,40 | 2 470 (+0,0) |
| | Sonnet5 | 2 470 | 176 | 287 | 69 | 2,20 | 2 473 (+3,0) |

**Sur ce tableau, les deux projets sont équivalents.** Les écarts résiduels de 3-4 kcal
chez Sonnet5 sont de simples arrondis à l'entier, sans conséquence. L'écart entre
profils est marqué des deux côtés et satisfait le brief :

| Comparaison | Opus5 | Sonnet5 |
| --- | --- | --- |
| prise de masse / sédentaire | kcal ×1,65 (+1 403) · protéines ×2,00 (+80 g) | kcal ×1,65 (+1 403) · protéines ×2,00 (+80 g) |
| sèche / sédentaire | kcal ×1,15 (+322) · protéines ×2,40 (+112 g) | kcal ×1,15 (+322) · protéines ×2,20 (+96 g) |
| sèche / prise de masse | kcal ×0,70 (−1 081) · protéines ×1,20 (+32 g) | kcal ×0,70 (−1 081) · protéines ×1,10 (+16 g) |

La différence apparaît sur les **bornes de sécurité**. Opus5 en pose trois
([nutrition.py:89-91](Opus5/mealplanner/nutrition.py:89)) et les applique
([nutrition.py:152-166](Opus5/mealplanner/nutrition.py:152)) : protéines ≤ 40 % de
l'énergie, lipides ≥ 0,8 g/kg, glucides ≥ 10 % de l'énergie. Sonnet5 n'en pose aucune
et calcule les glucides comme un simple reliquat écrêté à zéro
([macros.py:83](Sonnet5/meal_planner/macros.py:83)) :

| Profil limite | Opus5 | Sonnet5 |
| --- | --- | --- |
| femme 40 kg / 140 cm / 90 ans, sèche | 653 kcal · P 64 · G 27 · **L 32 (0,80 g/kg)** | 637 kcal · P 88 · G 32 · **L 18 (0,45 g/kg)** |
| femme 150 kg, sèche | 1 896 kcal · P 190 · **G 47** · L 105 | 1 849 kcal · P 330 · **G 17** · L 51 |
| femme 200 kg, sèche | 2 388 kcal · P 239 · **G 60** · L 133 | 2 329 kcal · P 440 · **G 0** · L 65 |

Le cas à 200 kg est le plus parlant : Sonnet5 recommande un régime à zéro glucide avec
76 % de l'énergie sous forme de protéines. Ce n'est pas seulement une valeur aberrante,
c'est une valeur qui se propage : `_macro_distance` masque la cible nulle par un
`or 1` ([suggestions.py:21](Sonnet5/meal_planner/suggestions.py:21)), si bien que le
terme glucidique devient `|68 − 1| / 1 = 68` et écrase tous les autres — le classement
des suggestions devient un tri par teneur croissante en glucides.

#### La somme des macros par repas redonne-t-elle le total ?

Opus5, sur les trois configurations (3, 4 et 5 repas), écart mesuré sur chaque macro :

```
ÉCART : kcal +0.0000  P +0.0000  G +0.0000  L +0.0000
```

C'est exact par construction : chaque macro est normalisée indépendamment sur la somme
des poids du plan de repas, puis l'énergie du repas est **recalculée** depuis ses macros
([nutrition.py:257-268](Opus5/mealplanner/nutrition.py:257)).

Sonnet5 boucle correctement au niveau journalier (ses ratios somment à 1,0 par macro),
mais les kcal de chaque repas sont un **quatrième pourcentage indépendant** au lieu
d'être dérivées des trois autres ([macros.py:104](Sonnet5/meal_planner/macros.py:104)) :

| Repas | kcal annoncées | kcal des macros annoncées | Écart |
| --- | ---: | ---: | ---: |
| petit_dejeuner | 888 | 961 | **+73 (+8,2 %)** |
| dejeuner | 1 243 | 1 202 | −41 (−3,3 %) |
| diner | 1 065 | 1 043 | −22 (−2,1 %) |
| collation | 355 | 358 | +3 (+0,8 %) |

L'utilisateur lit littéralement, à l'écran : « Petit-déjeuner — 888 kcal, 32 g
protéines, 152 g glucides, 25 g lipides ». Ces quatre nombres sont mutuellement
impossibles. C'est aussi cette cible incohérente qui sert de référence au moteur de
suggestion.

#### Priorisation de la péremption

Protocole : deux recettes également réalisables, on fait périmer un ingrédient de celle
qui est **deuxième** au classement, et on regarde si la tête change.

Opus5 — écart initial entre les deux recettes : **+0,0153** en faveur du thon/quinoa.

```
sans date          1. Quinoa, thon & haricots verts   0.6201  (urgence 0.000)
                   2. Riz, poulet & brocolis          0.6048  (urgence 0.000)
poulet périme J+1  1. Riz, poulet & brocolis          0.6723  (urgence 0.307)   <- CHANGEMENT
                   2. Quinoa, thon & haricots verts   0.6201
```

Gain apporté par la péremption : **+0,0675**, soit 4,4 fois l'écart initial. La
priorisation est donc réellement décisive, pas décorative. Symétriquement, le thon
périmé depuis 30 jours fait **reculer** sa recette (couverture 1,000 → 0,750, urgence
0,000) parce que les lots périmés sont exclus du stock
([pantry.py:79-80](Opus5/mealplanner/pantry.py:79)).

Sonnet5, même protocole :

```
thon périme J+1        1. Pâtes - Thon - Tomates   1.2927  (bonus urgence 13.0)
thon périmé DEPUIS 30j 1. Pâtes - Thon - Tomates  -0.2573  (bonus urgence 44.0)  <- en tête
```

Deux problèmes distincts, tous deux vérifiés par exécution :

1. **Les aliments périmés obtiennent le plus gros bonus.** `urgency_bonus +=
   max(0, EXPIRATION_HORIZON_DAYS - days_left)` ([suggestions.py:53](Sonnet5/meal_planner/suggestions.py:53))
   n'est borné qu'en bas. Pour `days_left = −30` le bonus vaut 44 contre 13 pour
   `days_left = 1`. Plus l'aliment est périmé depuis longtemps, plus l'application le
   recommande — et l'interface l'étiquette « ⏳ utilise des aliments à péremption
   proche » ([app.py:172](Sonnet5/app.py:172)). Rien, nulle part, n'exclut un aliment
   périmé du stock disponible.
2. **L'urgence ne peut jamais franchir un palier de faisabilité**, puisque la clé de tri
   primaire est le nombre d'ingrédients manquants
   ([suggestions.py:90](Sonnet5/meal_planner/suggestions.py:90)). Une recette qui
   sauverait trois aliments périmant demain mais à laquelle il manque un ingrédient
   restera derrière une recette complète qui n'en sauve aucun.

#### Détection de carences

| Scénario | Opus5 | Sonnet5 |
| --- | --- | --- |
| 7 jours pile à l'objectif | aucune alerte | aucune alerte |
| 6 jours corrects + 1 journée à 20 % | **aucun déficit** ; une note « info » de régularité | aucune alerte |
| 7 jours carencés (L 45 %, fibres 30 %, micros 20-40 %) | 8 alertes : lipides, fibres, fer, calcium, vitamine C, magnésium, oméga-3 (toutes « critique ») + excès de glucides | 2 alertes : lipides, fibres |
| 4 journées complètes + journée en cours à 1 repas | aucune alerte, journée en cours **explicitement exclue** (`day_in_progress=True`) | aucune alerte |

Aucun des deux ne crie au loup sur une journée isolée, et les deux détectent une
carence franche en lipides et en fibres : **sur ce point précis les deux sont
corrects**. La différence est de couverture. Opus5 surveille
`kcal, protein, carbs, fat, fiber, iron, calcium, vitamin_c, magnesium, omega3` et
formule le diagnostic avec un chiffre (« en retrait d'environ 70 % sur la période,
7 journées sur 7 sous l'objectif »), un conseil et des aliments sources triés par
densité **pour 100 kcal** ([analytics.py:224](Opus5/mealplanner/analytics.py:224)).
Sonnet5 surveille `protein_g, fat_g, fiber_g`
([tracking.py:19-23](Sonnet5/meal_planner/tracking.py:19)) : les micronutriments
nommément cités par le brief sont hors de portée, faute de table d'aliments qui les
contienne.

Nuance à porter au crédit de Sonnet5 : sur le cas « journée en cours incomplète », il
donne la bonne réponse — non par un traitement dédié, mais parce que son seuil
`min(4, days_logged)` est assez conservateur ([tracking.py:67](Sonnet5/meal_planner/tracking.py:67)).
Le résultat est correct ; le raisonnement est implicite.

#### Cohérence énergie / macros des recettes

| | Opus5 (dérivées des ingrédients) | Sonnet5 (codées en dur) |
| --- | --- | --- |
| Écart max entre kcal annoncées et 4P+4G+9L | −3,7 % | −4,2 % |
| Écart médian | −1,9 % | −0,9 % |

**Les deux sont corrects sur ce point**, et Sonnet5 est même très légèrement plus
cohérent en médiane malgré des valeurs saisies à la main. L'avantage d'Opus5 n'est pas
la précision mais l'impossibilité structurelle de dériver : les macros sont recalculées
depuis `foods.py` à chaque appel ([recipes.py:227-229](Opus5/mealplanner/recipes.py:227)),
donc une recette ne peut pas contredire ses ingrédients.

La table d'aliments d'Opus5 présente en revanche quelques écarts réels (médiane 5,2 %
sur 59 aliments, ce qui s'explique largement par les fibres comptées dans les glucides
à 4 kcal/g). Les pires cas ne s'expliquent pas tous ainsi :

| Aliment | kcal annoncées | 4P+4G+9L | Écart |
| --- | ---: | ---: | ---: |
| concombre | 15,0 | 18,1 | **20,7 %** |
| mais_doux | 86,0 | 100,0 | 16,3 % |
| carotte | 41,0 | 34,6 | 15,6 % |

Le concombre à 3,6 g de glucides pour 100 g est trop élevé (les tables usuelles donnent
~2 g). L'impact pratique est négligeable, mais c'est une imprécision de donnée que le
test d'auto-cohérence du projet ne rattrape pas, sa tolérance étant fixée à 25 %
([test_mealplanner.py:97-98](Opus5/tests/test_mealplanner.py:97)).

#### Confusion cru / cuit

Opus5 tranche explicitement et le rend visible dans le **nom affiché** de l'aliment :
« Riz blanc (cru) », « Pâtes (crues) », « Quinoa (cru) », « Patate douce (crue) ». Le
garde-manger et les recettes parlent donc le même langage, et l'utilisateur ne peut pas
se tromper au moment de la saisie.

Sonnet5 ne tranche nulle part. En relisant ses recettes avec une table d'aliments crus,
l'incohérence apparaît :

| Recette | Annoncé | Ingrédients lus CRUS | Ratio |
| --- | ---: | ---: | ---: |
| Quinoa - Pois chiches - Légumes | 540 kcal / 78 G | 920 kcal / 141 G | **1,70×** |
| Riz - Poulet - Brocolis | 560 kcal / 68 G | 927 kcal / 124 G | **1,66×** |
| Riz - Boeuf haché - Poivrons | 610 kcal / 68 G | 856 kcal / 123 G | 1,40× |
| Pâtes - Thon - Tomates | 580 kcal / 78 G | 793 kcal / 111 G | 1,37× |
| Omelette - Fromage - Pain complet | 520 kcal / 38 G | 535 kcal / 35 G | 1,03× |

Les macros ne sont donc cohérentes que sous l'hypothèse **cuit** — hypothèse qui n'est
écrite nulle part. Or l'utilisateur saisit son garde-manger en texte libre : il tape
« riz, 1000 g » en pensant à son paquet de riz cru. Quand il logge le plat,
[app.py:194](Sonnet5/app.py:194) retire 150 g de ce paquet pour une recette qui n'a
besoin que d'environ 50 g de riz cru. Le stock et les macros loggées sont faux tous les
deux, dans des sens opposés.

*Réserve d'honnêteté : ce contrôle utilise la table d'aliments d'Opus5 comme référence
externe, faute de table dans Sonnet5. C'est structurellement favorable à Opus5 pour ce
test précis. L'ambiguïté cru/cuit reste cependant démontrée indépendamment : rien dans
le code ni la documentation de Sonnet5 ne précise l'état des féculents, et les ratios
de 1,66× et 1,70× sur les deux plats les plus féculents ne sont pas un artefact de
table.*

#### Substitutions

| Cas | Opus5 | Sonnet5 |
| --- | --- | --- |
| 150 g poulet (dinde en stock) | Escalope de dinde **160 g**, en stock, « apport protéique équivalent » | `['dinde', 'tofu', 'poisson blanc']` |
| 80 g riz (quinoa en stock) | Quinoa **95 g**, en stock, « même rôle de source de glucides » | `['quinoa', 'pâtes', 'boulgour']` |
| 10 g huile d'olive (salade en stock) | Huile de colza **10 g**, à acheter | `['huile de colza', 'huile de tournesol']` |
| 150 g saumon (rien en stock) | Thon au naturel **115 g**, à acheter | `['thon', 'maquereau', 'poulet']` |
| 120 g œufs (tofu en stock) | Tofu ferme **100 g**, en stock | `["blancs d'oeufs", 'tofu soyeux']` |

Les propositions des deux sont plausibles en cuisine. Les quantités d'Opus5 sont
cohérentes : 150 g de poulet à 31 g P/100 g ≈ 160 g de dinde à 29 g P/100 g ;
80 g de riz à 77,2 g G ≈ 95 g de quinoa à 64,2 g G. Le garde-fou anti-conversion
absurde fonctionne : proposer de la salade verte pour 10 g d'huile est rejeté
([substitutions.py:145-146](Opus5/mealplanner/substitutions.py:145)).

Sonnet5 respecte la lettre du brief, qui n'exige pas de recalcul. Il ne dit simplement
jamais **combien**. Une remarque de fond : « saumon → poulet » fait perdre l'intérêt
oméga-3 de la recette sans le signaler.

### 5.3 Architecture — Opus5 4,5 / Sonnet5 3,0

Opus5 applique une séparation stricte, et elle tient à la vérification : aucun fichier
de `mealplanner/` n'importe `streamlit`, et `storage.py` est le seul module qui contient
du SQL. `NutritionFacts` est une abstraction réussie — un dataclass immuable qui
supporte `+`, `-`, `*` et `sum()` ([models.py:72-104](Opus5/mealplanner/models.py:72)) —
et qui explique pourquoi agréger 10 nutriments ne coûte pas plus cher que d'en agréger 4
dans tout le reste du code.

Sonnet5 est propre à l'échelle du module et ne contient **aucun code mort** (contre
4 membres publics inutilisés chez Opus5 : `Lot.critical`, `Substitution.describe`,
`Store.reset`, `NutritionFacts.rounded`). Trois réserves structurelles :

1. `app.py` est un monolithe de 192 LOC en `if/elif` sur `page`, avec effets de bord au
   niveau module (`storage.init_db()` ligne 20, `st.stop()` ligne 40). Ajouter une page
   signifie allonger la chaîne.
2. `tracking.py` importe `storage` ([tracking.py:11](Sonnet5/meal_planner/tracking.py:11))
   et appelle `storage.get_logs()` à l'intérieur d'`analyze_deficiencies`. La logique
   métier va donc chercher ses données elle-même, dans un fichier au chemin figé. J'ai
   dû monkeypatcher `storage.DB_PATH` pour pouvoir tester cette fonction — c'est le
   symptôme direct du couplage.
3. La logique métier fuit dans l'interface : la décrémentation du garde-manger après un
   repas est écrite dans le handler du bouton ([app.py:191-194](Sonnet5/app.py:191)),
   avec sa propre règle de correspondance des aliments, au lieu d'être une opération du
   domaine. Chez Opus5 la même chose est une méthode `Store.consume()` appliquant FEFO
   ([storage.py:173-199](Opus5/mealplanner/storage.py:173)).

### 5.4 Robustesse — Opus5 4,5 / Sonnet5 1,0

Opus5 : **41 tests, 41 verts, 0,017 s**, bibliothèque standard uniquement. Le chiffre
annoncé dans le README est exact. Sortie réelle :

```
Ran 41 tests in 0.017s

OK
```

Ils couvrent ce qui compte : bornes de Mifflin, disjonction des jeux d'objectifs,
somme des repas, FEFO, exclusion des périmés, substitutions absurdes rejetées,
non-déclenchement sur une journée isolée, exclusion de la journée en cours, aller-retour
de persistance. Ce ne sont pas des tests de façade.

Sonnet5 : **aucun test**. Les trois défauts suivants seraient tombés au premier test.

**Correspondance de noms par sous-chaîne bidirectionnelle**
([suggestions.py:31](Sonnet5/meal_planner/suggestions.py:31)) :

```python
if food.name == normalized or normalized in food.name or food.name in normalized:
```

Résultats vérifiés :

| Ingrédient cherché | Aliment en stock | Résultat |
| --- | --- | --- |
| `riz` | `chorizo` | **MATCH** |
| `lait` | `riz au lait` | **MATCH** |
| `lait` | `lait de coco` | MATCH |
| `huile d'olive` | `huile` | MATCH |
| `poulet` | `blanc de poulet` | MATCH |

Les deux derniers sont voulus et utiles. Le premier ne l'est pas : un utilisateur qui a
du chorizo se voit annoncer qu'il a du riz, la recette est déclarée réalisable, et le
log du repas retire **150 g de chorizo** de son inventaire.

**Un aliment réparti sur plusieurs lignes n'est vu que partiellement.** `add_food` fait
toujours un `INSERT` ([storage.py:96-100](Sonnet5/meal_planner/storage.py:96)) et
`find_matching_food` renvoie la première correspondance. Vérifié :

```
inventaire : riz 100 g (périme J+3), riz 900 g (sans date), poulet 400 g, ...
total réellement possédé : 1000 g de riz
find_matching_food('riz') renvoie : riz 100 g   -> seul le PREMIER lot est vu
Riz - Poulet - Brocolis réalisable ? False | manquants: ['riz']
```

Avec un kilo de riz dans le placard, l'application déclare qu'il en manque. Opus5, dans
la même situation, agrège les lots par FEFO (`draw(150 g)` sur 100+900 → pris 150 g,
manquant 0 g).

**Aucune borne sur les macros**, déjà chiffré en 5.2 (glucides = 0 g à 200 kg).

Côté cas limites, les deux tiennent debout : garde-manger vide, cible nulle,
type de repas inconnu — aucune exception dans les deux projets. Opus5 se replie sur le
catalogue complet pour un repas inconnu ; Sonnet5 renvoie une liste vide (non
atteignable depuis son interface, les types de repas y étant figés).

Réserves sur Opus5 : aucun test ne couvre la couche `ui/` ; `_apply_edits` associe les
lignes du tableau éditable aux lots par un `zip` positionnel
([page_pantry.py:149](Opus5/ui/page_pantry.py:149)), ce qui repose sur une hypothèse
d'ordre stable ; et `_evaluate` appelle `draw()` indépendamment par ingrédient, ce qui
compterait deux fois le stock si un aliment apparaissait deux fois dans une recette —
bug latent, aucune des 10 recettes n'est concernée aujourd'hui.

### 5.5 Expérience utilisateur réelle — Opus5 4,5 / Sonnet5 3,0

Les deux applications ont été lancées (ports 8501 et 8502), parcourues via
`streamlit.testing` sur un scénario complet, puis vérifiées visuellement dans un
navigateur. **Aucune des deux n'a produit d'exception, d'écran vide ou de crash.** Le
temps de démarrage est identique (1,14 s contre 1,08 s).

Opus5 rend, sur la page d'accueil : les 4 totaux du jour avec écart à l'objectif, trois
barres de progression, une carte par repas avec un statut ✅/⬜ et l'objectif du repas,
la liste des aliments à consommer en priorité (« Blanc d'œuf — 300 g (périme demain) »)
et la tendance 7 jours. La complexité est effectivement cachée : la formule de score
n'apparaît jamais, seulement des phrases comme « Utilise Blanc d'œuf, qui périme dans
1 jour(s) » ou « Apporte 182 kcal de moins que la cible : complétez avec une portion de
féculent ou un fruit ». Le bouton « Remplir avec un garde-manger d'exemple » évite dix
minutes de saisie avant de pouvoir juger l'application.

Deux réserves. D'abord, l'optimiseur de portions privilégie les protéines (poids 1,3
contre 1,0 pour les kcal, [suggester.py:39](Opus5/mealplanner/suggester.py:39)), ce qui
sur une collation de 620 kcal l'amène à s'arrêter à 0,85 portion et 438 kcal : il le dit
honnêtement, mais la suggestion reste courte de 182 kcal. Ensuite, le sélecteur
d'objectif vit à l'intérieur d'un `st.form`, où Streamlit ne redéclenche pas de rerun ;
le garde-fou [page_profile.py:76-77](Opus5/ui/page_profile.py:76) remplace alors en
silence l'objectif choisi par le défaut du nouveau niveau d'activité (choix « sèche »
avec activité « sédentaire » → enregistré en « maintien », sans message).

Sonnet5 est lisible et va droit au but. Ses pastilles de péremption colorées
(🔴 / 🟠 / 🟢 avec le nombre de jours restants) sur chaque ligne d'inventaire sont un
vrai bon point, plus immédiates que les bandeaux textuels d'Opus5. Mais il manque des
briques que l'utilisateur cherchera dès le deuxième jour : aucune vue de la progression
du jour, aucun moyen de logger un repas pris à l'extérieur, aucun moyen de supprimer une
entrée erronée, aucun regroupement de l'historique par journée, et aucune indication de
l'écart entre la recette proposée et la cible du repas. Les recettes n'ont pas d'étapes
de préparation : la page « Recettes de base » est un tableau de macros, pas un support
de cuisine.

### 5.6 Documentation et justifications — Opus5 5,0 / Sonnet5 2,0

Le README d'Opus5 fait 226 lignes et justifie chaque arbitrage : Streamlit plutôt
qu'Electron (bundle, second langage, gain nul en usage local), SQLite plutôt que JSON
(relationnel, filtrage par plage de dates, transactionnel, zéro dépendance), féculents
crus plutôt que cuits, macros dérivées plutôt que codées en dur. Il donne la formule de
score, la formule d'urgence, la règle de récurrence, un tableau d'exemple chiffré, et
une section « Ce qui reste hors périmètre » qui reconnaît ses limites.

J'ai traité ces affirmations comme des hypothèses à vérifier. Résultat :

| Affirmation du README | Vérification |
| --- | --- |
| « 41 tests » | 41 tests exécutés, 41 verts |
| « ~60 aliments » | 59 |
| « 10 recettes » | 10 |
| Tableau : sédentaire maintien 2 148 / 80 / 280 / 79 | exact |
| Tableau : sportif maintien 3 088 / 144 / 412 / 96 | exact (niveau « intense ») |
| Tableau : sportif prise de masse 3 551 / 160 / 506 / 99 | exact |
| Tableau : sportif sèche 2 470 / 192 / 271 / 69 | exact |
| « la somme des repas redonne exactement l'objectif » | écart mesuré < 10⁻⁴ |
| « les produits périmés sont exclus des suggestions » | confirmé |
| « aucune dépendance de test » | confirmé, `unittest` seul |

Aucune affirmation prise en défaut.

Le README de Sonnet5 fait 45 lignes. Il est **exact** — je n'y ai relevé aucune fausse
affirmation — mais purement descriptif. Le brief demandait explicitement une
justification de la stack et du choix de stockage : ni l'une ni l'autre n'y figure.
Aucun seuil n'est expliqué (pourquoi 14 jours d'horizon, pourquoi 0,8, pourquoi 4 jours
déficitaires), aucune limite n'est reconnue. Sa formule « en priorisant les aliments qui
périment bientôt » est vraie mais incomplète : elle priorise aussi, et davantage, les
aliments déjà périmés. À son crédit, les docstrings de module sont soignées et
expliquent l'intention (`suggestions.py`, `tracking.py`, `macros.py`), et son ratio
documentation/code est même légèrement supérieur (13,3 % contre 11,1 %).

---

## 6. Bugs et faiblesses

### 6.1 Sonnet5

**Critique**

1. **Les aliments périmés sont prioritaires au lieu d'être exclus** —
   [suggestions.py:52-53](Sonnet5/meal_planner/suggestions.py:52). Le bonus
   `max(0, 14 - days_left)` n'est borné qu'en bas : 44 pour un aliment périmé depuis
   30 jours, 13 pour un aliment périmant demain. Impact : l'application place en tête de
   ses recommandations un plat à base d'un aliment périmé depuis un mois, et l'étiquette
   « ⏳ utilise des aliments à péremption proche ». Risque sanitaire réel.
2. **Aucune borne sur les macros** — [macros.py:79-84](Sonnet5/meal_planner/macros.py:79).
   Un profil de 200 kg en sèche reçoit glucides = 0 g et 440 g de protéines (76 % de
   l'énergie). Impact : recommandation nutritionnelle dangereuse, et cible nulle qui
   corrompt ensuite le classement des suggestions via le `or 1` de
   [suggestions.py:21](Sonnet5/meal_planner/suggestions.py:21).
3. **Correspondance d'aliments par sous-chaîne bidirectionnelle** —
   [suggestions.py:31](Sonnet5/meal_planner/suggestions.py:31). « riz » correspond à
   « chorizo », « lait » à « riz au lait ». Impact : recette déclarée réalisable à tort,
   puis 150 g de chorizo retirés de l'inventaire au moment du log
   ([app.py:194](Sonnet5/app.py:194)).

**Majeur**

4. **Un aliment saisi en plusieurs lots n'est vu qu'au premier** —
   [storage.py:96](Sonnet5/meal_planner/storage.py:96) et
   [suggestions.py:27-33](Sonnet5/meal_planner/suggestions.py:27). Vérifié : 100 g +
   900 g de riz → l'application voit 100 g et déclare le riz manquant.
5. **Aucune mise à l'échelle des portions** — [recipes_data.py](Sonnet5/meal_planner/recipes_data.py).
   Recette figée à 560 kcal pour une cible de 1243 kcal, sans que l'écart soit affiché.
   Impact : l'utilisateur qui suit les suggestions mange moitié moins que son objectif
   sans le savoir.
6. **Incohérence énergie/macros par repas** — [macros.py:104](Sonnet5/meal_planner/macros.py:104).
   Jusqu'à +8,2 % au petit-déjeuner. Impact : quatre nombres mutuellement impossibles
   affichés à l'écran, et cible faussée pour le moteur de suggestion.
7. **Micronutriments absents de la détection de carences** —
   [tracking.py:19-23](Sonnet5/meal_planner/tracking.py:19). Trois nutriments surveillés
   au lieu des « fibres, lipides, micronutriments… » demandés.
8. **Ambiguïté cru/cuit jamais levée** — [recipes_data.py](Sonnet5/meal_planner/recipes_data.py).
   Macros cohérentes seulement sous l'hypothèse « cuit », inventaire saisi en texte libre.
   Impact : stock et macros loggées faux d'un facteur ~3 sur les féculents.

**Mineur**

9. **Le tri primaire annule l'effet de la péremption entre paliers** —
   [suggestions.py:90](Sonnet5/meal_planner/suggestions.py:90).
10. **Activité et objectif indépendants** — [models.py:18-23](Sonnet5/meal_planner/models.py:18).
    « Extrêmement actif » + « Sédentaire - maintien » est sélectionnable.
11. **`get_logs` ignore un filtre partiel** — [storage.py:157](Sonnet5/meal_planner/storage.py:157) :
    `if start_date and end_date` — une seule borne fournie renvoie tout l'historique.
12. **Import inutilisé** : `dataclasses.field` — [models.py:3](Sonnet5/meal_planner/models.py:3).
13. **API dépréciée** : `use_container_width` génère un avertissement à chaque rendu
    ([app.py:212](Sonnet5/app.py:212), [app.py:243](Sonnet5/app.py:243)).

### 6.2 Opus5

**Majeur**

1. **L'objectif choisi peut être remplacé en silence** —
   [page_profile.py:76-77](Opus5/ui/page_profile.py:76). Les widgets d'un `st.form`
   ne redéclenchent pas de rerun ; si l'utilisateur change son niveau d'activité et
   choisit un objectif de l'ancienne liste, le garde-fou substitue le défaut sans le
   dire. Impact : profil enregistré différent de ce qui a été sélectionné, sans message.

**Mineur**

2. **Valeurs nutritionnelles imprécises sur quelques légumes et fruits** —
   [foods.py:70](Opus5/mealplanner/foods.py:70) (concombre, 3,6 g de glucides pour
   100 g au lieu de ~2). Écart énergie/macros de 20,7 %, sous la tolérance de 25 % du
   test d'auto-cohérence ([test_mealplanner.py:97](Opus5/tests/test_mealplanner.py:97)).
   Impact pratique négligeable.
3. **L'optimiseur de portions sous-dimensionne les gros repas** —
   [suggester.py:39](Opus5/mealplanner/suggester.py:39). Le poids protéique de 1,3
   contre 1,0 pour les kcal fait s'arrêter la collation à 438 kcal pour une cible de
   620. Signalé à l'utilisateur, mais la proposition reste courte.
4. **`zip` positionnel entre les lots et le tableau édité** —
   [page_pantry.py:149](Opus5/ui/page_pantry.py:149). Repose sur une hypothèse d'ordre
   stable de `st.data_editor`.
5. **Double comptage latent si un aliment apparaissait deux fois dans une recette** —
   [suggester.py:134-137](Opus5/mealplanner/suggester.py:134). Aucune des 10 recettes
   n'est concernée aujourd'hui.
6. **Objectif fibres élevé pour les gros mangeurs** —
   [nutrition.py:179](Opus5/mealplanner/nutrition.py:179) : 14 g/1000 kcal donne 50 g/j
   à 3551 kcal, ce qui rendra l'alerte fibres quasi permanente en prise de masse.
7. **Quatre membres publics jamais utilisés** : `Lot.critical`
   ([pantry.py:55](Opus5/mealplanner/pantry.py:55)), `Substitution.describe`
   ([substitutions.py:113](Opus5/mealplanner/substitutions.py:113)), `Store.reset`
   ([storage.py:275](Opus5/mealplanner/storage.py:275)), `NutritionFacts.rounded`
   ([models.py:87](Opus5/mealplanner/models.py:87)).
8. **Import inutilisé** : `datetime.date` — [suggester.py:20](Opus5/mealplanner/suggester.py:20).
9. **Aucun test sur la couche `ui/`** : les 41 tests couvrent exclusivement `mealplanner/`.

---

## 7. Ce que chaque projet fait mieux que l'autre

### Opus5 fait mieux

1. **Répartition par repas exacte** : somme des macros conforme au total à 10⁻⁴ près sur
   3, 4 et 5 repas, contre jusqu'à +8,2 % d'incohérence chez Sonnet5.
2. **Bornes de sécurité nutritionnelles** : plafond protéique à 40 % de l'énergie,
   plancher lipidique de 0,8 g/kg, plancher glucidique de 10 %, là où Sonnet5 peut
   descendre à 0 g de glucides.
3. **Mise à l'échelle des portions** : 31 tailles évaluées par recette contre une seule
   portion figée.
4. **Exclusion des aliments périmés** au lieu de leur donner la priorité maximale.
5. **Micronutriments** : 6 micronutriments modélisés et surveillés, absents de Sonnet5.
6. **41 tests verts** contre zéro, couvrant précisément les règles métier délicates.
7. **Macros de recettes dérivées des ingrédients** : impossible qu'une recette
   contredise son contenu.
8. **Ambiguïté cru/cuit tranchée** et rendue visible dans le nom des aliments.
9. **Gestion multi-lots FEFO** correcte à l'agrégation comme à la consommation.
10. **Séparation métier/UI stricte** : `mealplanner/` n'importe jamais Streamlit et est
    testable sans base de données.
11. **Documentation** : chaque arbitrage justifié, chaque affirmation chiffrée vérifiée
    exacte.
12. **Complétude de l'interface** : progression du jour, saisie manuelle et libre,
    suppression d'entrées, graphiques, journée complète en un clic.

### Sonnet5 fait mieux

1. **Saisie du garde-manger en texte libre** : on peut y mettre « chorizo »,
   « restes de couscous » ou n'importe quel produit du frigo réel. Opus5 enferme
   l'utilisateur dans son catalogue de 59 aliments — tout ce qui n'y est pas est
   littéralement inexprimable, ce qui est une limite sévère pour un usage quotidien.
2. **Pastilles de péremption par ligne d'inventaire** (🔴 / 🟠 / 🟢 + jours restants),
   plus immédiates que les bandeaux d'alerte textuels d'Opus5, et présentes sur
   *chaque* aliment y compris ceux à plus de 7 jours.
3. **Horizon d'urgence plus généreux** : 14 jours contre 7 chez Opus5. Un aliment qui
   périme dans 10 jours reçoit un signal chez Sonnet5, aucun chez Opus5.
4. **Page dédiée de consultation des recettes** : Opus5 n'offre aucun moyen de
   simplement parcourir son catalogue de recettes — elles n'apparaissent qu'à travers le
   moteur de suggestion ou une liste déroulante de log.
5. **Économie de code** : 662 LOC contre 2 977 pour couvrir les mêmes cinq
   fonctionnalités en surface, soit 4,5 fois moins à lire et à maintenir.
   `macros.py` fait 72 LOC contre 190 pour `nutrition.py` et s'audite d'un coup d'œil.
6. **Aucun code mort** : contre 4 membres publics inutilisés chez Opus5.
7. **Table de répartition par repas directement lisible** : `MEAL_DISTRIBUTION` est un
   dictionnaire de ratios qu'on vérifie mentalement en trois secondes, là où la
   normalisation par poids relatifs d'Opus5 demande de dérouler le calcul.
8. **Noms d'ingrédients humains** dans les recettes (`"boeuf haché"`) plutôt que des
   identifiants opaques (`"boeuf_hache_5"`).
9. **Ratio documentation/code légèrement supérieur** : 13,3 % contre 11,1 %.
10. **Démarrage marginalement plus rapide** : 1,08 s contre 1,14 s, et import de la
    logique métier en 43 ms contre 76 ms.

---

## 8. Différences d'approche notables

**Granularité de la modélisation.** C'est la divergence structurante. Opus5 a construit
une table de 59 aliments × 10 nutriments et fait tout dériver d'elle : les macros des
recettes, la mise à l'échelle des portions, les micronutriments, les substitutions
calées sur le nutriment dominant, les aliments sources recommandés en cas de carence.
Sonnet5 a stocké des macros dénormalisées au niveau de la recette et n'a pas de table
d'aliments du tout. La conséquence n'est pas une question de goût : trois exigences du
brief (portions adaptées aux macros du repas, micronutriments dans la détection de
carences, quantités de substitution) deviennent inatteignables sans cette table. Le prix
payé est de 2 300 lignes de code supplémentaires.

**Gestion de l'incertitude.** Opus5 traite « je ne sais pas » comme une catégorie à part
entière et le dit : urgence = 0 pour un lot sans date, « ne rien savoir ne doit jamais
pénaliser ni avantager une recette » ([pantry.py:27-28](Opus5/mealplanner/pantry.py:27)) ;
journée en cours exclue du diagnostic tant qu'elle est incomplète ; minimum de 3 jours
loggés avant tout diagnostic ; repas saisis en texte libre exclus de l'analyse
micronutritionnelle, avec un message qui l'explique. Sonnet5 traite l'inconnu comme
l'absence : `SUBSTITUTIONS.get(name, [])`, `target or 1`, pas de date → pas de bonus. La
réponse est souvent la même, mais elle est obtenue implicitement — et quand elle ne
l'est pas (le `or 1` sur une cible nulle), rien ne le signale.

**Arbitrages faits ou évités.** Opus5 tranche deux questions que le brief laissait
ouvertes et assume les deux : les féculents sont crus (et le nom affiché le dit), et les
jeux d'objectifs sont disjoints par niveau d'activité (un sédentaire ne se voit jamais
proposer une sèche). Sonnet5 laisse les deux ouvertes : l'état des féculents n'est écrit
nulle part, et activité × objectif forment un produit cartésien dont certaines
combinaisons n'ont pas de sens. Éviter l'arbitrage a un coût mesurable : c'est
exactement là que naissent l'incohérence cru/cuit et le profil « ultra-actif sédentaire ».

**Nature du moteur de suggestion.** Opus5 fait une optimisation : recherche sur
(recette × portion) avec un score composite pondéré et une couverture du garde-manger
elle-même pondérée par la part d'énergie de chaque ingrédient — manquer 150 g de poulet
ne pèse pas comme manquer 8 g d'huile. Sonnet5 fait un filtre suivi d'un tri
lexicographique. Le premier peut sacrifier de la couverture pour gagner en adéquation ;
le second ne le peut jamais, ses critères étant hiérarchisés en dur.

**Traitement de l'erreur en entrée.** Opus5 contraint l'entrée (sélection dans un
catalogue) et valide dans le code (bornes, planchers, rejet des conversions absurdes).
Sonnet5 accepte tout et ne valide rien. C'est un arbitrage souplesse contre sûreté, et
les deux termes sont réels : la saisie libre de Sonnet5 est authentiquement plus
pratique, et c'est elle qui rend possible le bug chorizo/riz.

**Rapport aux tests.** Opus5 a écrit 389 LOC de tests, soit 13 % de son code, et les
sujets choisis correspondent exactement aux pièges que le brief tendait (journée isolée,
journée en cours, FEFO, disjonction des objectifs). Sonnet5 n'en a écrit aucun. Sur les
trois bugs critiques que j'ai trouvés chez Sonnet5, les trois seraient tombés au premier
test unitaire naïf.

---

## 9. Ce que le benchmark ne mesure pas

- **Un seul run par modèle.** C'est la limite principale. La variance entre deux
  générations d'un même modèle sur un brief de cette taille peut être considérable, et
  rien ici ne permet de distinguer une différence de capacité d'un tirage favorable.
  Aucune conclusion générale sur Opus 5 contre Sonnet 5 ne devrait être tirée de ce
  document.
- **Ni le temps ni le coût de génération** ne sont mesurés. Sonnet5 a produit 877 lignes
  contre 3 821 : si le coût et la latence étaient dans le brief implicite, le rapport
  qualité/prix ne serait pas celui du tableau de scores.
- **Aucun test utilisateur réel.** Le critère « expérience utilisateur » repose sur mon
  parcours des interfaces, pas sur l'observation de quelqu'un qui essaie vraiment de
  planifier ses repas. Le catalogue fermé d'Opus5 pourrait s'avérer bien plus bloquant
  en usage réel que ne le suggère ma note, et la saisie libre de Sonnet5 bien plus
  précieuse.
- **Biais de mon évaluation.** Trois points concrets. (a) J'ai lu le code avant de
  l'exécuter, ce qui a orienté les scénarios que j'ai testés vers les défauts que
  j'avais repérés à la lecture. (b) Le contrôle cru/cuit utilise la table d'aliments
  d'Opus5 comme référence externe, faute de table dans Sonnet5 — c'est structurellement
  favorable à Opus5 sur ce test, et je l'ai signalé sur place. (c) Un projet plus
  documenté offre plus de prises à la vérification ; Opus5 a été mesuré contre ses
  propres affirmations chiffrées, Sonnet5 n'en fait presque aucune, ce qui le protège
  d'un type de reproche.
- **Aucune validation par un nutritionniste.** Je vérifie la cohérence interne (l'énergie
  correspond-elle aux macros, les seuils sont-ils appliqués), pas la justesse
  diététique. Que 2,4 g/kg de protéines en sèche soit un bon conseil dépasse ce que ce
  benchmark peut établir.
- **Rien sur la durée.** Maintenabilité, coût d'ajout d'une fonctionnalité, tenue de la
  base au bout de six mois d'utilisation : non mesurés. Les 2 300 lignes
  supplémentaires d'Opus5 sont un actif dans mon analyse ; elles pourraient être un
  passif dans un contexte où personne ne les relit.
- **Une seule plateforme, une seule version.** Windows 11, Python 3.14.2, Streamlit
  1.60.0. Sonnet5 déclenche déjà des avertissements de dépréciation sur cette version ;
  le comportement des deux applications sur d'autres versions n'est pas établi.
- **Données synthétiques uniquement.** Les garde-mangers, les profils et les 7 jours
  d'historique ont été fabriqués par mes scripts. Aucune des deux applications n'a été
  confrontée à des données réelles, désordonnées, saisies par un humain fatigué.
- **Les tests d'Opus5 sont ses propres tests.** Que 41 tests passent prouve qu'il est
  cohérent avec ce que son auteur a décidé de vérifier, pas qu'il est correct. Les
  vérifications indépendantes de la section 5 sont là pour cette raison, mais elles ne
  couvrent pas tout le code.
